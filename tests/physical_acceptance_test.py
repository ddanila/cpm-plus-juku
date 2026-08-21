#!/usr/bin/env python3
"""Exercise manifest-bound physical workload and audit boundaries."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pty
import subprocess
import sys
import tempfile
import threading
import time
import tty


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/physical_acceptance.py"
sys.path.insert(0, str(ROOT / "tools"))
import physical_acceptance as acceptance  # noqa: E402


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def read_command(fd: int) -> bytes:
    result = bytearray()
    while not result.endswith(b"\r"):
        result.extend(os.read(fd, 64))
    return bytes(result)


def workload_executor_test() -> None:
    master, slave = pty.openpty()
    tty.setraw(master)
    tty.setraw(slave)
    failures: list[BaseException] = []

    def target() -> None:
        try:
            os.write(slave, b"CP/M Plus 3.1 Juku\r\nN3 19200\r\nA>")
            assert read_command(slave) == b"PAGER\r"
            os.write(slave, b"PAGER\r\nPress RETURN to Continue")
            assert read_command(slave) == b"\r"
            os.write(slave, b"\r\nPress RETURN to continue")
            assert read_command(slave) == b"\r"
            os.write(slave, b"\r\nOK\r\nA>")
            assert read_command(slave) == b"INTERACT\r"
            os.write(slave, b"READY")
            assert read_command(slave) == b"A\r"
            os.write(slave, b"PHYSICAL")
        except BaseException as error:
            failures.append(error)

    worker = threading.Thread(target=target)
    worker.start()
    workload = {
        "boot_expect": ["CP/M Plus 3.1 Juku", "N3 19200"],
        "commands": [
            {"name": "paged", "command": "PAGER", "expect": ["OK"]},
            {"name": "interactive", "command": "INTERACT",
             "steps": [
                 {"wait": "READY", "send_hex": "41 0d"},
                 {"wait": "PHYSICAL", "operator": "Press test key."},
             ],
             "expect": ["DONE"]},
        ],
    }
    events: list[tuple[str, dict[str, object]]] = []
    operator_actions: list[str] = []

    def operator_confirm(instruction: str) -> None:
        operator_actions.append(instruction)
        os.write(slave, b"DONE\r\nA>")

    console = acceptance.N4Console(master)
    boot, commands = acceptance.execute_workload(
        console, workload, operator_wait=2, command_timeout=2,
        emit=lambda event, **fields: events.append((event, fields)),
        operator_confirm=operator_confirm,
    )
    worker.join(timeout=2)
    os.close(master)
    os.close(slave)
    if worker.is_alive() or failures:
        raise AssertionError(f"synthetic target failed: {failures}")
    if boot["result"] != "pass" or console.page_returns != 2 or \
            [item["result"] for item in commands] != ["pass", "pass"] or \
            commands[0]["page_returns"] != 2 or \
            operator_actions != ["Press test key."] or \
            not any(event == "command_input" for event, _ in events) or \
            not any(event == "operator_action_confirmed"
                    for event, _ in events):
        raise AssertionError("paging/interactive workload evidence differs")


def timeout_diagnostic_test() -> None:
    master, slave = pty.openpty()
    tty.setraw(master)
    tty.setraw(slave)

    def target() -> None:
        os.write(slave, b"CP/M Plus 3.1 Juku\r\nN3 19200\r\nA>")
        assert read_command(slave) == b"STALL\r"

    worker = threading.Thread(target=target)
    worker.start()
    console = acceptance.N4Console(master)
    try:
        acceptance.execute_workload(
            console,
            {"boot_expect": ["N3 19200"], "commands": [
                {"name": "stall", "command": "STALL", "expect": ["DONE"]},
            ]},
            operator_wait=1, command_timeout=0.1,
            emit=lambda _event, **_fields: None,
        )
    except acceptance.WorkloadFailure as error:
        if len(error.commands) != 1 or \
                error.commands[0]["failure"]["type"] != "ConsoleTimeout" or \
                "console tail" not in error.commands[0]["failure"]["message"]:
            raise AssertionError("timeout diagnostic lacks target state")
    else:
        raise AssertionError("stalled target was accepted")
    worker.join(timeout=1)
    os.close(master)
    os.close(slave)


def delayed_console_open_test() -> None:
    """The native host opens N4 only after a potentially long Fastboot."""
    master, slave = pty.openpty()
    tty.setraw(master)
    tty.setraw(slave)
    slave_path = os.ttyname(slave)
    os.close(slave)
    failures: list[BaseException] = []

    def target() -> None:
        fd = -1
        try:
            time.sleep(0.05)
            fd = os.open(slave_path, os.O_RDWR | os.O_NOCTTY)
            tty.setraw(fd)
            os.write(fd, b"A>")
        except BaseException as error:
            failures.append(error)
        finally:
            if fd >= 0:
                os.close(fd)

    worker = threading.Thread(target=target)
    worker.start()
    console = acceptance.N4Console(master)
    end = console.wait_for(b"A>", start=0, timeout=1)
    worker.join(timeout=1)
    os.close(master)
    if end != 2 or worker.is_alive() or failures:
        raise AssertionError(f"delayed PTY slave was not accepted: {failures}")


def resume_workload_test() -> None:
    master, slave = pty.openpty()
    tty.setraw(master)
    tty.setraw(slave)
    failures: list[BaseException] = []

    def target() -> None:
        try:
            assert read_command(slave) == b"\r"
            os.write(slave, b"\r\nA>")
            assert read_command(slave) == b"DIR\r"
            os.write(slave, b"DIR\r\nDIAG COM\r\nA>")
        except BaseException as error:
            failures.append(error)

    worker = threading.Thread(target=target)
    worker.start()
    events: list[str] = []
    console = acceptance.N4Console(master)
    boot, commands = acceptance.execute_workload(
        console,
        {"boot_expect": ["A>"], "commands": [
            {"name": "dir", "command": "DIR", "expect": ["DIAG"]},
        ]},
        operator_wait=2, command_timeout=2, resume=True,
        emit=lambda event, **_fields: events.append(event),
    )
    worker.join(timeout=2)
    os.close(master)
    os.close(slave)
    if worker.is_alive() or failures or boot["result"] != "pass" or \
            commands[0]["result"] != "pass" or \
            "resume_probe_queued" not in events:
        raise AssertionError(f"synthetic resume failed: {failures}")


def host_snapshot_test() -> None:
    server = acceptance.DEFAULT_COSIM / "build/jukuhost"
    with tempfile.TemporaryDirectory(prefix="physical-host-snapshot.") as name:
        inputs = Path(name)
        snapped, dependencies = acceptance.snapshot_host(server, inputs)
        if dependencies:
            raise AssertionError("native host unexpectedly has script dependencies")
        completed = subprocess.run(
            [snapped["path"], "--help"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if completed.returncode != 0 or "usage: jukuhost" not in completed.stdout:
            raise AssertionError(
                "snapshotted disk server is not independently executable:\n"
                + completed.stdout
            )


def operator_wait_budget_test() -> None:
    args = acceptance.parser().parse_args([
        "run", "/dev/null", "--profile", "full", "--output", "/tmp/out",
        "--operator-wait", "1800",
    ])
    artifacts = acceptance.verify_manifest(
        acceptance.DEFAULT_MANIFEST, acceptance.DEFAULT_COSIM, "full",
    )
    command = acceptance.server_command(
        args, artifacts, Path("/tmp/volume.img"), "/dev/pts/0",
        Path("/tmp/requests.jsonl"),
        acceptance.DEFAULT_COSIM / "build/jukuhost",
    )
    restart_index = command.index("--boot-restarts") + 1
    timeout_index = command.index("--timeout") + 1
    if command[restart_index] != "3" or command[timeout_index] != "1800" or \
            "serving A:" not in acceptance.CONSOLE_READY_MARKERS:
        raise AssertionError("operator wait is not bound to pre-boot retries")

    resume_args = acceptance.parser().parse_args([
        "run", "/dev/null", "--profile", "c8-reconnect",
        "--output", "/tmp/out", "--resume",
    ])
    resume_artifacts = acceptance.verify_manifest(
        ROOT / "out/cpm-plus-juku-c8-manifest.json",
        acceptance.DEFAULT_COSIM, "c8-reconnect",
    )
    resume_command = acceptance.server_command(
        resume_args, resume_artifacts, Path("/tmp/volume.img"),
        "/dev/pts/0", Path("/tmp/requests.jsonl"),
        acceptance.DEFAULT_COSIM / "build/jukuhost",
    )
    if "--resume-disk" not in resume_command or \
            "--network-rom" in resume_command or \
            "--fast-stage" in resume_command:
        raise AssertionError("resume server command contains cold-boot options")


def request_clock_alignment_test() -> None:
    records = [
        {"monotonic_seconds": 930014.0, "elapsed_seconds": 14.0,
         "operation": 0x14, "records": 8, "drive": 0},
        {"monotonic_seconds": 930020.0, "elapsed_seconds": 20.0,
         "operation": 0x14, "records": 8, "drive": 0},
    ]
    aligned = acceptance.align_request_trace(records, 0.05)
    metrics = acceptance.request_metrics(aligned, 13.0, 21.0)
    if aligned[0]["monotonic_seconds"] != 14.05 or \
            aligned[1]["monotonic_seconds"] != 20.05 or \
            metrics["disk_read_requests"] != 2 or \
            metrics["disk_read_records"] != 16:
        raise AssertionError("host/runner clock epochs were not aligned")


def fake_server_source() -> str:
    return r'''#!/usr/bin/env python3
import os, signal, struct, sys, time, zlib

def option(name):
    return sys.argv[sys.argv.index(name) + 1]

fd = os.open(option("--console-pty"), os.O_RDWR | os.O_NOCTTY)
started = int(time.monotonic() * 1000)

def event(elapsed, text):
    payload = text.encode("ascii")
    header = struct.pack("<BBHQ", 3, 1, len(payload), elapsed)
    body = header + payload
    return body + struct.pack("<I", zlib.crc32(body))

capture = b"JHCAP1\x01\0" + struct.pack("<Q", started)
capture += event(5, "Fastboot V16 complete: 123 compressed bytes")
capture += event(
    370,
    "request op=14 seq=01 drive=0 track=2 sector=1 status=0 "
    "records=8 request-bytes=9 reply-bytes=549 duplicate=0",
)
open(option("--capture"), "wb").write(capture)
open(option("--log"), "w").write("00000000 INFO  fake native log\n")
print("00000125 INFO  serving A: fake, 19200 baud 8O1, N3", flush=True)
time.sleep(0.05)
os.write(fd, b"CP/M Plus 3.1 Juku\r\nN3 19200\r\nA>")

def read_command():
    data = bytearray()
    while not data.endswith(b"\r"):
        data.extend(os.read(fd, 64))
    return bytes(data)

assert read_command() == b"PAGER\r"
os.write(fd, b"PAGER\r\nPress RETURN to Continue")
assert read_command() == b"\r"
os.write(fd, b"\r\nOK\r\nA>")
assert read_command() == b"INTERACT\r"
os.write(fd, b"READY")
assert read_command() == b"A\r"
os.write(fd, b"DONE\r\nA>")
stopped = False
def stop(_signum, _frame):
    global stopped
    stopped = True
signal.signal(signal.SIGINT, stop)
while not stopped:
    time.sleep(0.01)
os.close(fd)
print("fake host stopped cleanly", flush=True)
'''


def lifecycle_and_audit_test() -> None:
    with tempfile.TemporaryDirectory(prefix="physical-acceptance.") as name:
        temporary = Path(name)
        workload = temporary / "workload.json"
        admitted = [
            "DATE.COM", "DEVICE.COM", "DUMP.COM", "HELP.COM", "PIP.COM",
            "SET.COM", "SETDEF.COM", "SHOW.COM", "SUBMIT.COM",
        ]
        write_json(workload, {
            "schema": acceptance.WORKLOAD_SCHEMA,
            "name": "full",
            "volume_profile": "full-a",
            "boot_expect": ["CP/M Plus 3.1 Juku", "N3 19200"],
            "required_coverage": admitted,
            "commands": [
                {"name": "paged", "command": "PAGER", "expect": ["OK"],
                 "coverage": admitted},
                {"name": "interactive", "command": "INTERACT",
                 "steps": [{"wait": "READY", "send_hex": "41 0d"}],
                 "expect": ["DONE"]},
            ],
        })
        fake_server = temporary / "fake_server.py"
        fake_server.write_text(fake_server_source())
        fake_server.chmod(0o755)
        output = temporary / "result"
        completed = subprocess.run([
            sys.executable, str(TOOL), "run", "/dev/null",
            "--profile", "full", "--output", str(output),
            "--workload", str(workload), "--server", str(fake_server),
            "--operator-wait", "2", "--host-ready-timeout", "2",
            "--command-timeout", "2", "--session-timeout", "10",
            "--shutdown-timeout", "2",
        ], cwd=ROOT, text=True, capture_output=True)
        if completed.returncode != 0:
            retained = (output / "result.json").read_text() \
                if (output / "result.json").is_file() else "<missing result>"
            raise AssertionError(
                f"fake physical run failed:\n{completed.stdout}\n"
                f"{completed.stderr}\n{retained}"
            )
        failures = acceptance.audit_directory(output)
        if failures:
            raise AssertionError(f"retained physical evidence failed: {failures}")
        result = json.loads((output / "result.json").read_text())
        if not result["host"]["clean_shutdown"] or \
                result["host"]["shutdown_signal"] != "SIGINT" or \
                Path(result["working_volume"]["path"]).name != \
                "cpm-plus-juku-full.img" or \
                result["commands"][0]["page_returns"] != 1 or \
                result["boot"]["request_metrics"]["disk_read_requests"] != 1 or \
                result["boot"]["request_metrics"][
                    "elapsed_from_first_disk_request"
                ] is None:
            raise AssertionError(
                "host lifecycle, paging, or request metrics differ"
            )
        console = output / "console.bin"
        original = console.read_bytes()
        console.write_bytes(original + b"tampered")
        if not any("console evidence changed" in failure
                   for failure in acceptance.audit_directory(output)):
            raise AssertionError("changed console evidence was accepted")
        console.write_bytes(original)
        request_trace = output / "requests.jsonl"
        trace_original = request_trace.read_bytes()
        request_trace.write_bytes(trace_original + b"{}\n")
        if not any("requests evidence changed" in failure
                   for failure in acceptance.audit_directory(output)):
            raise AssertionError("changed request trace was accepted")
        request_trace.write_bytes(trace_original)
        result["commands"][0]["result"] = "fail"
        write_json(output / "result.json", result)
        if not any("command did not pass" in failure
                   for failure in acceptance.audit_directory(output)):
            raise AssertionError("failed target command was accepted")


def main() -> int:
    c7_manifest = ROOT / "out/cpm-plus-juku-c7-manifest.json"
    c8_manifest = ROOT / "out/cpm-plus-juku-c8-manifest.json"
    for profile, minimum_commands, manifest in (
        ("full", 30, acceptance.DEFAULT_MANIFEST),
        ("development", 10, acceptance.DEFAULT_MANIFEST),
        ("display", 1, acceptance.DEFAULT_MANIFEST),
        ("performance", 10, acceptance.DEFAULT_MANIFEST),
        ("c7-raw", 5, c7_manifest),
        ("c8-blind", 15, c8_manifest),
        ("c8-reconnect", 15, c8_manifest),
        ("c8-attended", 7, c8_manifest),
        ("c8-cold", 4, c8_manifest),
    ):
        artifacts = acceptance.verify_manifest(
            manifest, acceptance.DEFAULT_COSIM, profile,
        )
        _, workload = acceptance.load_workload(profile)
        if len(workload["commands"]) < minimum_commands or \
                artifacts["volume"]["sha256"] == \
                artifacts["drive_b"]["sha256"]:
            raise AssertionError(f"{profile} workload/artifact binding differs")
    workload_executor_test()
    timeout_diagnostic_test()
    delayed_console_open_test()
    resume_workload_test()
    host_snapshot_test()
    operator_wait_budget_test()
    request_clock_alignment_test()
    lifecycle_and_audit_test()
    print("PHYSICAL-ACCEPTANCE-TEST: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
