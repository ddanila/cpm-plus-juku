#!/usr/bin/env python3
"""Verify exact-C6 runtime evidence for CCP repeat and HIST.COM."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "build/cpm3-history-runtime.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    data = json.loads(METRICS.read_text())
    platform = data.get("_platform")
    require(isinstance(platform, dict), "history runtime platform is absent")
    require(platform["network_rom"]["name"] ==
            "juku-network-rom-abi1.2-c6.bin",
            "history runtime did not use exact C6")
    require(platform["system"]["name"] ==
            "cpm-plus-juku-network-rom-extended-native-system.bin",
            "history runtime did not use the current native system")
    require(platform["fastboot"]["name"] ==
            "cpm-plus-juku-network-rom-extended-native-fastboot-v16.bin",
            "history runtime did not use V16 Fastboot")

    expected = {
        "extra": "SHOW A:[SPACE]",
        "extra2": "HIST",
        "extra3": "!!",
        "extra4": " ",
        "extra5": "HIST",
        "extra6": "X" * 77,
        "extra7": "HIST",
        "extra8": "HIST CLEAR",
        "extra9": "HIST",
    }
    for metric, command in expected.items():
        record = data.get(metric)
        require(isinstance(record, dict) and record.get("command") == command,
                f"runtime command differs: {metric}")
    for metric in ("extra2", "extra5", "extra7", "extra8", "extra9"):
        record = data[metric]
        entry = record.get("stack_entry_sp")
        anchor = record.get("stack_anchor_sp")
        low = record.get("stack_low_sp")
        observed = record.get("stack_bytes_observed")
        require(all(isinstance(value, int)
                    for value in (entry, anchor, low, observed)),
                f"runtime stack evidence is absent: {metric}")
        require(0x9A00 <= low <= anchor == entry == 0x9CFE
                and observed == anchor - low
                and observed < 0x0100,
                f"runtime stack evidence is unsafe: {metric}")

    require(data["extra3"]["read_requests"] > 0,
            "repeat token did not execute the retained SHOW command")
    require(all(data[name]["read_requests"] > 0 for name in (
        "extra2", "extra5", "extra7", "extra8", "extra9",
    )),
            "HIST.COM was not loaded for every runtime case")
    require(data["extra4"]["read_requests"] == 0,
            "blank input unexpectedly performed disk I/O")
    print(
        "CPM3-HISTORY-RUNTIME: PASS "
        "(reload, repeat, blank/overlong retention, clear, exact C6)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
