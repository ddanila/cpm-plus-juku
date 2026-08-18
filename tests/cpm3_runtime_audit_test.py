#!/usr/bin/env python3
"""Negative gates for shipped DRI runtime-memory admission."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "audit_cpm3_runtime.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "audit_cpm3_runtime", MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load runtime-memory audit module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(call, marker: str) -> None:
    try:
        call()
    except ValueError as error:
        if marker not in str(error):
            raise AssertionError(f"wrong runtime rejection: {error}")
    else:
        raise AssertionError(f"runtime mutation accepted: {marker}")


def metrics_for(module, data: dict, profile: str) -> dict:
    result = {"_platform": json.loads(json.dumps(data["artifacts"]))}
    for record in data["records"]:
        if record["profile"] != profile:
            continue
        runtime = record["runtime"]
        metric = {"command": record["command"]}
        for expected_field, actual_field in module.METRIC_FIELDS.items():
            value = runtime[expected_field]
            if expected_field in module.ADDRESS_FIELDS:
                value = int(value, 16)
            metric[actual_field] = value
        result[record["metric"]] = metric
    return result


def main() -> int:
    module = load_module()
    original_path = module.RUNTIME
    original = json.loads(original_path.read_text())
    module.audit()
    with tempfile.TemporaryDirectory(prefix="cpm3-runtime-test.") as name:
        work = Path(name)
        mutated_path = work / "runtime.json"

        changed = json.loads(json.dumps(original))
        del changed["programs"]["DATE.COM"]
        mutated_path.write_text(json.dumps(changed))
        module.RUNTIME = mutated_path
        expect_rejection(module.audit, "runtime program set")

        changed = json.loads(json.dumps(original))
        changed["programs"]["DUMP.COM"]["runtime"]["low_sp"] = "04BD"
        mutated_path.write_text(json.dumps(changed))
        expect_rejection(module.audit, "DUMP.COM")

        changed = json.loads(json.dumps(original))
        changed["programs"]["SETDEF.COM"]["metric"] = "extra2"
        mutated_path.write_text(json.dumps(changed))
        expect_rejection(module.audit, "duplicate runtime metric")

        changed = json.loads(json.dumps(original))
        changed["programs"]["HEXCOM.COM"]["runtime"]["entry_sp"] = "7CFE"
        mutated_path.write_text(json.dumps(changed))
        expect_rejection(module.audit, "entry stack")

        changed = json.loads(json.dumps(original))
        changed["artifacts"]["network_rom"]["name"] = \
            "juku-network-rom-abi1.bin"
        mutated_path.write_text(json.dumps(changed))
        module.RUNTIME = mutated_path
        expect_rejection(module.audit, "not the C6 network_rom")

        module.RUNTIME = original_path
        data = module.audit()
        metrics = metrics_for(module, data, "full")
        metrics_path = work / "metrics.json"
        metrics_path.write_text(json.dumps(metrics))
        module.verify_metrics(data, "full", metrics_path)
        metrics["_platform"]["network_rom"]["sha256"] = "f" * 64
        metrics_path.write_text(json.dumps(metrics))
        expect_rejection(
            lambda: module.verify_metrics(data, "full", metrics_path),
            "exact C6 artifacts",
        )
        metrics = metrics_for(module, data, "full")
        metrics["extra9"]["command"] = "DATE"
        metrics_path.write_text(json.dumps(metrics))
        expect_rejection(
            lambda: module.verify_metrics(data, "full", metrics_path),
            "runtime command differs",
        )

        report = {
            "schema": "cpm-plus-juku-volume-report-v1",
            "files": [
                {
                    "destination": f"0:{record['name']}",
                    "volume_bytes": record["disk_bytes"],
                    "allocated_bytes": record["allocated_bytes"],
                }
                for record in data["records"]
                if record["profile"] == "dev"
            ],
        }
        report_path = work / "volume-report.json"
        report_path.write_text(json.dumps(report))
        module.verify_volume_report(data, "dev", report_path)
        report["files"][0]["allocated_bytes"] += 2048
        report_path.write_text(json.dumps(report))
        expect_rejection(
            lambda: module.verify_volume_report(data, "dev", report_path),
            "volume allocation differs",
        )

    module.RUNTIME = original_path
    print("CPM3-RUNTIME-TEST: PASS (eight negative gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
