#!/usr/bin/env python3
"""Prove final physical promotion requires matching blind and visual sets."""

from __future__ import annotations

import copy
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import display_acceptance as display  # noqa: E402
import physical_closure as closure  # noqa: E402
import physical_performance as performance  # noqa: E402
import physical_promotion as promotion  # noqa: E402


HOST = "host-server"


def run(system: str = performance.OPTIMIZED_SYSTEM,
        fastboot: str = performance.OPTIMIZED_FASTBOOT) -> dict[str, object]:
    return {
        "board": "CS00015", "rom_sha256": closure.ROM,
        "system_sha256": system, "fastboot_sha256": fastboot,
        "host_server_sha256": HOST,
    }


def blind_report() -> dict[str, object]:
    return {
        "schema": closure.SCHEMA, "status": "pass", "board": "CS00015",
        "full": run(), "development": run(),
        "performance": {
            "control": run(performance.CONTROL_SYSTEM,
                           performance.CONTROL_FASTBOOT),
            "optimized": run(),
        },
        "remaining": ["four-mode analog display observation"],
    }


def display_report() -> dict[str, object]:
    return {
        "schema": display.REPORT_SCHEMA, "status": "pass", "board": "CS00015",
        "modes": [{"mode": mode, **run()} for mode in display.MODES],
    }


def rejected(blind: dict[str, object], visual: dict[str, object],
             label: str) -> None:
    try:
        promotion.promote(blind, visual)
    except promotion.PromotionError:
        return
    raise AssertionError(f"physical promotion accepted {label}")


def main() -> int:
    blind = blind_report()
    visual = display_report()
    report = promotion.promote(blind, visual)
    if report.get("status") != "pass" or report.get("remaining") != [] or \
            report.get("display_modes") != [0, 1, 2, 3]:
        raise AssertionError("physical promotion summary differs")

    broken = copy.deepcopy(visual)
    broken["modes"][2]["host_server_sha256"] = "other"
    rejected(blind, broken, "mixed host")
    broken = copy.deepcopy(visual)
    broken["modes"] = broken["modes"][:-1]
    rejected(blind, broken, "missing display mode")
    broken = copy.deepcopy(visual)
    broken["modes"][0]["system_sha256"] = "other"
    rejected(blind, broken, "wrong display system")
    broken = copy.deepcopy(blind)
    broken["performance"]["optimized"]["rom_sha256"] = "other"
    rejected(broken, visual, "wrong optimized ROM")
    broken = copy.deepcopy(blind)
    broken["remaining"] = []
    rejected(broken, visual, "premature blind closure")
    print("PHYSICAL-PROMOTION-TEST: PASS (identity, modes, remaining negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
