#!/usr/bin/env python3
"""Audit the four retained blind CS00015 feature-plan result bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import physical_acceptance as acceptance
import physical_performance as performance


SCHEMA = "cpm-plus-juku-physical-closure-v1"
ROM = "0487d5150f9b662a193b3f031aadd90002ee232477d355d3877a757a247c2f09"
FULL_VOLUME = \
    "21fb8112aa908624fc52b17993b9d0a383c83ad4443059703c4b9e48e1453fd5"
DEVELOPMENT_VOLUME = \
    "5ff16bf3e2a8588674a6b12b3d8f9640cea16c152ff2e692140b9ec5634ddfcd"
FULL_WORKLOAD = \
    "8c160981bcf950450e7f44590778abc974a39b94636dee35255176fc3cab9494"
DEVELOPMENT_WORKLOAD = \
    "9a4299aede1fe858a70d347e015e0b985cf154e3cb9a0eb854733b6a64b93e57"
CRC_MARKER = "CRC16-CCITT: 4613  records: 0004"


class ClosureError(RuntimeError):
    """The retained result set does not close the blind physical plan."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ClosureError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hash(result: dict[str, Any], name: str) -> Any:
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    record = artifacts.get(name)
    return record.get("sha256") if isinstance(record, dict) else None


def commands(result: dict[str, Any], role: str) -> dict[str, dict[str, Any]]:
    records = result.get("commands")
    require(isinstance(records, list), f"{role} commands are absent")
    mapped = {
        str(record.get("name")): record
        for record in records if isinstance(record, dict)
    }
    require(len(mapped) == len(records), f"{role} command names differ")
    require(all(record.get("result") == "pass" for record in mapped.values()),
            f"{role} contains a failed command")
    return mapped


def workload_hash(result: dict[str, Any]) -> Any:
    workload = result.get("workload")
    return workload.get("sha256") if isinstance(workload, dict) else None


def summarize_profile(result: dict[str, Any], role: str) -> dict[str, Any]:
    expected = {
        "full": ("full", FULL_VOLUME, FULL_WORKLOAD, (
            "pip-copy", "crc-copy", "pip-copy-repeat", "crc-copy-repeat",
        )),
        "development": (
            "development", DEVELOPMENT_VOLUME, DEVELOPMENT_WORKLOAD,
            ("hexcom", "hello", "sid", "patch", "ed", "type-ed"),
        ),
    }
    profile, volume, workload, required_commands = expected[role]
    require(result.get("status") == "pass", f"{role} run did not pass")
    require(result.get("profile") == profile, f"{role} profile differs")
    require(result.get("board") == "CS00015", f"{role} board differs")
    require(artifact_hash(result, "system") == performance.OPTIMIZED_SYSTEM,
            f"{role} system identity differs")
    require(artifact_hash(result, "fast_stage") == performance.OPTIMIZED_FASTBOOT,
            f"{role} Fastboot identity differs")
    require(artifact_hash(result, "rom") == ROM, f"{role} ROM differs")
    require(artifact_hash(result, "volume") == volume,
            f"{role} volume identity differs")
    require(workload_hash(result) == workload,
            f"{role} workload identity differs")
    mapped = commands(result, role)
    for name in required_commands:
        require(name in mapped, f"{role} command {name} is absent")
    if role == "full":
        for name in ("crc-copy", "crc-copy-repeat"):
            markers = mapped[name].get("expected_markers")
            require(isinstance(markers, list) and CRC_MARKER in markers,
                    f"full {name} does not bind CRC 4613")
    return {
        "profile": profile,
        "board": result.get("board"),
        "system_sha256": performance.OPTIMIZED_SYSTEM,
        "fastboot_sha256": performance.OPTIMIZED_FASTBOOT,
        "rom_sha256": ROM,
        "volume_sha256": volume,
        "workload_sha256": workload,
        "host_server_sha256": artifact_hash(result, "host_server"),
        "commands": len(mapped),
        "boot_elapsed_seconds": result.get("boot", {}).get("elapsed_seconds"),
        "required_commands": list(required_commands),
    }


