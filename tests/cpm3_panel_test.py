#!/usr/bin/env python3
"""Admission gates for the project-owned CP437 status panel."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from panel_oracle import framebuffer  # noqa: E402


PANEL = ROOT / "build/panel.cim"
EXPECTED_SHA256 = \
    "db8e2696c39b6466b629a7f8fca837cc921ad57662f319b6b6b94c77d1a1e74c"
EXPECTED_HIDDEN = \
    "b15d2b862aa7bfcebe4b470ed8a55c254ec998841a0d1470cf16cb912b83672f"
EXPECTED_VISIBLE = \
    "462d35ce8e146306734658613ef9a5a37ba09ac9021ac66368046d11ff98d7c2"
EXPECTED_EST_HIDDEN = \
    "43bb9b8710ad9ae6be52553d700167e0504c4b83cc77545e5de2c0efa4fc6cdf"
EXPECTED_EST_VISIBLE = \
    "fa591622fdc5525aacb54bdec1fc48fbfa8555e1f506ee4ee72049df99e8281f"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def destinations(name: str) -> dict[str, dict]:
    report = json.loads((ROOT / f"out/{name}.report.json").read_text())
    return {item["destination"]: item for item in report["files"]}


def main() -> int:
    payload = PANEL.read_bytes()
    require(len(payload) == 1349 and digest(payload) == EXPECTED_SHA256,
            "PANEL.COM identity differs")
    require(0x0100 + len(payload) < 0x9A00,
            "PANEL.COM does not fit the exact C6 TPA")
    hidden = framebuffer(cursor=False)
    visible = framebuffer(cursor=True)
    require(digest(hidden) == EXPECTED_HIDDEN
            and digest(visible) == EXPECTED_VISIBLE,
            "PANEL source-framebuffer oracle differs")
    est_hidden = framebuffer(cursor=False, s21=0x0F)
    est_visible = framebuffer(cursor=True, s21=0x0F)
    require(digest(est_hidden) == EXPECTED_EST_HIDDEN
            and digest(est_visible) == EXPECTED_EST_VISIBLE,
            "PANEL Estonian fallback framebuffer oracle differs")

    for name in (
        "cpm-plus-juku-full", "cpm-plus-juku-dev",
        "cpm-plus-juku-museum-demo",
    ):
        files = destinations(name)
        record = files.get("0:PANEL.COM")
        require(record is not None
                and record["sha256"] == EXPECTED_SHA256
                and record["volume_bytes"] == 1349
                and record["provenance"] == {
                    "source": "src/panel.asm",
                    "version": "Juku Panel 1.0",
                    "license": "LICENSE",
                }, f"{name} PANEL admission differs")

    for name in (
        "cpm-plus-juku-recovery", "cpm-plus-juku-native-recovery",
        "cpm-plus-juku-c6-recovery",
    ):
        require("0:PANEL.COM" not in destinations(name),
                f"{name} unexpectedly contains PANEL.COM")

    print(
        "CPM3-PANEL: PASS "
        "(identity, source framebuffer, profiles, recovery)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
