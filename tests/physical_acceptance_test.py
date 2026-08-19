#!/usr/bin/env python3
"""Exercise C6 physical workload, lifecycle, evidence, and audit boundaries."""

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
            os.write(slave, b"\r\nOK\r\nA>")
            assert read_command(slave) == b"INTERACT\r"
            os.write(slave, b"READY")
            assert read_command(slave) == b"A\r"
            os.write(slave, b"DONE\r\nA>")
        except BaseException as error:
            failures.append(error)

    worker = threading.Thread(target=target)
    worker.start()
    workload = {
        "boot_expect": ["CP/M Plus 3.1 Juku", "N3 19200"],
        "commands": [
            {"name": "paged", "command": "PAGER", "expect": ["OK"]},
            {"name": "interactive", "command": "INTERACT",
             "steps": [{"wait": "READY", "send_hex": "41 0d"}],
             "expect": ["DONE"]},
        ],
    }
    events: list[tuple[str, dict[str, object]]] = []
    console = acceptance.N4Console(master)
    boot, commands = acceptance.execute_workload(
        console, workload, operator_wait=2, command_timeout=2,
        emit=lambda event, **fields: events.append((event, fields)),
    )
    worker.join(timeout=2)
    os.close(master)
    os.close(slave)
    if worker.is_alive() or failures:
        raise AssertionError(f"synthetic target failed: {failures}")
    if boot["result"] != "pass" or console.page_returns != 1 or \
            [item["result"] for item in commands] != ["pass", "pass"] or \
            commands[0]["page_returns"] != 1 or \
            not any(event == "command_input" for event, _ in events):
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


def fake_server_source() -> str:
    return r'''#!/usr/bin/env python3
import hashlib, json, os, signal, sys, time

def option(name):
    return sys.argv[sys.argv.index(name) + 1]

fd = os.open(option("--console-pty"), os.O_RDWR | os.O_NOCTTY)
system = sys.argv[2]
stage = option("--fast-stage1")
boot = {
    "schema": "juku-janet-boot-result-v1",
    "network_rom": True,
    "effective_boot_baud": 19200,
    "disk_baud": 19200,
    "system_sha256": hashlib.sha256(open(system, "rb").read()).hexdigest(),
    "fast_stage_sha256": hashlib.sha256(open(stage, "rb").read()).hexdigest(),
    "first_disk_request": {"elapsed_seconds": 0.125}
}
open(option("--boot-result-json"), "w").write(json.dumps(boot) + "\n")
print("Advertising N4 remote console on fake; awaiting target", flush=True)
time.sleep(0.05)
trace = {
    "schema": "juku-netdisk-request-trace-v1",
    "monotonic_seconds": time.monotonic(),
    "elapsed_seconds": 0.125,
    "operation": 0x14,
    "sequence": 1,
    "drive": 0,
    "track": 2,
    "sector": 1,
    "status": 0,
    "records": 8,
    "request_bytes": 10,
    "reply_bytes": 549,
    "encoding": "v3-ahead-8",
    "duplicate": False,
}
open(option("--request-trace-jsonl"), "w").write(json.dumps(trace) + "\n")
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
            raise AssertionError(
                f"fake physical run failed:\n{completed.stdout}\n{completed.stderr}"
            )
        failures = acceptance.audit_directory(output)
        if failures:
            raise AssertionError(f"retained physical evidence failed: {failures}")
        result = json.loads((output / "result.json").read_text())
        if not result["host"]["clean_shutdown"] or \
                result["host"]["shutdown_signal"] != "SIGINT" or \
                result["commands"][0]["page_returns"] != 1 or \
                result["boot"]["request_metrics"]["disk_read_requests"] != 1:
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
    for profile, minimum_commands in (
        ("full", 29), ("development", 10), ("display", 1),
    ):
        artifacts = acceptance.verify_manifest(
            acceptance.DEFAULT_MANIFEST, acceptance.DEFAULT_COSIM, profile,
        )
        _, workload = acceptance.load_workload(profile)
        if len(workload["commands"]) < minimum_commands or \
                artifacts["volume"]["sha256"] == \
                artifacts["drive_b"]["sha256"]:
            raise AssertionError(f"{profile} workload/artifact binding differs")
    workload_executor_test()
    timeout_diagnostic_test()
    lifecycle_and_audit_test()
    print("PHYSICAL-ACCEPTANCE-TEST: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
