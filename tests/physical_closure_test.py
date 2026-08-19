#!/usr/bin/env python3
"""Prove the combined blind physical-closure contract fails closed."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import physical_closure as closure  # noqa: E402
import physical_performance as performance  # noqa: E402


def metrics(reads: int, records: int, *, writes: int = 0) \
        -> dict[str, object]:
    return {
        "disk_read_requests": reads,
        "disk_read_records": records,
        "disk_write_requests": writes,
        "disk_retries": 0,
        "disk_request_wire_bytes": reads * 9 + writes * 137,
        "disk_reply_wire_bytes": records * 64 + writes * 7,
        "elapsed_from_first_disk_request": 1.0 if reads or writes else None,
    }


def performance_result(role: str) -> dict[str, object]:
    control = role == "control"
    phases = {
        "dir-a": metrics(0, 0),
        "type-readme": metrics(1, 8),
        "select-b": metrics(4, 32),
        "dir-b": metrics(1 if control else 0, 8 if control else 0),
        "select-a": metrics(0, 0),
        "diag-cpu": metrics(1, 8),
        "diag-usart": metrics(1, 8),
        "warm-boot": metrics(2, 16),
        "erase-readme": metrics(1, 8, writes=1),
        "dir-after-erase": metrics(0, 0),
    }
    return {
        "status": "pass",
        "profile": "performance",
        "board": "CS00015",
        "artifacts": {
            "system": {"sha256": performance.CONTROL_SYSTEM if control
                       else performance.OPTIMIZED_SYSTEM},
            "fast_stage": {"sha256": performance.CONTROL_FASTBOOT if control
                           else performance.OPTIMIZED_FASTBOOT},
            "volume": {"sha256": performance.RECOVERY_VOLUME},
            "rom": {"sha256": closure.ROM},
            "host_server": {"sha256": "server"},
        },
        "workload": {"sha256": performance.WORKLOAD},
        "boot": {"request_metrics": metrics(10 if control else 8,
                                             80 if control else 64),
                 "elapsed_seconds": 4.0},
        "commands": [
            {"name": name, "result": "pass", "request_metrics": value,
             "elapsed_seconds": 1.0}
            for name, value in phases.items()
        ],
    }


def profile_result(role: str) -> dict[str, object]:
    full = role == "full"
    names = (
        ("pip-copy", "crc-copy", "pip-copy-repeat", "crc-copy-repeat")
        if full else ("hexcom", "hello", "sid", "patch", "ed", "type-ed")
    )
    records = []
    for name in names:
        record: dict[str, object] = {"name": name, "result": "pass"}
        if name.startswith("crc-copy"):
            record["expected_markers"] = [closure.CRC_MARKER]
        records.append(record)
    return {
        "status": "pass",
        "profile": role,
        "board": "CS00015",
        "artifacts": {
            "system": {"sha256": performance.OPTIMIZED_SYSTEM},
            "fast_stage": {"sha256": performance.OPTIMIZED_FASTBOOT},
            "rom": {"sha256": closure.ROM},
            "volume": {"sha256": closure.FULL_VOLUME if full
                       else closure.DEVELOPMENT_VOLUME},
            "host_server": {"sha256": "server"},
        },
        "workload": {"sha256": closure.FULL_WORKLOAD if full
                     else closure.DEVELOPMENT_WORKLOAD},
        "boot": {"elapsed_seconds": 10.0},
        "commands": records,
    }


def rejected(full: dict[str, object], development: dict[str, object],
             control: dict[str, object], optimized: dict[str, object],
             label: str) -> None:
    try:
        closure.close(full, development, control, optimized)
    except (closure.ClosureError, performance.ComparisonError):
        return
    raise AssertionError(f"physical closure accepted {label}")


def retained_report_test() -> None:
    with tempfile.TemporaryDirectory(prefix="physical-closure.") as name:
        base = Path(name)
        results = {
            "full": profile_result("full"),
            "development": profile_result("development"),
            "control": performance_result("control"),
            "optimized": performance_result("optimized"),
        }
        directories = {}
        for role, result in results.items():
            directory = base / role
            directory.mkdir()
            (directory / "result.json").write_text(
                json.dumps(result, indent=2) + "\n",
            )
            directories[role] = directory
        with patch.object(closure.acceptance, "audit_directory", return_value=[]):
            report = closure.build_report(directories)
            if closure.audit_report(report) != report:
                raise AssertionError("retained closure report changed")
            broken = copy.deepcopy(report)
            broken["decision"] = "edited"
            try:
                closure.audit_report(broken)
            except closure.ClosureError:
                pass
            else:
                raise AssertionError("edited closure report was accepted")
            original = (directories["full"] / "result.json").read_text()
            (directories["full"] / "result.json").write_text(original + " ")
            try:
                closure.audit_report(report)
            except closure.ClosureError:
                pass
            else:
                raise AssertionError("changed closure input was accepted")


def main() -> int:
    full = profile_result("full")
    development = profile_result("development")
    control = performance_result("control")
    optimized = performance_result("optimized")
    report = closure.close(full, development, control, optimized)
    if report.get("status") != "pass" or \
            report["performance"]["delta"]["boot_read_requests"] != -2 or \
            report["remaining"] != ["four-mode analog display observation"]:
        raise AssertionError("physical closure summary differs")

    broken = copy.deepcopy(full)
    broken["artifacts"]["system"]["sha256"] = "wrong"
    rejected(broken, development, control, optimized, "wrong full system")
    broken = copy.deepcopy(full)
    broken["commands"][1]["expected_markers"] = []
    rejected(broken, development, control, optimized, "missing CRC proof")
    broken = copy.deepcopy(development)
    broken["commands"] = broken["commands"][:-1]
    rejected(full, broken, control, optimized, "incomplete development run")
    broken = copy.deepcopy(optimized)
    broken["artifacts"]["host_server"]["sha256"] = "different"
    rejected(full, development, control, broken, "mismatched host")
    broken = copy.deepcopy(control)
    broken["board"] = "CS00024"
    rejected(full, development, broken, optimized, "mixed board set")
    retained_report_test()
    print("PHYSICAL-CLOSURE-TEST: PASS (identity, coverage, pair negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
