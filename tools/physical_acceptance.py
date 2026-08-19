#!/usr/bin/env python3
"""Run and audit C6 full, development, or display acceptance on a Juku."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
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
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COSIM = Path(os.environ.get(
    "JUKU_COSIM_ROOT", str(ROOT.parent / "8080-cosim"),
))
DEFAULT_MANIFEST = ROOT / "out/cpm-plus-juku-c6-manifest.json"
WORKLOADS = ROOT / "physical/workloads"
RUNTIME_MEMORY = ROOT / "third_party/cpm3/releases/runtime-memory.json"
SCHEMA = "cpm-plus-juku-physical-acceptance-v1"
WORKLOAD_SCHEMA = "cpm-plus-juku-physical-workload-v1"
RESULT_SCHEMA = "cpm-plus-juku-physical-acceptance-result-v1"
CONSOLE_READY_MARKERS = (
    "Advertising N4 remote console on ",
    "Resuming N4 remote console on ",
)
DISK_READ_OPERATIONS = frozenset((0x11, 0x13, 0x14))
DISK_WRITE_OPERATIONS = frozenset((0x12, 0x15))
PAGE_PROMPT = b"Press RETURN to Continue"
PROFILE_VOLUMES = {
    "full": "full-a",
    "development": "development-a",
    "display": "full-a",
}


class AcceptanceError(RuntimeError):
    """A bounded physical acceptance operation failed."""


class ConsoleTimeout(AcceptanceError):
    def __init__(self, marker: bytes, tail: bytes) -> None:
        super().__init__(
            f"target timeout waiting for {marker!r}; "
            f"console tail={tail!r}"
        )
        self.marker = marker
        self.tail = tail


class WorkloadFailure(AcceptanceError):
    def __init__(self, message: str, commands: list[dict[str, Any]],
                 boot: dict[str, Any]) -> None:
        super().__init__(message)
        self.commands = commands
        self.boot = boot


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AcceptanceError(f"{path} is not a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def identity(path: Path) -> dict[str, Any]:
    path = path.resolve()
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def snapshot_file(source: Path, destination: Path) -> dict[str, Any]:
    source = source.resolve()
    shutil.copyfile(source, destination)
    result = identity(destination)
    result["source_path"] = str(source)
    return result


def checked_artifact(base: Path, entry: dict[str, Any], label: str) \
        -> dict[str, Any]:
    filename = entry.get("file")
    if not isinstance(filename, str):
        raise AcceptanceError(f"manifest {label} filename is missing")
    path = (base / filename).resolve()
    if not path.is_file():
        raise AcceptanceError(f"manifest {label} is missing: {path}")
    actual = identity(path)
    if actual["bytes"] != entry.get("bytes") or \
            actual["sha256"] != entry.get("sha256"):
        raise AcceptanceError(f"manifest {label} differs: {path}")
    return actual


def git_state(directory: Path) -> dict[str, Any]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=directory, check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=directory, check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    return {"path": str(directory.resolve()), "head": head, "dirty": dirty}


def verify_manifest(manifest_path: Path, cosim: Path, profile: str) \
        -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    requirements = manifest.get("requirements")
    if manifest.get("schema") != "cpm-plus-juku-boot-manifest-v1" or \
            not isinstance(requirements, dict) or \
            requirements.get("rom_abi") != "1.2" or \
            requirements.get("fastboot") != 16 or \
            requirements.get("bootstrap_baud") != 19200 or \
            requirements.get("netdisk") != 3 or \
            requirements.get("disk_baud") != 19200:
        raise AcceptanceError("manifest is not a C6/V16/N3 19200 artifact set")
    base = manifest_path.parent
    system_entry = manifest.get("system")
    stage_entry = manifest.get("fast_stage")
    if not isinstance(system_entry, dict) or not isinstance(stage_entry, dict):
        raise AcceptanceError("manifest system or fast stage is missing")
    system = checked_artifact(base, system_entry, "system")
    fast_stage = checked_artifact(base, stage_entry, "fast stage")

    wanted = PROFILE_VOLUMES[profile]
    volumes = manifest.get("volumes")
    if not isinstance(volumes, list):
        raise AcceptanceError("manifest volumes are missing")
    matches = [entry for entry in volumes
               if isinstance(entry, dict) and entry.get("profile") == wanted]
    if len(matches) != 1:
        raise AcceptanceError(f"manifest has no unique {wanted} volume")
    volume = checked_artifact(base, matches[0], f"{profile} A: volume")
    drive_b_entries = [entry for entry in volumes
                       if isinstance(entry, dict)
                       and entry.get("profile") == "approved-apps-b"]
    if len(drive_b_entries) != 1:
        raise AcceptanceError("manifest has no unique approved-apps-b volume")
    drive_b = checked_artifact(base, drive_b_entries[0], "read-only B: volume")

    rom_entry = manifest.get("rom")
    if not isinstance(rom_entry, dict):
        raise AcceptanceError("manifest ROM binding is missing")
    rom_base = cosim.resolve() / "spinoffs/jukuravi/network-rom"
    rom = checked_artifact(rom_base, rom_entry, "C6 ROM")
    metadata_name = rom_entry.get("metadata_file")
    if not isinstance(metadata_name, str):
        raise AcceptanceError("manifest ROM metadata binding is missing")
    metadata_entry = {
        "file": metadata_name,
        "bytes": rom_entry.get("metadata_bytes"),
        "sha256": rom_entry.get("metadata_sha256"),
    }
    rom_metadata = checked_artifact(
        rom_base, metadata_entry, "C6 ROM metadata",
    )
    if rom_entry.get("candidate") != "network-first-abi1.2-c6-simulator":
        raise AcceptanceError("manifest is not bound to the immutable C6 ROM")
    return {
        "manifest": identity(manifest_path),
        "build_identity": manifest.get("build_identity"),
        "system": system,
        "fast_stage": fast_stage,
        "volume": volume,
        "drive_b": drive_b,
        "rom": rom,
        "rom_metadata": rom_metadata,
    }


def load_workload(profile: str, path: Path | None = None) \
        -> tuple[Path, dict[str, Any]]:
    path = (path or WORKLOADS / f"{profile}.json").resolve()
    workload = load_json(path)
    if workload.get("schema") != WORKLOAD_SCHEMA or \
            workload.get("name") != profile or \
            workload.get("volume_profile") != PROFILE_VOLUMES[profile]:
        raise AcceptanceError(f"workload identity differs: {path}")
    commands = workload.get("commands")
    required = workload.get("required_coverage")
    boot_expect = workload.get("boot_expect")
    if not isinstance(commands, list) or not commands or \
            not isinstance(required, list) or not required or \
            not isinstance(boot_expect, list) or not boot_expect:
        raise AcceptanceError("workload commands, coverage, or banner is empty")
    names: set[str] = set()
    coverage: set[str] = set()
    for index, command in enumerate(commands, 1):
        if not isinstance(command, dict) or \
                not isinstance(command.get("name"), str) or \
                not isinstance(command.get("command"), str):
            raise AcceptanceError(f"workload command {index} is malformed")
        name = command["name"]
        if name in names:
            raise AcceptanceError(f"duplicate workload command name: {name}")
        names.add(name)
        expected = command.get("expect", [])
        steps = command.get("steps", [])
        if not isinstance(expected, list) or \
                not all(isinstance(value, str) for value in expected) or \
                not isinstance(steps, list):
            raise AcceptanceError(f"workload command {name} checks are malformed")
        for step in steps:
            if not isinstance(step, dict) or \
                    not isinstance(step.get("wait"), str) or \
                    not isinstance(step.get("send_hex"), str):
                raise AcceptanceError(f"workload command {name} step is malformed")
            bytes.fromhex(step["send_hex"])
        command_coverage = command.get("coverage", [])
        if not isinstance(command_coverage, list) or \
                not all(isinstance(value, str) for value in command_coverage):
            raise AcceptanceError(f"workload command {name} coverage is malformed")
        coverage.update(command_coverage)
    if coverage != set(required):
        missing = sorted(set(required) - coverage)
        extra = sorted(coverage - set(required))
        raise AcceptanceError(
            f"workload coverage differs; missing={missing}, extra={extra}"
        )
    runtime = load_json(RUNTIME_MEMORY)
    programs = runtime.get("programs")
    runtime_profile = "dev" if profile == "development" else profile
    admitted: set[str] = set()
    if profile == "display":
        admitted = {"VIDTEST.COM"}
    elif isinstance(programs, dict):
        admitted = {
            name for name, record in programs.items()
            if isinstance(record, dict)
            and record.get("profile") == runtime_profile
        }
    if not admitted or not admitted.issubset(coverage):
        raise AcceptanceError(
            "workload omits admitted runtime programs: "
            + ", ".join(sorted(admitted - coverage))
        )
    return path, workload


class EventLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.started = time.monotonic()
        self.stream = path.open("w", buffering=1)

    def emit(self, event: str, **fields: Any) -> None:
        monotonic = time.monotonic()
        record = {
            "at_utc": utc_now(),
            "monotonic_seconds": round(monotonic, 6),
            "elapsed_seconds": round(monotonic - self.started, 6),
            "event": event,
            **fields,
        }
        self.stream.write(json.dumps(record, sort_keys=True) + "\n")
        self.stream.flush()

    def close(self) -> None:
        self.stream.close()


class N4Console:
    """Binary N4 console with global paging and bounded marker waits."""

    def __init__(self, fd: int) -> None:
        self.fd = fd
        self.transcript = bytearray()
        self.page_scan = 0
        self.page_returns = 0

    def send(self, data: bytes) -> None:
        os.write(self.fd, data)

    def _receive(self, deadline: float) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        ready, _, _ = select.select([self.fd], [], [], min(0.1, remaining))
        if ready:
            incoming = os.read(self.fd, 4096)
            if incoming:
                self.transcript.extend(incoming)

    def wait_for(self, marker: bytes, *, start: int, timeout: float) \
            -> int:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshot = bytes(self.transcript)
            marker_at = snapshot.find(marker, start)
            page_at = snapshot.find(PAGE_PROMPT, self.page_scan)
            if page_at >= 0 and (marker_at < 0 or page_at < marker_at):
                self.send(b"\r")
                self.page_returns += 1
                self.page_scan = page_at + len(PAGE_PROMPT)
                continue
            if marker_at >= 0:
                return marker_at + len(marker)
            self._receive(deadline)
        raise ConsoleTimeout(marker, bytes(self.transcript[-512:]))


def response_record(name: str, command: str, start: int, end: int,
                    transcript: bytes, expected: list[str], prompt: str,
                    pages: int, started: float) -> dict[str, Any]:
    response = transcript[start:end]
    ended = time.monotonic()
    return {
        "name": name,
        "command": command,
        "result": "pass",
        "started_at_utc": utc_now(),
        "started_monotonic": round(started, 6),
        "ended_monotonic": round(ended, 6),
        "elapsed_seconds": round(ended - started, 6),
        "response_start": start,
        "response_end": end,
        "response_bytes": len(response),
        "response_sha256": sha256_bytes(response),
        "expected_markers": expected,
        "prompt": prompt,
        "page_returns": pages,
    }


def execute_workload(console: N4Console, workload: dict[str, Any], *,
                     operator_wait: float, command_timeout: float,
                     emit: Callable[..., None]) \
        -> tuple[dict[str, Any], list[dict[str, Any]]]:
    emit("target_wait_started", timeout_seconds=operator_wait)
    boot_started = time.monotonic()
    boot_end = console.wait_for(b"A>", start=0, timeout=operator_wait)
    boot_ended = time.monotonic()
    banner = bytes(console.transcript[:boot_end])
    expected_banner = list(workload["boot_expect"])
    missing_banner = [marker for marker in expected_banner
                      if marker.encode("ascii") not in banner]
    if missing_banner:
        raise WorkloadFailure(
            f"boot banner lacks {missing_banner}", [], {
                "result": "fail", "response_start": 0,
                "response_end": boot_end,
                "response_sha256": sha256_bytes(banner),
            },
        )
    boot = {
        "result": "pass",
        "started_monotonic": round(boot_started, 6),
        "ended_monotonic": round(boot_ended, 6),
        "elapsed_seconds": round(boot_ended - boot_started, 6),
        "response_start": 0,
        "response_end": boot_end,
        "response_bytes": len(banner),
        "response_sha256": sha256_bytes(banner),
        "expected_markers": expected_banner,
    }
    emit("target_prompt", elapsed_seconds=boot["elapsed_seconds"])
    commands: list[dict[str, Any]] = []
    for item in workload["commands"]:
        name = item["name"]
        command = item["command"]
        expected = list(item.get("expect", []))
        prompt = item.get("prompt", "A>")
        timeout = float(item.get("timeout", command_timeout))
        start = len(console.transcript)
        pages_before = console.page_returns
        started = time.monotonic()
        emit("command_started", name=name, command=command,
             timeout_seconds=timeout)
        console.send(command.encode("ascii") + b"\r")
        position = start
        try:
            for step_number, step in enumerate(item.get("steps", []), 1):
                position = console.wait_for(
                    step["wait"].encode("ascii"), start=position,
                    timeout=timeout,
                )
                delay = float(step.get("delay", 0))
                if delay:
                    time.sleep(delay)
                payload = bytes.fromhex(step["send_hex"])
                console.send(payload)
                emit("command_input", name=name, step=step_number,
                     bytes=len(payload), sha256=sha256_bytes(payload))
            end = console.wait_for(
                prompt.encode("ascii"), start=position, timeout=timeout,
            )
            transcript = bytes(console.transcript)
            response = transcript[start:end]
            missing = [marker for marker in expected
                       if marker.encode("ascii") not in response]
            if missing:
                raise AcceptanceError(f"target reply lacks {missing}")
            record = response_record(
                name, command, start, end, transcript, expected, prompt,
                console.page_returns - pages_before, started,
            )
            commands.append(record)
            emit("command_passed", name=name,
                 elapsed_seconds=record["elapsed_seconds"],
                 response_sha256=record["response_sha256"])
        except BaseException as error:
            transcript = bytes(console.transcript)
            response = transcript[start:]
            ended = time.monotonic()
            failed = {
                "name": name,
                "command": command,
                "result": "fail",
                "started_monotonic": round(started, 6),
                "ended_monotonic": round(ended, 6),
                "elapsed_seconds": round(ended - started, 6),
                "response_start": start,
                "response_end": len(transcript),
                "response_bytes": len(response),
                "response_sha256": sha256_bytes(response),
                "expected_markers": expected,
                "prompt": prompt,
                "page_returns": console.page_returns - pages_before,
                "failure": {"type": type(error).__name__, "message": str(error)},
            }
            commands.append(failed)
            emit("command_failed", name=name, failure=failed["failure"])
            raise WorkloadFailure(str(error), commands, boot) from error
    return boot, commands


def server_command(args: argparse.Namespace, artifacts: dict[str, Any],
                   working_volume: Path, console_pty: str,
                   boot_result: Path, request_trace: Path,
                   server: Path) -> list[str]:
    if not server.is_file():
        raise AcceptanceError(f"disk server is missing: {server}")
    return [
        sys.executable, str(server), args.serial,
        artifacts["system"]["path"], str(working_volume),
        "--fast-stage1", artifacts["fast_stage"]["path"],
        "--network-rom",
        "--boot-result-json", str(boot_result),
        "--request-trace-jsonl", str(request_trace),
        "--boot-manifest", artifacts["manifest"]["path"],
        "--drive-b", artifacts["drive_b"]["path"],
        "--disk-baud", "19200", "--disk-protocol", "3",
        "--disk-read-ahead-records", "8",
        "--media-mode", "write-through",
        "--console-pty", console_pty, "--console-trace",
        "--timeout", str(args.operator_wait),
        "--boot-restarts", "3",
        "--disk-timeout", str(args.session_timeout),
    ]


def load_request_trace(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    previous = -1.0
    for number, line in enumerate(path.read_text().splitlines(), 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise AcceptanceError(
                f"request trace line {number} is malformed: {error}"
            ) from error
        if not isinstance(record, dict) or \
                record.get("schema") != "juku-netdisk-request-trace-v1":
            raise AcceptanceError(f"request trace line {number} has bad schema")
        timestamp = record.get("monotonic_seconds")
        operation = record.get("operation")
        if not isinstance(timestamp, (int, float)) or timestamp < previous or \
                not isinstance(operation, int):
            raise AcceptanceError(
                f"request trace line {number} has invalid ordering or operation"
            )
        previous = float(timestamp)
        records.append(record)
    return records


def request_metrics(records: list[dict[str, Any]], start: float,
                    end: float) -> dict[str, int]:
    selected = [
        record for record in records
        if start <= float(record["monotonic_seconds"]) <= end
    ]
    reads = [record for record in selected
             if record["operation"] in DISK_READ_OPERATIONS]
    writes = [record for record in selected
              if record["operation"] in DISK_WRITE_OPERATIONS]
    return {
        "requests": len(selected),
        "disk_read_requests": len(reads),
        "disk_read_records": sum(int(record.get("records", 0))
                                 for record in reads),
        "disk_write_requests": len(writes),
        "disk_retries": sum(
            1 for record in (*reads, *writes) if record.get("duplicate") is True
        ),
        "request_wire_bytes": sum(int(record.get("request_bytes", 0))
                                  for record in selected),
        "reply_wire_bytes": sum(int(record.get("reply_bytes", 0))
                                for record in selected),
        "reads_a": sum(1 for record in reads if record.get("drive") == 0),
        "reads_b": sum(1 for record in reads if record.get("drive") == 1),
    }


def attach_request_metrics(boot: dict[str, Any],
                           commands: list[dict[str, Any]],
                           records: list[dict[str, Any]]) -> None:
    for item in (boot, *commands):
        start = item.get("started_monotonic")
        end = item.get("ended_monotonic")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            item["request_metrics"] = request_metrics(
                records, float(start), float(end),
            )


def snapshot_inputs(output: Path, artifacts: dict[str, Any],
                    workload: Path, server: Path) \
        -> tuple[dict[str, Any], Path, Path, dict[str, Any]]:
    inputs = output / "inputs"
    inputs.mkdir()
    snapped: dict[str, Any] = {
        "build_identity": artifacts["build_identity"],
    }
    for name in (
            "manifest", "system", "fast_stage", "volume", "drive_b", "rom",
            "rom_metadata"):
        source = Path(str(artifacts[name]["path"]))
        snapped[name] = snapshot_file(source, inputs / source.name)
        if snapped[name]["sha256"] != artifacts[name]["sha256"]:
            raise AcceptanceError(f"input snapshot differs while copying {name}")
    snapped_server = snapshot_file(server, inputs / server.name)
    snapped["host_server"] = snapped_server
    snapped_workload = inputs / "workload.json"
    snapshot_file(workload, snapped_workload)
    snapped_runner = snapshot_file(Path(__file__), inputs / "physical_acceptance.py")
    return snapped, snapped_workload, Path(snapped_server["path"]), snapped_runner


def validate_boot_result(boot: dict[str, Any], artifacts: dict[str, Any]) -> None:
    first = boot.get("first_disk_request")
    if boot.get("schema") != "juku-janet-boot-result-v1" or \
            boot.get("network_rom") is not True or \
            boot.get("effective_boot_baud") != 19200 or \
            boot.get("disk_baud") != 19200 or \
            boot.get("system_sha256") != artifacts["system"]["sha256"] or \
            boot.get("fast_stage_sha256") != \
            artifacts["fast_stage"]["sha256"] or \
            not isinstance(first, dict) or \
            float(first.get("elapsed_seconds", 0)) <= 0:
        raise AcceptanceError("boot result does not prove the bound C6/V16 run")


def host_tail(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_bytes()[-4096:].decode("utf-8", "replace")


def run_acceptance(args: argparse.Namespace) -> int:
    profile = args.profile
    artifacts = verify_manifest(args.manifest, args.cosim, profile)
    workload_path, workload = load_workload(profile, args.workload)
    output = args.output.resolve()
    working_volume = output / "working-a.img"
    boot_path = output / "boot.json"
    request_trace_path = output / "requests.jsonl"
    console_path = output / "console.bin"
    host_path = output / "host.log"
    events_path = output / "events.jsonl"
    result_path = output / "result.json"
    server = args.server.resolve() if args.server is not None else \
        args.cosim.resolve() / "tools/janet_disk_server.py"
    if not server.is_file():
        raise AcceptanceError(f"disk server is missing: {server}")
    artifacts["host_server"] = identity(server)
    master, slave = pty.openpty()
    tty.setraw(master)
    tty.setraw(slave)
    console_pty = os.ttyname(slave)
    command = server_command(
        args, artifacts, working_volume, console_pty, boot_path,
        request_trace_path, server,
    )
    if args.dry_run:
        os.close(master)
        os.close(slave)
        print(shlex.join(command))
        print(f"workload {profile}: {len(workload['commands'])} commands")
        return 0
    if output.exists():
        os.close(master)
        os.close(slave)
        raise AcceptanceError(f"output directory already exists: {output}")
    output.mkdir(parents=True)
    artifacts, workload_path, server, runner_snapshot = snapshot_inputs(
        output, artifacts, workload_path, server,
    )
    command = server_command(
        args, artifacts, working_volume, console_pty, boot_path,
        request_trace_path, server,
    )
    shutil.copyfile(Path(artifacts["volume"]["path"]), working_volume)
    volume_before = sha256(working_volume)
    events = EventLog(events_path)
    started_at = utc_now()
    console = N4Console(master)
    process: subprocess.Popen[str] | None = None
    reader: threading.Thread | None = None
    ready = threading.Event()
    boot_evidence: dict[str, Any] = {}
    commands: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None
    host: dict[str, Any] = {
        "command": command,
        "ready": False,
        "shutdown_signal": None,
        "forced_termination": False,
        "returncode": None,
        "clean_shutdown": False,
    }
    log_stream = host_path.open("w", buffering=1)
    log_stream.write("COMMAND " + shlex.join(command) + "\n")
    events.emit("run_started", profile=profile, board=args.board)
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", bufsize=1, start_new_session=True,
        )
        host["pid"] = process.pid
        events.emit("host_started", pid=process.pid)
        assert process.stdout is not None

        def capture_host() -> None:
            for line in process.stdout:
                print(line, end="")
                log_stream.write(line)
                log_stream.flush()
                if any(marker in line for marker in CONSOLE_READY_MARKERS):
                    ready.set()

        reader = threading.Thread(target=capture_host, daemon=True)
        reader.start()
        if not ready.wait(args.host_ready_timeout):
            raise AcceptanceError(
                "host did not advertise its N4 PTY; "
                f"returncode={process.poll()} tail={host_tail(host_path)!r}"
            )
        host["ready"] = True
        host["ready_at_utc"] = utc_now()
        events.emit("host_ready", console_pty=console_pty)
        os.close(slave)
        slave = -1
        boot_evidence, commands = execute_workload(
            console, workload, operator_wait=args.operator_wait,
            command_timeout=args.command_timeout, emit=events.emit,
        )
    except WorkloadFailure as error:
        commands = error.commands
        boot_evidence = error.boot
        failure = {"type": type(error).__name__, "message": str(error)}
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error)}
    finally:
        console_path.write_bytes(bytes(console.transcript))
        if process is not None and process.poll() is None:
            host["shutdown_signal"] = "SIGINT"
            events.emit("host_shutdown_requested", signal="SIGINT")
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=args.shutdown_timeout)
            except subprocess.TimeoutExpired:
                host["forced_termination"] = True
                events.emit("host_shutdown_forced", signal="SIGTERM")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        if process is not None:
            host["returncode"] = process.poll()
        if reader is not None:
            reader.join(timeout=5)
        log_stream.flush()
        log_stream.close()
        if slave >= 0:
            os.close(slave)
        os.close(master)

    host["clean_shutdown"] = (
        not host["forced_termination"]
        and host["returncode"] in (0, 130)
    )
    if failure is None and not host["clean_shutdown"]:
        failure = {
            "type": "HostShutdownError",
            "message": f"host return code {host['returncode']}",
        }
    boot_result: dict[str, Any] | None = None
    if boot_path.is_file():
        try:
            boot_result = load_json(boot_path)
            validate_boot_result(boot_result, artifacts)
        except BaseException as error:
            if failure is None:
                failure = {"type": type(error).__name__, "message": str(error)}
    elif failure is None:
        failure = {"type": "BootEvidenceError", "message": "boot.json missing"}
    request_records: list[dict[str, Any]] = []
    if request_trace_path.is_file():
        try:
            request_records = load_request_trace(request_trace_path)
            attach_request_metrics(boot_evidence, commands, request_records)
            if failure is None and \
                    boot_evidence.get("request_metrics", {}).get(
                        "disk_read_requests", 0,
                    ) <= 0:
                raise AcceptanceError(
                    "request trace does not prove boot disk reads"
                )
        except BaseException as error:
            if failure is None:
                failure = {"type": type(error).__name__, "message": str(error)}
    elif failure is None:
        failure = {
            "type": "RequestTraceError", "message": "requests.jsonl missing",
        }
    events.emit("run_finished", result="pass" if failure is None else "fail")
    events.close()
    result = {
        "schema": RESULT_SCHEMA,
        "session_schema": SCHEMA,
        "status": "pass" if failure is None else "fail",
        "profile": profile,
        "board": args.board,
        "started_at_utc": started_at,
        "ended_at_utc": utc_now(),
        "artifacts": artifacts,
        "repositories": {
            "cpm-plus-juku": git_state(ROOT),
            "8080-cosim": git_state(args.cosim.resolve()),
        },
        "runner": runner_snapshot,
        "workload": {
            **identity(workload_path),
            "name": workload["name"],
            "commands": len(workload["commands"]),
            "required_coverage": workload["required_coverage"],
        },
        "working_volume": {
            "path": str(working_volume),
            "sha256_before": volume_before,
            "sha256_after": sha256(working_volume),
        },
        "host": {
            **host,
            "log": {**identity(host_path), "path": "host.log"},
        },
        "events": {**identity(events_path), "path": "events.jsonl"},
        "requests": ({**identity(request_trace_path), "path": "requests.jsonl"}
                     if request_trace_path.is_file() else None),
        "console": {**identity(console_path), "path": "console.bin"},
        "boot": boot_evidence,
        "boot_result": boot_result,
        "boot_result_file": identity(boot_path) if boot_path.is_file() else None,
        "commands": commands,
        "failure": failure,
    }
    if failure is not None:
        result["failure"]["console_tail_hex"] = \
            bytes(console.transcript[-512:]).hex()
        result["failure"]["host_tail"] = host_tail(host_path)
    write_json(result_path, result)
    print(
        f"PHYSICAL-ACCEPTANCE: {result['status'].upper()} "
        f"{profile} ({len(commands)}/{len(workload['commands'])} commands); "
        f"evidence={output}"
    )
    return 0 if failure is None else 1


def audit_directory(directory: Path) -> list[str]:
    directory = directory.resolve()
    result = load_json(directory / "result.json")
    failures: list[str] = []
    if result.get("schema") != RESULT_SCHEMA or result.get("status") != "pass":
        failures.append("result is not a passing physical acceptance record")
        return failures
    profile = result.get("profile")
    if profile not in PROFILE_VOLUMES:
        failures.append("result profile is invalid")
        return failures
    workload_entry = result.get("workload", {})
    workload_path = Path(str(workload_entry.get("path", "")))
    try:
        checked_path, workload = load_workload(str(profile), workload_path)
        if sha256(checked_path) != workload_entry.get("sha256"):
            failures.append("workload changed after the run")
    except BaseException as error:
        failures.append(f"workload cannot be verified: {error}")
        return failures
    runner = result.get("runner", {})
    runner_path = Path(str(runner.get("path", "")))
    if not runner_path.is_file() or \
            runner_path.stat().st_size != runner.get("bytes") or \
            sha256(runner_path) != runner.get("sha256"):
        failures.append("runner snapshot changed")
    for key in ("console", "events", "requests"):
        entry = result.get(key, {})
        if not isinstance(entry, dict):
            failures.append(f"{key} evidence is missing")
            continue
        path = directory / str(entry.get("path", ""))
        if not path.is_file() or path.stat().st_size != entry.get("bytes") or \
                sha256(path) != entry.get("sha256"):
            failures.append(f"{key} evidence changed")
    event_path = directory / str(result.get("events", {}).get("path", ""))
    event_names: list[str] = []
    if event_path.is_file():
        try:
            event_names = [
                json.loads(line)["event"]
                for line in event_path.read_text().splitlines() if line
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            failures.append(f"event log is malformed: {error}")
    for event in (
            "run_started", "host_started", "host_ready", "target_prompt",
            "host_shutdown_requested", "run_finished"):
        if event not in event_names:
            failures.append(f"host/target lifecycle event is missing: {event}")
    host = result.get("host", {})
    host_log = host.get("log", {}) if isinstance(host, dict) else {}
    host_path = directory / str(host_log.get("path", ""))
    if not host_path.is_file() or sha256(host_path) != host_log.get("sha256"):
        failures.append("host log changed")
    if not isinstance(host, dict) or not host.get("ready") or \
            not host.get("clean_shutdown") or \
            host.get("forced_termination") or \
            host.get("returncode") not in (0, 130):
        failures.append("host lifecycle is incomplete or unclean")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        failures.append("artifact identities are missing")
        return failures
    for name in (
            "manifest", "system", "fast_stage", "volume", "drive_b", "rom",
            "rom_metadata", "host_server"):
        entry = artifacts.get(name, {})
        path = Path(str(entry.get("path", "")))
        if not path.is_file() or path.stat().st_size != entry.get("bytes") or \
                sha256(path) != entry.get("sha256"):
            failures.append(f"bound artifact changed: {name}")
    working = result.get("working_volume", {})
    working_path = Path(str(working.get("path", "")))
    if working.get("sha256_before") != artifacts["volume"].get("sha256") or \
            not working_path.is_file() or \
            working_path.parent.resolve() != directory or \
            sha256(working_path) != working.get("sha256_after"):
        failures.append("private writable A: chain differs")
    boot_result = result.get("boot_result")
    try:
        if not isinstance(boot_result, dict):
            raise AcceptanceError("boot result is missing")
        validate_boot_result(boot_result, artifacts)
    except BaseException as error:
        failures.append(f"boot evidence differs: {error}")
    boot_file = result.get("boot_result_file")
    if not isinstance(boot_file, dict):
        failures.append("boot result file identity is missing")
    else:
        boot_path = Path(str(boot_file.get("path", "")))
        if not boot_path.is_file() or \
                boot_path.stat().st_size != boot_file.get("bytes") or \
                sha256(boot_path) != boot_file.get("sha256"):
            failures.append("boot result file changed")
    console_entry = result.get("console", {})
    console_path = directory / str(console_entry.get("path", ""))
    transcript = console_path.read_bytes() if console_path.is_file() else b""
    boot = result.get("boot", {})
    boot_start = boot.get("response_start") if isinstance(boot, dict) else None
    boot_end = boot.get("response_end") if isinstance(boot, dict) else None
    if not isinstance(boot_start, int) or not isinstance(boot_end, int) or \
            not 0 <= boot_start <= boot_end <= len(transcript):
        failures.append("target boot transcript offsets differ")
    else:
        boot_response = transcript[boot_start:boot_end]
        if sha256_bytes(boot_response) != boot.get("response_sha256"):
            failures.append("target boot transcript hash differs")
        for marker in workload["boot_expect"]:
            if marker.encode("ascii") not in boot_response:
                failures.append(f"target boot banner lacks {marker!r}")
    commands = result.get("commands")
    if not isinstance(commands, list) or len(commands) != len(workload["commands"]):
        failures.append("command result count differs from the workload")
        return failures
    for expected_command, command in zip(workload["commands"], commands):
        if not isinstance(command, dict) or command.get("result") != "pass" or \
                command.get("name") != expected_command["name"] or \
                command.get("command") != expected_command["command"]:
            failures.append(f"command did not pass: {expected_command['name']}")
            continue
        start = command.get("response_start")
        end = command.get("response_end")
        if not isinstance(start, int) or not isinstance(end, int) or \
                not 0 <= start <= end <= len(transcript):
            failures.append(f"command offsets differ: {command['name']}")
            continue
        response = transcript[start:end]
        if sha256_bytes(response) != command.get("response_sha256"):
            failures.append(f"command reply hash differs: {command['name']}")
        prompt = expected_command.get("prompt", "A>")
        if prompt.encode("ascii") not in response:
            failures.append(f"command prompt is missing: {command['name']}")
        for marker in expected_command.get("expect", []):
            if marker.encode("ascii") not in response:
                failures.append(
                    f"command reply lacks {marker!r}: {command['name']}"
                )
    request_entry = result.get("requests", {})
    request_path = directory / str(request_entry.get("path", "")) \
        if isinstance(request_entry, dict) else Path()
    try:
        records = load_request_trace(request_path)
        metric_records = [boot, *commands]
        for record in metric_records:
            start = record.get("started_monotonic")
            end = record.get("ended_monotonic")
            if not isinstance(start, (int, float)) or \
                    not isinstance(end, (int, float)):
                failures.append("request-metric time boundary is missing")
                continue
            expected_metrics = request_metrics(records, float(start), float(end))
            if record.get("request_metrics") != expected_metrics:
                failures.append("request metrics differ from retained trace")
        if boot.get("request_metrics", {}).get("disk_read_requests", 0) <= 0:
            failures.append("boot request trace has no disk reads")
    except BaseException as error:
        failures.append(f"request trace cannot be verified: {error}")
    if event_names.count("command_started") != len(commands) or \
            event_names.count("command_passed") != len(commands):
        failures.append("command lifecycle event count differs")
    return failures


def audit(args: argparse.Namespace) -> int:
    failures = audit_directory(args.directory)
    if failures:
        print("PHYSICAL-ACCEPTANCE-AUDIT: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    result = load_json(args.directory.resolve() / "result.json")
    print(
        "PHYSICAL-ACCEPTANCE-AUDIT: PASS "
        f"({result['profile']}, {len(result['commands'])} target commands)"
    )
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="action_name", required=True)
    run_parser = commands.add_parser("run", help="run one physical workload")
    run_parser.add_argument("serial")
    run_parser.add_argument("--profile", choices=tuple(PROFILE_VOLUMES),
                            required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    run_parser.add_argument("--workload", type=Path)
    run_parser.add_argument("--cosim", type=Path, default=DEFAULT_COSIM)
    run_parser.add_argument(
        "--server", type=Path,
        help="override the host executable for a controlled regression",
    )
    run_parser.add_argument("--board", default="CS00015")
    run_parser.add_argument("--operator-wait", type=float, default=1800)
    run_parser.add_argument("--host-ready-timeout", type=float, default=30)
    run_parser.add_argument("--command-timeout", type=float, default=600)
    run_parser.add_argument("--session-timeout", type=float, default=10800)
    run_parser.add_argument("--shutdown-timeout", type=float, default=20)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.set_defaults(action=run_acceptance)
    audit_parser = commands.add_parser("audit", help="recheck retained evidence")
    audit_parser.add_argument("directory", type=Path)
    audit_parser.set_defaults(action=audit)
    return result


def main() -> int:
    args = parser().parse_args()
    return int(args.action(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AcceptanceError, OSError, subprocess.SubprocessError,
            TypeError, ValueError) as error:
        print(f"physical-acceptance: {error}", file=sys.stderr)
        raise SystemExit(1)