def close(full: dict[str, Any], development: dict[str, Any],
          control: dict[str, Any], optimized: dict[str, Any]) \
        -> dict[str, Any]:
    full_summary = summarize_profile(full, "full")
    development_summary = summarize_profile(development, "development")
    comparison = performance.compare(control, optimized)
    control_summary = comparison["control"]
    optimized_summary = comparison["optimized"]
    summaries = (
        full_summary, development_summary, control_summary, optimized_summary,
    )
    require(all(summary.get("board") == "CS00015" for summary in summaries),
            "closure result set is not entirely CS00015")
    for field in ("rom_sha256", "host_server_sha256"):
        values = {summary.get(field) for summary in summaries}
        require(len(values) == 1 and None not in values,
                f"closure {field} differs")
    require(control_summary["rom_sha256"] == ROM,
            "performance ROM differs from full/development")
    return {
        "schema": SCHEMA,
        "status": "pass",
        "decision": (
            "CS00015 blind full/development acceptance and controlled M4 "
            "performance evidence pass; analog display acceptance is separate"
        ),
        "board": "CS00015",
        "full": full_summary,
        "development": development_summary,
        "performance": comparison,
        "remaining": ["four-mode analog display observation"],
    }


def load_result(directory: Path) -> dict[str, Any]:
    path = directory.resolve() / "result.json"
    result = json.loads(path.read_text())
    require(isinstance(result, dict), f"{path} is not an object")
    return result


def build_report(directories: dict[str, Path]) -> dict[str, Any]:
    require(set(directories) == {"full", "development", "control", "optimized"},
            "physical closure input roles differ")
    resolved = {role: directory.resolve()
                for role, directory in directories.items()}
    for role, directory in resolved.items():
        failures = acceptance.audit_directory(directory)
        require(not failures, f"{role} audit failed: {failures}")
    results = {role: load_result(directory)
               for role, directory in resolved.items()}
    report = close(
        results["full"], results["development"],
        results["control"], results["optimized"],
    )
    report["inputs"] = {
        role: {
            "directory": str(directory),
            "result_sha256": sha256(directory / "result.json"),
        }
        for role, directory in resolved.items()
    }
    return report


def audit_report(report: dict[str, Any]) -> dict[str, Any]:
    require(report.get("schema") == SCHEMA and report.get("status") == "pass",
            "physical closure report identity differs")
    inputs = report.get("inputs")
    require(isinstance(inputs, dict) and
            set(inputs) == {"full", "development", "control", "optimized"},
            "physical closure report inputs differ")
    directories: dict[str, Path] = {}
    for role, record in inputs.items():
        require(isinstance(record, dict) and
                isinstance(record.get("directory"), str) and
                isinstance(record.get("result_sha256"), str),
                f"physical closure {role} input is malformed")
        directory = Path(record["directory"]).resolve()
        require(sha256(directory / "result.json") == record["result_sha256"],
                f"physical closure {role} result hash differs")
        directories[role] = directory
    expected = build_report(directories)
    require(report == expected, "physical closure report differs from evidence")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("full", type=Path)
    parser.add_argument("development", type=Path)
    parser.add_argument("control", type=Path)
    parser.add_argument("optimized", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directories = {
        "full": args.full.resolve(),
        "development": args.development.resolve(),
        "control": args.control.resolve(),
        "optimized": args.optimized.resolve(),
    }
    report = build_report(directories)
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(args.output)
    print(
        "PHYSICAL-CLOSURE: PASS "
        f"(full {report['full']['commands']} commands, development "
        f"{report['development']['commands']} commands, M4 boot "
        f"{report['performance']['control']['boot']['disk_read_requests']} -> "
        f"{report['performance']['optimized']['boot']['disk_read_requests']})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ClosureError, performance.ComparisonError,
            OSError, ValueError) as error:
        print(f"physical-closure: {error}")
        raise SystemExit(1)
