#!/usr/bin/env python3
"""Prove the C4 physical recorder rejects gaps and accepts complete evidence."""

from __future__ import annotations

import hashlib
import json
import os
import pty
import shutil
import subprocess
import sys
import tempfile
import threading
import tty
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/physical_qualification.py"
CANDIDATE = ROOT / "out/network-first-abi1-cs00015-c4"
D15 = "3e8b9eb2f3752002821e6ec18dd59805108389c9d93aba40316bd2e18eb7684f"
D16 = "f15b1b029edd845e0aa7622d61e9b84740957dce1f38a75867cedccef54494ac"
TESTS = (
    "automatic_no_keypress", "post_no_failure_indication", "prompt",
    "warm_boot", "dir", "sequential_read", "diag", "erase_write",
    "keyboard", "compact_display", "cursor_blink", "host_loss_recovery",
    "server_reconnect_without_reset",
)
sys.path.insert(0, str(ROOT / "tools"))
import physical_qualification as qualification  # noqa: E402


def invoke(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *arguments], cwd=ROOT, check=check,
        text=True, capture_output=True,
    )


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def captured_run(path: Path, *, kind: str, boot: dict[str, object] | None,
                 volume: Path) -> None:
    log = path / "host.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("disk request op=14 seq=01 drive=0 track=2 sector=1 status=0\n")
    if boot is not None:
        write_json(path / "boot.json", boot)
    write_json(
        path / "run.json",
        {
            "schema": "juku-network-first-physical-host-run-v1",
            "kind": kind,
            "returncode": 130,
            "host_log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            "volume": str(volume),
            "volume_sha256_before":
                hashlib.sha256(volume.read_bytes()).hexdigest(),
            "volume_sha256_after": hashlib.sha256(volume.read_bytes()).hexdigest(),
            "boot_result": boot,
        },
    )


def attach_n4_capture(path: Path, *, kind: str) -> None:
    transcript = b"CP/M Plus 3.1 Juku\r\nA>DIR\r\nA>"
    smoke = {
        "schema": "juku-network-first-n4-smoke-v1",
        "kind": kind,
        "result": "pass",
        "checks": {"dir": "pass"},
        "transcript_bytes": len(transcript),
        "transcript_sha256": hashlib.sha256(transcript).hexdigest(),
    }
    (path / "console.bin").write_bytes(transcript)
    write_json(path / "console.json", smoke)
    run = json.loads((path / "run.json").read_text())
    run["n4_smoke"] = smoke
    run["console_transcript_sha256"] = smoke["transcript_sha256"]
    write_json(path / "run.json", run)


def read_command(fd: int) -> bytes:
    result = bytearray()
    while not result.endswith(b"\r"):
        result.extend(os.read(fd, 64))
    return bytes(result)


def n4_smoke_test() -> None:
    master, slave = pty.openpty()
    tty.setraw(master)
    tty.setraw(slave)
    failures: list[BaseException] = []

    def cold_target() -> None:
        try:
            os.write(slave, b"\r\nCP/M Plus 3.1 Juku\r\nNetDisk v3, 19200\r\nA>")
            assert read_command(slave) == b"DIR\r"
            os.write(slave, b"DIR\r\nCCP COM DIAG COM README TXT\r\nA>")
            assert read_command(slave) == b"TYPE README.TXT\r"
            os.write(slave, b"CP/M Plus 3.1 docs\r\nPress RETURN to Continue")
            assert read_command(slave) == b"\r"
            os.write(slave, b"\r\ncontinued\r\nA>")
            assert read_command(slave) == b"DIAG CPU\r"
            os.write(slave, b"CPU: PASS\r\nA>")
            assert read_command(slave) == b"WBOOT\r"
            os.write(slave, b"\r\nA>")
            assert read_command(slave) == b"ERA README.TXT\r"
            os.write(slave, b"\r\nA>")
            assert read_command(slave) == b"DIR\r"
            os.write(slave, b"CCP COM DIAG COM\r\nA>")
        except BaseException as error:
            failures.append(error)

    worker = threading.Thread(target=cold_target)
    worker.start()
    result = qualification.n4_console_smoke(
        master, resume=False, timeout=2,
    )
    worker.join(timeout=2)
    os.close(master)
    os.close(slave)
    if worker.is_alive() or failures or result["result"] != "pass" or \
            set(result["checks"]) != {
                "dir", "sequential_read", "diag", "warm_boot", "erase_write",
            }:
        raise AssertionError(f"cold N4 smoke differs: {result}, {failures}")

    master, slave = pty.openpty()
    tty.setraw(master)
    tty.setraw(slave)
    failures = []

    def resume_target() -> None:
        try:
            assert read_command(slave) == b"DIR\r"
            os.write(slave, b"DIR\r\nCCP COM DIAG COM\r\nA>")
        except BaseException as error:
            failures.append(error)

    worker = threading.Thread(target=resume_target)
    worker.start()
    result = qualification.n4_console_smoke(
        master, resume=True, timeout=2,
    )
    worker.join(timeout=2)
    os.close(master)
    os.close(slave)
    if worker.is_alive() or failures or result["checks"] != {
            "reconnect_dir": "pass",
    }:
        raise AssertionError(f"resume N4 smoke differs: {result}, {failures}")


