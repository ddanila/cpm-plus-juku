#!/usr/bin/env python3
"""Re-audit blind and visual evidence into the final CS00015 promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import display_acceptance as display
import physical_closure as closure
import physical_performance as performance


SCHEMA = "cpm-plus-juku-physical-promotion-v1"


class PromotionError(RuntimeError):
    """The retained evidence does not close physical promotion."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PromotionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def promote(blind: dict[str, Any], visual: dict[str, Any]) -> dict[str, Any]:
    require(blind.get("schema") == closure.SCHEMA and
            blind.get("status") == "pass" and
            blind.get("remaining") == ["four-mode analog display observation"],
            "blind closure decision differs")
    require(visual.get("schema") == display.REPORT_SCHEMA and
            visual.get("status") == "pass",
            "display acceptance decision differs")
    require(blind.get("board") == "CS00015" and
            visual.get("board") == "CS00015",
            "physical promotion board differs")

    performance_report = blind.get("performance")
    require(isinstance(performance_report, dict),
            "blind performance report is malformed")
    blind_runs = [
        blind.get("full"), blind.get("development"),
        performance_report.get("control"),
        performance_report.get("optimized"),
    ]
    visual_runs = visual.get("modes")
    require(all(isinstance(run, dict) for run in blind_runs),
            "blind promotion runs are malformed")
    require(isinstance(visual_runs, list) and len(visual_runs) == 4 and
            {run.get("mode") for run in visual_runs
             if isinstance(run, dict)} == set(display.MODES),
            "display promotion modes differ")
    runs = blind_runs + visual_runs
    require(all(run.get("board") == "CS00015" for run in runs),
            "promotion run board differs")
    require({run.get("rom_sha256") for run in runs} == {closure.ROM},
            "promotion ROM identity differs")
    require({run.get("host_server_sha256") for run in runs} and
            len({run.get("host_server_sha256") for run in runs}) == 1 and
            None not in {run.get("host_server_sha256") for run in runs},
            "promotion host identity differs")

    optimized_runs = [blind["full"], blind["development"],
                      performance_report["optimized"], *visual_runs]
    require({run.get("system_sha256") for run in optimized_runs} ==
            {performance.OPTIMIZED_SYSTEM},
            "promotion optimized system identity differs")
    require({run.get("fastboot_sha256") for run in optimized_runs} ==
            {performance.OPTIMIZED_FASTBOOT},
            "promotion optimized Fastboot identity differs")
    host = runs[0]["host_server_sha256"]
    return {
        "schema": SCHEMA,
        "status": "pass",
        "decision": (
            "CS00015 full/development, controlled M4, and four-mode analog "
            "display evidence pass for the exact C6 physical baseline"
        ),
        "board": "CS00015",
        "rom_sha256": closure.ROM,
        "system_sha256": performance.OPTIMIZED_SYSTEM,
        "fastboot_sha256": performance.OPTIMIZED_FASTBOOT,
        "host_server_sha256": host,
        "blind_schema": closure.SCHEMA,
        "display_schema": display.REPORT_SCHEMA,
        "display_modes": sorted(display.MODES),
        "remaining": [],
    }


def load(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"{label} report is not an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blind", type=Path)
    parser.add_argument("display", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    blind_path = args.blind.resolve()
    display_path = args.display.resolve()
    blind = load(blind_path, "blind closure")
    visual = load(display_path, "display acceptance")
    closure.audit_report(blind)
    display.audit_report(visual)
    report = promote(blind, visual)
    report["inputs"] = {
        "blind": {"path": str(blind_path), "sha256": sha256(blind_path)},
        "display": {"path": str(display_path), "sha256": sha256(display_path)},
    }
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(args.output)
    print("PHYSICAL-PROMOTION: PASS (blind + modes 0,1,2,3; remaining 0)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PromotionError, closure.ClosureError, display.DisplayError,
            performance.ComparisonError, OSError, ValueError) as error:
        print(f"physical-promotion: {error}")
        raise SystemExit(1)
