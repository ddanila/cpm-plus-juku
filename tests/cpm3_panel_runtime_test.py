#!/usr/bin/env python3
"""Verify exact-C6 runtime and memory evidence for PANEL.COM."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "build/cpm3-panel-runtime.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    data = json.loads(METRICS.read_text())
    platform = data.get("_platform")
    expected_platform = json.loads((
        ROOT / "third_party/cpm3/releases/runtime-memory.json"
    ).read_text())["artifacts"]
    require(platform == expected_platform,
            "PANEL runtime did not bind the exact C6 platform")
    record = data.get("extra")
    require(isinstance(record, dict) and record.get("command") == "PANEL",
            "PANEL runtime command is absent")
    entry = record.get("stack_entry_sp")
    anchor = record.get("stack_anchor_sp")
    low = record.get("stack_low_sp")
    observed = record.get("stack_bytes_observed")
    require(all(isinstance(value, int)
                for value in (entry, anchor, low, observed)),
            "PANEL stack evidence is absent")
    require((entry, anchor, low, observed) ==
            (0x9CFE, 0x9CFE, 0x9CF2, 12)
            and record.get("stack_segments") == 1
            and record.get("explicit_sp_writes") == 0,
            "PANEL stack evidence differs")
    require(record.get("read_requests", 0) > 0,
            "PANEL.COM was not loaded from the network disk")
    print(
        "CPM3-PANEL-RUNTIME: PASS "
        f"(exact C6, {observed} stack bytes, local framebuffer)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