def main() -> int:
    n4_smoke_test()
    if not CANDIDATE.is_dir():
        raise AssertionError("bench package must be generated before recorder test")
    manifest = json.loads((CANDIDATE / "manifest.json").read_text())
    with tempfile.TemporaryDirectory(prefix="c4-physical-recorder.") as name:
        session = Path(name) / "session"
        invoke(
            "init", "--candidate", str(CANDIDATE),
            "--output", str(session),
        )
        dry_run = invoke(
            "run", str(session), "/dev/null", "--console-smoke", "--dry-run",
        )
        if "--console-pty N4-CONSOLE-PTY" not in dry_run.stdout:
            raise AssertionError("console-smoke host wiring is absent")
        incomplete = invoke("audit", str(session), check=False)
        if incomplete.returncode != 1 or \
                "only 0 complete cold-boot timings" not in incomplete.stdout:
            raise AssertionError("incomplete evidence was not rejected")
        # The wrapper must own Ctrl+C and forward exactly one SIGINT. Keeping
        # the server out of the terminal process group prevents a second
        # interrupt from landing during its atomic writable-volume save.
        source = TOOL.read_text()
        if "start_new_session=True" not in source:
            raise AssertionError("physical server is not signal-isolated")
        for index, elapsed in enumerate((4.25, 4.31, 4.28), 1):
            run_directory = session / f"boot-{index:02d}"
            run_directory.mkdir()
            volume = run_directory / "working-network-disk.img"
            shutil.copyfile(CANDIDATE / "network-disk.img", volume)
            boot = {
                "schema": "juku-janet-boot-result-v1",
                "network_rom": True,
                "effective_boot_baud": 19200,
                "disk_baud": 19200,
                "system_sha256":
                    manifest["files"]["cpm-plus-system.bin"]["sha256"],
                "fast_stage_sha256":
                    manifest["files"]["fastboot-v15.bin"]["sha256"],
                "first_disk_request": {"elapsed_seconds": elapsed},
            }
            captured_run(
                run_directory, kind="cold boot", boot=boot, volume=volume,
            )
            if index == 1:
                attach_n4_capture(run_directory, kind="cold boot")
        captured_run(
            session / "resume-01", kind="resume", boot=None, volume=volume,
        )
        record = [
            "record", str(session), "--d15-sha256", D15,
            "--d16-sha256", D16,
        ]
        for test in TESTS:
            record.extend(("--test", f"{test}=pass"))
        invoke(*record)
        passed = invoke("audit", str(session))
        if "PHYSICAL-QUALIFICATION-AUDIT: PASS" not in passed.stdout:
            raise AssertionError("complete physical evidence did not pass")
        result = json.loads((session / "session.json").read_text())
        if result.get("status") != \
                "physical qualification passed; acceptance audit pending" or \
                result.get("cold_boot_timings_seconds") != [4.25, 4.31, 4.28]:
            raise AssertionError("qualification summary differs")
        console_path = session / "boot-01" / "console.bin"
        original_console = console_path.read_bytes()
        with console_path.open("ab") as console:
            console.write(b"tampered")
        tampered_console = invoke("audit", str(session), check=False)
        if tampered_console.returncode != 1 or \
                "invalid or incomplete cold-boot capture" not in \
                tampered_console.stdout:
            raise AssertionError("changed N4 evidence was not rejected")
        console_path.write_bytes(original_console)
        repaired = invoke("audit", str(session))
        if "PHYSICAL-QUALIFICATION-AUDIT: PASS" not in repaired.stdout:
            raise AssertionError("restored N4 evidence did not pass")
        with (session / "boot-01" / "host.log").open("a") as log:
            log.write("tampered\n")
        tampered = invoke("audit", str(session), check=False)
        if tampered.returncode != 1 or \
                "invalid or incomplete cold-boot capture" not in tampered.stdout:
            raise AssertionError("changed captured evidence was not rejected")
        result = json.loads((session / "session.json").read_text())
        if result.get("status") != "physical qualification incomplete":
            raise AssertionError("failed re-audit retained a passing status")
    print("PHYSICAL-QUALIFICATION-RECORDER-TEST: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
