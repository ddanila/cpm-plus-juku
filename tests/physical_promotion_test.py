#!/usr/bin/env python3
"""Prove final physical promotion requires matching blind and visual sets."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


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


def retained_report_test() -> None:
    with tempfile.TemporaryDirectory(prefix="physical-promotion.") as name:
        base = Path(name)
        blind_path = base / "blind.json"
        display_path = base / "display.json"
        blind_path.write_text(json.dumps(blind_report(), indent=2) + "\n")
        display_path.write_text(json.dumps(display_report(), indent=2) + "\n")
        with patch.object(promotion.closure, "audit_report"), \
                patch.object(promotion.display, "audit_report"):
            report = promotion.build_report(blind_path, display_path)
            if promotion.audit_report(report) != report:
                raise AssertionError("retained promotion report changed")
            broken = copy.deepcopy(report)
            broken["decision"] = "edited"
            try:
                promotion.audit_report(broken)
            except promotion.PromotionError:
                pass
            else:
                raise AssertionError("edited promotion report was accepted")
            display_path.write_text(display_path.read_text() + " ")
            try:
                promotion.audit_report(report)
            except promotion.PromotionError:
                pass
            else:
                raise AssertionError("changed promotion input was accepted")


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
    retained_report_test()
    print("PHYSICAL-PROMOTION-TEST: PASS (identity, modes, remaining negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
