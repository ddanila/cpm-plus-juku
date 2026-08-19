#!/usr/bin/env python3
"""Prove the controlled M4 artifacts and fail-closed comparison contract."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import physical_acceptance as acceptance  # noqa: E402
import physical_performance as performance  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def fake_result(role: str) -> dict[str, object]:
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
    commands = [
        {"name": name, "request_metrics": value, "elapsed_seconds": 1.0}
        for name, value in phases.items()
    ]
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
            "rom": {"sha256": "rom"},
            "host_server": {"sha256": "server"},
        },
        "workload": {"sha256": performance.WORKLOAD},
        "boot": {
            "request_metrics": metrics(10 if control else 8,
                                       80 if control else 64),
            "elapsed_seconds": 4.0,
        },
        "commands": commands,
    }


def main() -> int:
    expected = {
        ROOT / "out/cpm-plus-juku-network-rom-control-system.bin":
        performance.CONTROL_SYSTEM,
        ROOT / "out/cpm-plus-juku-network-rom-control-fastboot-v16.bin":
        performance.CONTROL_FASTBOOT,
        ROOT / "out/cpm-plus-juku-network-rom-extended-native-system.bin":
        performance.OPTIMIZED_SYSTEM,
        ROOT / "out/cpm-plus-juku-network-rom-extended-native-fastboot-v16.bin":
        performance.OPTIMIZED_FASTBOOT,
        ROOT / "out/cpm-plus-juku-c6-recovery.img":
        performance.RECOVERY_VOLUME,
        ROOT / "physical/workloads/performance.json": performance.WORKLOAD,
    }
    for path, wanted in expected.items():
        if digest(path) != wanted:
            raise AssertionError(f"M4 controlled artifact differs: {path}")
    if (ROOT / "build/adapter-romabi-extended-control.bin").stat().st_size != \
            2924:
        raise AssertionError("M4 cache-off adapter size differs")
    manifest = json.loads((
        ROOT / "out/cpm-plus-juku-c6-control-manifest.json"
    ).read_text())
    if manifest.get("build_identity") != "c6-control-e68158497438b19c" or \
            manifest.get("system", {}).get("sha256") != \
            performance.CONTROL_SYSTEM or \
            manifest.get("fast_stage", {}).get("sha256") != \
            performance.CONTROL_FASTBOOT:
        raise AssertionError("M4 control manifest differs")
    acceptance.load_workload("performance")

    control = fake_result("control")
    optimized = fake_result("optimized")
    report = performance.compare(control, optimized)
    if report["delta"] != {
        "boot_read_requests": -2,
        "boot_read_records": -16,
        "boot_elapsed_from_first_disk_request": 0.0,
        "b_dir_read_requests": -1,
    }:
        raise AssertionError("M4 comparison result differs")
    broken = copy.deepcopy(optimized)
    broken["boot"]["request_metrics"]["disk_read_requests"] = 9
    try:
        performance.compare(control, broken)
    except performance.ComparisonError:
        pass
    else:
        raise AssertionError("M4 wrong optimized count was accepted")
    broken = copy.deepcopy(optimized)
    broken["artifacts"]["host_server"]["sha256"] = "different"
    try:
        performance.compare(control, broken)
    except performance.ComparisonError:
        pass
    else:
        raise AssertionError("M4 mismatched host was accepted")
    broken = copy.deepcopy(optimized)
    broken["commands"][6]["request_metrics"]["disk_retries"] = 1
    try:
        performance.compare(control, broken)
    except performance.ComparisonError:
        pass
    else:
        raise AssertionError("M4 unmeasured-phase retry was accepted")
    print("PHYSICAL-PERFORMANCE-TEST: PASS (control, identities, negative gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
