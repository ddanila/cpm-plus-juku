#!/usr/bin/env python3
"""Capture and audit the C4 physical CS00015 qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pty
import select
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import tty
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COSIM = ROOT.parent / "8080-cosim"
CANDIDATE = "network-first-abi1-cs00015-c4"
SCHEMA = "juku-network-first-physical-qualification-v1"
EXPECTED_D15 = "3e8b9eb2f3752002821e6ec18dd59805108389c9d93aba40316bd2e18eb7684f"
EXPECTED_D16 = "f15b1b029edd845e0aa7622d61e9b84740957dce1f38a75867cedccef54494ac"
MANUAL_TESTS = (
    "automatic_no_keypress",
    "post_no_failure_indication",
    "prompt",
    "warm_boot",
    "dir",
    "sequential_read",
    "diag",
    "erase_write",
    "keyboard",
    "compact_display",
    "cursor_blink",
    "host_loss_recovery",
    "server_reconnect_without_reset",
)
VALID_RESULTS = ("pending", "pass", "fail")


class N4Console:
    """Small binary-safe client for a janet_disk_server --console-pty."""

    def __init__(self, fd: int) -> None:
        self.fd = fd
        self.transcript = bytearray()

    def send(self, data: bytes) -> None:
        os.write(self.fd, data)

    def read_until(self, marker: bytes, timeout: float) -> bytes:
        start = len(self.transcript)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.fd], [], [], 0.1)
            if not ready:
                continue
            incoming = os.read(self.fd, 4096)
            if not incoming:
                continue
            self.transcript.extend(incoming)
            current = bytes(self.transcript[start:])
            if marker in current:
                return current
        raise TimeoutError(
            f"N4 console did not emit {marker!r}; "
            f"transcript={bytes(self.transcript[start:])!r}"
        )

    def read_paged(self, timeout: float) -> bytes:
        start = len(self.transcript)
        handled = 0
        prompt = b"Press RETURN to Continue"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.fd], [], [], 0.1)
            if ready:
                incoming = os.read(self.fd, 4096)
                if incoming:
                    self.transcript.extend(incoming)
            current = bytes(self.transcript[start:])
            if b"A>" in current:
                return current
            if prompt in current[handled:]:
                self.send(b"\r")
                handled = len(current)
        raise TimeoutError(
            "paged N4 console did not return to CCP; "
            f"transcript={bytes(self.transcript[start:])!r}"
        )


def n4_console_smoke(fd: int, *, resume: bool, timeout: float) -> dict[str, Any]:
    """Exercise the physical CP/M console; raise on any missing evidence."""
    console = N4Console(fd)
    results: dict[str, str] = {}
    if resume:
        # Queue input immediately. The replacement server keeps it until the
        # target's bounded N4 reprobe succeeds, so no local key is required.
        console.send(b"DIR\r")
        directory = console.read_until(b"A>", timeout)
        if b"CCP" not in directory or b"DIAG" not in directory:
            raise ValueError("post-reconnect DIR lacks recovery-volume files")
        results["reconnect_dir"] = "pass"
    else:
        banner = console.read_until(b"A>", timeout)
        if b"CP/M Plus 3.1 Juku" not in banner or \
                b"NetDisk v3, 19200" not in banner:
            raise ValueError("automatic boot banner or NetDisk identity differs")
        # Match a human operator: allow CP/M to enter its idle input path before
        # the first command. This is the exact boundary that exposed C3.
        time.sleep(0.25)
        console.send(b"DIR\r")
        directory = console.read_until(b"A>", timeout)
        if b"CCP" not in directory or b"README" not in directory:
            raise ValueError("DIR lacks qualification-volume files")
        results["dir"] = "pass"

        console.send(b"TYPE README.TXT\r")
        sequential = console.read_paged(timeout)
        if b"CP/M Plus 3.1" not in sequential:
            raise ValueError("sequential README read lacks expected contents")
        results["sequential_read"] = "pass"

        console.send(b"DIAG CPU\r")
        diagnostic = console.read_until(b"A>", timeout)
        if b"CPU: PASS" not in diagnostic:
            raise ValueError("DIAG CPU did not pass")
        results["diag"] = "pass"

        console.send(b"WBOOT\r")
        console.read_until(b"A>", timeout)
        results["warm_boot"] = "pass"

        console.send(b"ERA README.TXT\r")
        console.read_until(b"A>", timeout)
        console.send(b"DIR\r")
        after_erase = console.read_until(b"A>", timeout)
        if b"README" in after_erase:
            raise ValueError("README.TXT remains after ERA")
        results["erase_write"] = "pass"
    return {
        "schema": "juku-network-first-n4-smoke-v1",
        "kind": "resume" if resume else "cold boot",
        "result": "pass",
        "checks": results,
        "transcript_bytes": len(console.transcript),
        "transcript_sha256": hashlib.sha256(console.transcript).hexdigest(),
        "transcript": bytes(console.transcript),
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"{path} is not a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        text=True, stdout=subprocess.PIPE,
    )
    return result.stdout.strip()


def verify_candidate(candidate: Path) -> dict[str, Any]:
    candidate = candidate.resolve()
    manifest_path = candidate / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"candidate manifest is missing: {manifest_path}")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != "juku-network-first-bench-candidate-v1" or \
            manifest.get("candidate") != CANDIDATE or \
            manifest.get("status") != "physical qualification pending":
        raise ValueError("candidate identity/status is not the pending C4 gate")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise TypeError("candidate file manifest is missing")
    for name, expected in files.items():
        path = candidate / name
        if not path.is_file() or not isinstance(expected, dict):
            raise ValueError(f"candidate artifact is missing: {name}")
        if path.stat().st_size != expected.get("bytes") or \
                sha256(path) != expected.get("sha256"):
            raise ValueError(f"candidate artifact differs: {name}")
    d15 = candidate / "D15-low-8K.bin"
    d16 = candidate / "D16-high-8K.bin"
    combined = candidate / "combined-rom.bin"
    if sha256(d15) != EXPECTED_D15 or sha256(d16) != EXPECTED_D16 or \
            d15.read_bytes() + d16.read_bytes() != combined.read_bytes():
        raise ValueError("C4 programmer halves or concatenation differ")
    return manifest


def load_session(directory: Path) -> tuple[Path, dict[str, Any]]:
    directory = directory.resolve()
    session = load_json(directory / "session.json")
    if session.get("schema") != SCHEMA or session.get("candidate") != CANDIDATE:
        raise ValueError("physical session identity differs")
    manual_tests = session.get("manual_tests")
    if not isinstance(manual_tests, dict) or \
            set(manual_tests) != set(MANUAL_TESTS):
        raise ValueError("physical session test matrix differs")
    verify_candidate(Path(str(session["candidate_directory"])))
    cosim = Path(str(session["cosim_directory"]))
    if sha256(cosim / "tools/janet_disk_server.py") != \
            session.get("host_server_sha256"):
        raise ValueError("disk-server source changed after session initialization")
    if sha256(Path(__file__).resolve()) != session.get("recorder_sha256"):
        raise ValueError("qualification recorder changed after session initialization")
    return directory, session


def valid_n4_capture(directory: Path, run: dict[str, Any], kind: str) -> bool:
    """Validate optional automated physical-console evidence byte for byte."""
    smoke = run.get("n4_smoke")
    if smoke is None:
        return True
    transcript = directory / "console.bin"
    record = directory / "console.json"
    return (
        isinstance(smoke, dict)
        and smoke.get("schema") == "juku-network-first-n4-smoke-v1"
        and smoke.get("kind") == kind
        and smoke.get("result") == "pass"
        and transcript.is_file()
        and record.is_file()
        and load_json(record) == smoke
        and transcript.stat().st_size == smoke.get("transcript_bytes")
        and sha256(transcript) == smoke.get("transcript_sha256")
        and run.get("console_transcript_sha256") == sha256(transcript)
    )


def checklist(session: Path) -> str:
    tests = "\n".join(f"- [ ] `{name}`" for name in MANUAL_TESTS)
    return f"""# C4 physical qualification checklist

