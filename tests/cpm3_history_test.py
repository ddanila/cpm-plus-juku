#!/usr/bin/env python3
"""Admission gates for the reproducible Juku CP/M 3 history extension."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CCP = ROOT / "build/cpm3-history/CCP.COM"
MANIFEST = ROOT / "build/cpm3-history/manifest.json"
HIST = ROOT / "build/history.cim"
TOOL = ROOT / "tools/build_cpm3_history_ccp.py"
UPSTREAM = ROOT / "third_party/cpm3/ccp.com"
EXPECTED_CCP = "e27c1fcc2b185eaac395069b0e77575a026cff9d87130cd9bd117711746eedb7"
EXPECTED_HIST = "3f3754e41bb7a501fdb6a8951a108287409a8efb6b03360de1ba0bf6d960faf2"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def by_destination(report: Path) -> dict[str, dict]:
    data = json.loads(report.read_text())
    require(data.get("schema") == "cpm-plus-juku-volume-report-v1",
            f"volume report schema differs: {report}")
    return {
        item["destination"]: item
        for item in data["files"]
    }


def main() -> int:
    require(CCP.is_file() and MANIFEST.is_file() and HIST.is_file(),
            "history build output is absent")
    require(len(CCP.read_bytes()) == 3379 and digest(CCP) == EXPECTED_CCP,
            "history CCP identity differs")
    require(len(HIST.read_bytes()) == 286 and digest(HIST) == EXPECTED_HIST,
            "HIST.COM identity differs")

    manifest = json.loads(MANIFEST.read_text())
    require(manifest.get("schema") == "cpm-plus-juku-history-ccp-v1",
            "history CCP manifest schema differs")
    require(manifest["upstream"] == {
        "name": "Digital Research CP/M 3.1 CCP",
        "bytes": 3200,
        "sha256": digest(UPSTREAM),
        "license": "third_party/cpm3/LICENSE.md",
    }, "upstream CCP evidence differs")
    require(manifest["derived"]["bytes"] == 3379
            and manifest["derived"]["sha256"] == EXPECTED_CCP
            and manifest["derived"]["runtime_end_exclusive"] == "0E33",
            "derived CCP evidence differs")
    require(manifest["history_state"] == {
        "start": "D571", "end": "D5BF", "bytes": 79,
        "next_reserved": "D5C0",
    }, "history state overlaps a reserved range")

    with tempfile.TemporaryDirectory(prefix="cpm3-history-test.") as name:
        rebuilt = Path(name) / "CCP.COM"
        subprocess.run(
            ["python3", str(TOOL), "--output", str(rebuilt)],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        require(rebuilt.read_bytes() == CCP.read_bytes(),
                "history CCP rebuild is not deterministic")
        rebuilt_manifest = json.loads(
            rebuilt.with_name("manifest.json").read_text()
        )
        require(rebuilt_manifest == manifest,
                "history CCP manifest is not deterministic")

    for profile in ("full", "dev", "museum-demo"):
        report = ROOT / {
            "full": "out/cpm-plus-juku-full.report.json",
            "dev": "out/cpm-plus-juku-dev.report.json",
            "museum-demo": "out/cpm-plus-juku-museum-demo.report.json",
        }[profile]
        files = by_destination(report)
        require(files["0:CCP.COM"]["sha256"] == EXPECTED_CCP
                and files["0:CCP.COM"]["volume_bytes"] == 3379,
                f"{profile} does not contain the history CCP")
        require(files["0:HIST.COM"]["sha256"] == EXPECTED_HIST
                and files["0:HIST.COM"]["volume_bytes"] == 286,
                f"{profile} does not contain HIST.COM")

    for profile in ("recovery", "native-recovery", "c6-recovery"):
        report = ROOT / {
            "recovery": "out/cpm-plus-juku-recovery.report.json",
            "native-recovery": "out/cpm-plus-juku-native-recovery.report.json",
            "c6-recovery": "out/cpm-plus-juku-c6-recovery.report.json",
        }[profile]
        files = by_destination(report)
        require("0:HIST.COM" not in files,
                f"{profile} unexpectedly contains HIST.COM")
        require(files["0:CCP.COM"]["sha256"] == digest(UPSTREAM)
                and files["0:CCP.COM"]["volume_bytes"] == 3200,
                f"{profile} no longer contains the exact recovery CCP")

    print("CPM3-HISTORY: PASS (rebuild, state map, profiles, recovery)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
