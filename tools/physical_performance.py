#!/usr/bin/env python3
"""Audit the controlled cache-off/cache-on CS00015 M4 comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import physical_acceptance as acceptance


SCHEMA = "cpm-plus-juku-physical-performance-v1"
CONTROL_SYSTEM = \
    "e68158497438b19ca3773d2ec11d91a0ddf888e351c0d9cd559e8b4c6e223ea7"
CONTROL_FASTBOOT = \
    "294e85b80ce824fcf08829369d3ce2ff3c1a7d6268e246a0c780dbe92f32adcd"
OPTIMIZED_SYSTEM = \
    "57de00733bea16a3ce6427b8e010649727c6b0d84144724c43c5114a1cf35091"
OPTIMIZED_FASTBOOT = \
    "3c2cf62d43b7867844b18fb142fbae8c49bdc83a148fcb22bfac9a8a26b32d67"
RECOVERY_VOLUME = \
    "67d0a99b2979642d6f7d5d9c20ef705be685c99f1ab7846b8cf4f3ea383a54b0"
WORKLOAD = \
    "4f76ac2cbbc579260d5a3b4f6ebe53cfff799ebe280d346205c919c9cd536960"


class ComparisonError(RuntimeError):
    """The retained M4 comparison does not prove the planned change."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ComparisonError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    commands = result.get("commands")
    require(isinstance(commands, list), "physical commands are absent")
    mapped = {
        str(record.get("name")): record
        for record in commands if isinstance(record, dict)
    }
    require(len(mapped) == len(commands), "physical command names differ")
    return mapped


def phase(record: dict[str, Any], name: str) -> dict[str, Any]:
    metrics = record.get("request_metrics")
    require(isinstance(metrics, dict), f"{name} request metrics are absent")
    return {
        "disk_read_requests": metrics.get("disk_read_requests"),
        "disk_read_records": metrics.get("disk_read_records"),
        "disk_write_requests": metrics.get("disk_write_requests"),
        "disk_retries": metrics.get("disk_retries"),
        "disk_request_wire_bytes": metrics.get("disk_request_wire_bytes"),
        "disk_reply_wire_bytes": metrics.get("disk_reply_wire_bytes"),
        "elapsed_seconds": record.get("elapsed_seconds"),
        "elapsed_from_first_disk_request": metrics.get(
            "elapsed_from_first_disk_request"
        ),
    }


def summarize(result: dict[str, Any], *, role: str) -> dict[str, Any]:
    require(result.get("status") == "pass", f"{role} run did not pass")
    require(result.get("profile") == "performance",
            f"{role} run is not the performance workload")
    artifacts = result.get("artifacts")
    workload = result.get("workload")
    require(isinstance(artifacts, dict) and isinstance(workload, dict),
            f"{role} identities are absent")
    expected_system = CONTROL_SYSTEM if role == "control" else OPTIMIZED_SYSTEM
    expected_fastboot = CONTROL_FASTBOOT if role == "control" \
        else OPTIMIZED_FASTBOOT
    require(artifacts.get("system", {}).get("sha256") == expected_system,
            f"{role} system identity differs")
    require(artifacts.get("fast_stage", {}).get("sha256") == expected_fastboot,
            f"{role} Fastboot identity differs")
    require(artifacts.get("volume", {}).get("sha256") == RECOVERY_VOLUME,
            f"{role} volume is not the immutable C6 recovery image")
    require(workload.get("sha256") == WORKLOAD,
            f"{role} performance workload identity differs")
    commands = command_map(result)
    for name in (
        "dir-a", "type-readme", "select-b", "dir-b", "select-a",
        "diag-cpu", "warm-boot", "erase-readme", "dir-after-erase",
    ):
        require(name in commands, f"{role} command {name} is absent")
    return {
        "board": result.get("board"),
        "system_sha256": expected_system,
        "fastboot_sha256": expected_fastboot,
        "rom_sha256": artifacts.get("rom", {}).get("sha256"),
        "volume_sha256": RECOVERY_VOLUME,
        "host_server_sha256": artifacts.get("host_server", {}).get("sha256"),
        "workload_sha256": WORKLOAD,
        "boot": phase(result.get("boot", {}), "boot"),
        **{name: phase(commands[name], name) for name in commands},
    }


def compare(control: dict[str, Any], optimized: dict[str, Any]) \
        -> dict[str, Any]:
    before = summarize(control, role="control")
    after = summarize(optimized, role="optimized")
    require(before["board"] == after["board"], "comparison boards differ")
    for key in (
        "rom_sha256", "volume_sha256", "host_server_sha256", "workload_sha256",
    ):
        require(before[key] == after[key], f"comparison {key} differs")

    expected = {
        "control": {
            "boot": (10, 80), "dir-a": (0, 0),
            "type-readme": (1, 8), "select-b": (4, 32), "dir-b": (1, 8),
        },
        "optimized": {
            "boot": (8, 64), "dir-a": (0, 0),
            "type-readme": (1, 8), "select-b": (4, 32), "dir-b": (0, 0),
        },
    }
    for role, summary in (("control", before), ("optimized", after)):
        for name, actual in summary.items():
            if not isinstance(actual, dict) or \
                    "disk_retries" not in actual:
                continue
            require(actual["disk_retries"] == 0,
                    f"{role} {name} retried")
        for name, (reads, records) in expected[role].items():
            actual = summary[name]
            require(
                (actual["disk_read_requests"], actual["disk_read_records"]) ==
                (reads, records),
                f"{role} {name} read count differs",
            )
        require(summary["erase-readme"]["disk_write_requests"] > 0,
                f"{role} did not exercise synchronous erase writes")
        require(summary["boot"]["elapsed_from_first_disk_request"] is not None,
                f"{role} boot timing boundary is absent")

    return {
        "schema": SCHEMA,
        "status": "pass",
        "decision": (
            "hot-directory cache removes two cold-read requests and the first "
            "B: DIR request without retries; elapsed values are observations"
        ),
        "control": before,
        "optimized": after,
        "delta": {
            "boot_read_requests": (
                after["boot"]["disk_read_requests"]
                - before["boot"]["disk_read_requests"]
            ),
            "boot_read_records": (
                after["boot"]["disk_read_records"]
                - before["boot"]["disk_read_records"]
            ),
            "boot_elapsed_from_first_disk_request": round(
                float(after["boot"]["elapsed_from_first_disk_request"])
                - float(before["boot"]["elapsed_from_first_disk_request"]), 6,
            ),
            "b_dir_read_requests": (
                after["dir-b"]["disk_read_requests"]
                - before["dir-b"]["disk_read_requests"]
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", type=Path)
    parser.add_argument("optimized", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for directory in (args.control, args.optimized):
        failures = acceptance.audit_directory(directory)
        require(not failures, f"{directory} audit failed: {failures}")
    control_result = json.loads((args.control / "result.json").read_text())
    optimized_result = json.loads((args.optimized / "result.json").read_text())
    report = compare(control_result, optimized_result)
    report["inputs"] = {
        "control_result_sha256": sha256(args.control / "result.json"),
        "optimized_result_sha256": sha256(args.optimized / "result.json"),
    }
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(args.output)
    print(
        "PHYSICAL-PERFORMANCE: PASS "
        f"(boot {report['control']['boot']['disk_read_requests']} -> "
        f"{report['optimized']['boot']['disk_read_requests']}, "
        f"B: DIR {report['control']['dir-b']['disk_read_requests']} -> "
        f"{report['optimized']['dir-b']['disk_read_requests']})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ComparisonError, OSError, ValueError) as error:
        print(f"physical-performance: {error}")
        raise SystemExit(1)