Session: `{session}`

1. Verify programmer readback hashes for both EPROMs and record them.
2. Run at least three independent cold boots. Each must reach `A>` without a
   keypress; keep the generated `boot.json` and `host.log` from every run.
   `run --console-smoke` also captures and validates `DIR`, sequential read,
   diagnostics, warm boot, erase/write, and a post-erase directory over N4.
3. Complete the genuinely local observations below on the display and keyboard.
4. After a console-smoke run stops its host, leave CP/M running and start
   `resume --console-smoke`. It queues `DIR` until the bounded N4 reprobe and
   proves live server reattachment without RESET.
5. Run `audit`; promotion is forbidden until it reports PASS.

Required observations:

{tests}

Use `record --test name=pass` only for observations actually made on CS00015.
Do not infer a physical pass from simulator output.
"""


def init(args: argparse.Namespace) -> int:
    candidate = args.candidate.resolve()
    manifest = verify_candidate(candidate)
    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"qualification directory already exists: {output}")
    output.mkdir(parents=True)
    cosim = args.cosim.resolve()
    session: dict[str, Any] = {
        "schema": SCHEMA,
        "candidate": CANDIDATE,
        "status": "collecting physical evidence",
        "board": args.board,
        "created_at_utc": utc_now(),
        "candidate_directory": str(candidate),
        "candidate_manifest_sha256": sha256(candidate / "manifest.json"),
        "candidate_files": manifest["files"],
        "reference_volume": str(candidate / "network-disk.img"),
        "reference_volume_sha256": sha256(candidate / "network-disk.img"),
        "cosim_directory": str(cosim),
        "host_server_sha256": sha256(cosim / "tools/janet_disk_server.py"),
        "recorder_sha256": sha256(Path(__file__).resolve()),
        "repositories": {
            "cpm-plus-juku": git_head(ROOT),
            "8080-cosim": git_head(cosim),
        },
        "programmer_verification": {"D15": None, "D16": None},
        "manual_tests": {
            name: {"result": "pending", "notes": ""}
            for name in MANUAL_TESTS
        },
        "notes": [],
    }
    write_json(output / "session.json", session)
    (output / "CHECKLIST.md").write_text(checklist(output) + "\n")
    print(f"PHYSICAL-QUALIFICATION: initialized {output}")
    print(f"  board: {args.board}")
    print(f"  C4 manifest: {session['candidate_manifest_sha256']}")
    print("  writable A: a fresh private copy will be made for every cold boot")
    return 0


def next_run(directory: Path, prefix: str) -> Path:
    index = 1
    while (directory / f"{prefix}-{index:02d}").exists():
        index += 1
    return directory / f"{prefix}-{index:02d}"


def server_command(directory: Path, session: dict[str, Any], args: argparse.Namespace,
                   *, resume: bool, result: Path,
                   console_pty: str | None = None) -> list[str]:
    candidate = Path(str(session["candidate_directory"]))
    cosim = args.cosim.resolve()
    if cosim != Path(str(session["cosim_directory"])):
        raise ValueError("server checkout differs from the initialized session")
    if resume:
        prior = sorted(directory.glob("boot-*/run.json"))
        if not prior:
            raise ValueError("resume requires a previously captured cold boot")
        prior_run = load_json(prior[-1])
        volume = Path(str(prior_run.get("volume", "")))
        if not volume.is_file():
            raise ValueError("latest cold-boot working volume is missing")
    else:
        volume = result / "working-network-disk.img"
    command = [
        sys.executable, str(cosim / "tools/janet_disk_server.py"),
        args.serial,
        str(candidate / "cpm-plus-system.bin"),
        str(volume),
    ]
    if resume:
        command.append("--resume-disk")
    else:
        command.extend((
            "--fast-stage1", str(candidate / "fastboot-v15.bin"),
            "--network-rom",
            "--boot-result-json", str(result / "boot.json"),
        ))
    command.extend((
        "--disk-baud", "19200", "--disk-protocol", "3", "--writable",
        "--timeout", str(args.timeout),
        "--disk-timeout", str(args.disk_timeout),
    ))
    if console_pty is not None:
        command.extend(("--console-pty", console_pty))
    return command


def run_server(args: argparse.Namespace, *, resume: bool) -> int:
    directory, session = load_session(args.session)
    result = next_run(directory, "resume" if resume else "boot")
    console_master: int | None = None
    console_slave: int | None = None
    console_pty: str | None = None
    if args.console_smoke and not args.dry_run:
        console_master, console_slave = pty.openpty()
        tty.setraw(console_master)
        tty.setraw(console_slave)
        console_pty = os.ttyname(console_slave)
    elif args.console_smoke:
        console_pty = "N4-CONSOLE-PTY"
    command = server_command(
        directory, session, args, resume=resume, result=result,
        console_pty=console_pty,
    )
    if args.dry_run:
        print(shlex.join(command))
        return 0
    result.mkdir()
    volume = Path(command[4])
    if not resume:
        shutil.copyfile(
            Path(str(session["reference_volume"])), volume,
        )
    volume_before = sha256(volume)
    started = utc_now()
    log_path = result / "host.log"
    returncode = 1
    smoke_result: dict[str, Any] | None = None
    smoke_errors: list[BaseException] = []
    with log_path.open("w") as log:
        log.write("COMMAND " + shlex.join(command) + "\n")
        log.flush()
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, start_new_session=True,
        )
        if console_slave is not None:
            os.close(console_slave)
            console_slave = None

        def exercise_console() -> None:
            nonlocal smoke_result
            assert console_master is not None
            try:
                smoke_result = n4_console_smoke(
                    console_master, resume=resume,
                    timeout=args.console_timeout,
                )
            except BaseException as error:
                smoke_errors.append(error)
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)

        console_worker = None
        if console_master is not None:
            console_worker = threading.Thread(
                target=exercise_console, daemon=True,
            )
            console_worker.start()
        assert process.stdout is not None
        try:
            for line in process.stdout:
                print(line, end="")
                log.write(line)
                log.flush()
            returncode = process.wait()
        except KeyboardInterrupt:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
            returncode = process.wait(timeout=10)
        if console_worker is not None:
            console_worker.join(timeout=5)
            if console_worker.is_alive():
                assert console_master is not None
                os.close(console_master)
                console_master = None
                console_worker.join(timeout=1)
                smoke_errors.append(TimeoutError("N4 console worker did not stop"))
        if console_master is not None:
            os.close(console_master)
            console_master = None
    boot_path = result / "boot.json"
    record = {
        "schema": "juku-network-first-physical-host-run-v1",
        "kind": "resume" if resume else "cold boot",
        "started_at_utc": started,
        "ended_at_utc": utc_now(),
        "returncode": returncode,
        "command": command,
        "host_log_sha256": sha256(log_path),
        "volume": str(volume),
        "volume_sha256_before": volume_before,
        "volume_sha256_after": sha256(volume),
        "boot_result": load_json(boot_path) if boot_path.is_file() else None,
    }
    if smoke_result is not None:
        transcript = smoke_result.pop("transcript")
        assert isinstance(transcript, bytes)
        transcript_path = result / "console.bin"
        transcript_path.write_bytes(transcript)
        write_json(result / "console.json", smoke_result)
        record["n4_smoke"] = smoke_result
        record["console_transcript_sha256"] = sha256(transcript_path)
    write_json(result / "run.json", record)
    if smoke_result is not None:
        passed = (
            ("server_reconnect_without_reset",)
            if resume else (
                "automatic_no_keypress", "post_no_failure_indication",
                "prompt", "warm_boot", "dir", "sequential_read", "diag",
                "erase_write",
            )
        )
        evidence = (
            "automated physical N4 cold-boot transcript"
            if not resume else
            "automated physical N4 live-server reattach transcript; "
            "disk-request loss remains a separate observation"
        )
        for name in passed:
            session["manual_tests"][name] = {
                "result": "pass", "notes": evidence,
            }
        session["updated_at_utc"] = utc_now()
        write_json(directory / "session.json", session)
    print(f"PHYSICAL-QUALIFICATION: captured {result}")
    if smoke_errors:
        raise ValueError("N4 console smoke failed: " + "; ".join(
            str(error) for error in smoke_errors
        ))
    return 0 if returncode in (0, 130) else returncode


def assignments(values: list[str], *, allowed: tuple[str, ...] | None = None
                ) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected NAME=VALUE, got {value!r}")
        name, assigned = value.split("=", 1)
        if allowed is not None and assigned not in allowed:
            raise ValueError(f"invalid value for {name}: {assigned}")
        result[name] = assigned
    return result


def record(args: argparse.Namespace) -> int:
    directory, session = load_session(args.session)
    results = assignments(args.test, allowed=VALID_RESULTS)
    notes = assignments(args.test_note)
    unknown = (set(results) | set(notes)) - set(MANUAL_TESTS)
    if unknown:
        raise ValueError("unknown physical tests: " + ", ".join(sorted(unknown)))
    for name, value in results.items():
        session["manual_tests"][name]["result"] = value
    for name, value in notes.items():
        session["manual_tests"][name]["notes"] = value
    verification = session["programmer_verification"]
    if args.d15_sha256:
        if args.d15_sha256.lower() != EXPECTED_D15:
            raise ValueError("D15 programmer verification hash differs from C4")
        verification["D15"] = args.d15_sha256.lower()
    if args.d16_sha256:
        if args.d16_sha256.lower() != EXPECTED_D16:
            raise ValueError("D16 programmer verification hash differs from C4")
        verification["D16"] = args.d16_sha256.lower()
    if args.note:
        session["notes"].extend(args.note)
    session["updated_at_utc"] = utc_now()
    write_json(directory / "session.json", session)
    print(f"PHYSICAL-QUALIFICATION: updated {directory}")
    return 0


def audit(args: argparse.Namespace) -> int:
    directory, session = load_session(args.session)
    failures: list[str] = []
    if session.get("board") != "CS00015":
        failures.append("board identity is not CS00015")
    verification = session.get("programmer_verification", {})
    if verification.get("D15") != EXPECTED_D15:
        failures.append("D15 programmer verification is missing or different")
    if verification.get("D16") != EXPECTED_D16:
        failures.append("D16 programmer verification is missing or different")
    boots: list[dict[str, Any]] = []
    boot_volumes: set[str] = set()
    volume_chain: dict[str, str] = {}
    for path in sorted(directory.glob("boot-*/run.json")):
        run = load_json(path)
        log_path = path.parent / "host.log"
        boot_path = path.parent / "boot.json"
        volume_path = Path(str(run.get("volume", "")))
        boot = run.get("boot_result")
        valid_capture = (
            run.get("kind") == "cold boot"
            and run.get("returncode") in (0, 130)
            and log_path.is_file()
            and run.get("host_log_sha256") == sha256(log_path)
            and boot_path.is_file()
            and isinstance(boot, dict)
            and boot == load_json(boot_path)
            and "disk request" in log_path.read_text(errors="replace")
            and volume_path.is_file()
            and volume_path.parent.resolve() == path.parent.resolve()
            and run.get("volume_sha256_before") ==
            session["reference_volume_sha256"]
            and isinstance(run.get("volume_sha256_after"), str)
            and len(run["volume_sha256_after"]) == 64
            and valid_n4_capture(path.parent, run, "cold boot")
        )
        if valid_capture and isinstance(boot, dict):
            boots.append(boot)
            resolved_volume = str(volume_path.resolve())
            boot_volumes.add(resolved_volume)
            volume_chain[resolved_volume] = run["volume_sha256_after"]
        else:
            failures.append(f"invalid or incomplete cold-boot capture: {path.parent.name}")
    if len(boots) < 3:
        failures.append(f"only {len(boots)} complete cold-boot timings; need 3")
    candidate_files = session["candidate_files"]
    for index, boot in enumerate(boots, 1):
        if boot.get("schema") != "juku-janet-boot-result-v1" or \
                boot.get("network_rom") is not True or \
                boot.get("effective_boot_baud") != 19200 or \
                boot.get("disk_baud") != 19200 or \
                boot.get("system_sha256") != \
                candidate_files["cpm-plus-system.bin"]["sha256"] or \
                boot.get("fast_stage_sha256") != \
                candidate_files["fastboot-v15.bin"]["sha256"]:
            failures.append(f"cold boot {index} identity/protocol differs")
        first = boot.get("first_disk_request")
        if not isinstance(first, dict) or \
                float(first.get("elapsed_seconds", 0)) <= 0:
            failures.append(f"cold boot {index} has no positive timing")
    resumes = []
    for path in sorted(directory.glob("resume-*/run.json")):
        run = load_json(path)
        log_path = path.parent / "host.log"
        volume_path = Path(str(run.get("volume", "")))
        if run.get("kind") == "resume" and run.get("returncode") in (0, 130) \
                and log_path.is_file() \
                and run.get("host_log_sha256") == sha256(log_path) \
                and "disk request" in log_path.read_text(errors="replace") \
                and volume_path.is_file() \
                and str(volume_path.resolve()) in boot_volumes \
                and isinstance(run.get("volume_sha256_before"), str) \
                and run.get("volume_sha256_before") == \
                volume_chain.get(str(volume_path.resolve())) \
                and isinstance(run.get("volume_sha256_after"), str) \
                and len(run["volume_sha256_after"]) == 64 \
                and valid_n4_capture(path.parent, run, "resume"):
            resumes.append(run)
            volume_chain[str(volume_path.resolve())] = run["volume_sha256_after"]
        else:
            failures.append(f"invalid or incomplete resume capture: {path.parent.name}")
    if not resumes:
        failures.append("no live NetDisk resume host run was captured")
    for volume, expected_hash in volume_chain.items():
        if sha256(Path(volume)) != expected_hash:
            failures.append(f"working volume changed outside captured runs: {volume}")
    for name in MANUAL_TESTS:
        value = session["manual_tests"][name]["result"]
        if value != "pass":
            failures.append(f"physical observation {name} is {value}")
    if failures:
        session["status"] = "physical qualification incomplete"
        session["last_audit_at_utc"] = utc_now()
        session["last_audit_failures"] = failures
        write_json(directory / "session.json", session)
        print("PHYSICAL-QUALIFICATION-AUDIT: INCOMPLETE")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    timings = [
        float(boot["first_disk_request"]["elapsed_seconds"])
        for boot in boots
    ]
    session["status"] = "physical qualification passed; acceptance audit pending"
    session["qualified_at_utc"] = utc_now()
    session["last_audit_at_utc"] = session["qualified_at_utc"]
    session["last_audit_failures"] = []
    session["cold_boot_timings_seconds"] = timings
    write_json(directory / "session.json", session)
    print(
        "PHYSICAL-QUALIFICATION-AUDIT: PASS "
        f"({len(timings)} cold boots, {min(timings):.3f}..{max(timings):.3f}s)"
    )
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init", help="create a qualification record")
    init_parser.add_argument("--candidate", type=Path,
                             default=ROOT / "out" / CANDIDATE)
    init_parser.add_argument("--output", type=Path, required=True)
    init_parser.add_argument("--board", default="CS00015")
    init_parser.add_argument("--cosim", type=Path, default=DEFAULT_COSIM)
    init_parser.set_defaults(action=init)
    for name, resume in (("run", False), ("resume", True)):
        run_parser = commands.add_parser(name)
        run_parser.add_argument("session", type=Path)
        run_parser.add_argument("serial")
        run_parser.add_argument("--cosim", type=Path,
                                default=DEFAULT_COSIM)
        run_parser.add_argument("--timeout", type=float, default=86400)
        run_parser.add_argument("--disk-timeout", type=float, default=86400)
        run_parser.add_argument(
            "--console-smoke", action="store_true",
            help="run the auditable N4 command suite and stop the host cleanly",
        )
        run_parser.add_argument(
            "--console-timeout", type=float, default=900,
            help="seconds allowed for each N4 command or reconnect",
        )
        run_parser.add_argument("--dry-run", action="store_true")
        run_parser.set_defaults(
            action=lambda args, resume=resume: run_server(args, resume=resume),
        )
    record_parser = commands.add_parser("record")
    record_parser.add_argument("session", type=Path)
    record_parser.add_argument("--test", action="append", default=[],
                               metavar="NAME=pass|fail|pending")
    record_parser.add_argument("--test-note", action="append", default=[],
                               metavar="NAME=TEXT")
    record_parser.add_argument("--d15-sha256")
    record_parser.add_argument("--d16-sha256")
    record_parser.add_argument("--note", action="append", default=[])
    record_parser.set_defaults(action=record)
    audit_parser = commands.add_parser("audit")
    audit_parser.add_argument("session", type=Path)
    audit_parser.set_defaults(action=audit)
    return result


def main() -> int:
    args = parser().parse_args()
    return int(args.action(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError, TimeoutError,
            TypeError, ValueError) as error:
        print(f"physical-qualification: {error}", file=sys.stderr)
        raise SystemExit(1)
