#!/usr/bin/env python3
"""Prove four-mode display observations and run identities fail closed."""

from __future__ import annotations

import copy
import hashlib
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


def run(mode: int, host: str = "server") -> tuple[dict[str, object], bytes]:
    marker = display.MODES[mode][2]
    response = (
        f"Juku Vidtest 1.0\r\n{marker}\r\n{display.LOCALE}\r\n"
        "VIDTEST READY\r\nJuku Vidtest 1.0 DONE\r\nA>"
    ).encode("ascii")
    result = {
        "status": "pass", "profile": "display", "board": "CS00015",
        "artifacts": {
            "system": {"sha256": performance.OPTIMIZED_SYSTEM},
            "fast_stage": {"sha256": performance.OPTIMIZED_FASTBOOT},
            "rom": {"sha256": closure.ROM},
            "volume": {"sha256": closure.FULL_VOLUME},
            "host_server": {"sha256": host},
        },
        "workload": {"sha256": display.DISPLAY_WORKLOAD},
        "commands": [{
            "name": "vidtest", "command": "VIDTEST", "result": "pass",
            "response_start": 0, "response_end": len(response),
        }],
    }
    return result, response


def document(base: Path) -> dict[str, object]:
    observations = []
    for mode, (raw_s21, geometry, _) in display.MODES.items():
        photo = base / f"mode{mode}.jpg"
        photo.write_bytes(f"photo-{mode}".encode("ascii"))
        observations.append({
            "mode": mode, "raw_s21": raw_s21, "geometry": geometry,
            "result_directory": f"mode{mode}",
            "edges_visible": True, "glyphs_readable": True,
            "locale_stable": True, "cursor_blinked": True,
            "joined_cp437": True if mode == 3 else "not-applicable",
            "framebuffer_fault": False, "monitor_cropping": "",
            "photos": [{
                "path": photo.name,
                "sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
            }],
        })
    return {
        "schema": display.SCHEMA, "board": "CS00015",
        "monitor": {"manufacturer": "Test", "model": "Oracle",
                    "input": "RGB"},
        "observations": observations,
    }


def rejected(doc: dict[str, object], results: dict[int, dict[str, object]],
             transcripts: dict[int, bytes], base: Path, label: str) -> None:
    try:
        display.accept(doc, results, transcripts, base)
    except display.DisplayError:
        return
    raise AssertionError(f"display acceptance accepted {label}")


def retained_report_test(base: Path) -> None:
    doc = document(base)
    observation_path = base / "observations.json"
    observation_path.write_text(json.dumps(doc, indent=2) + "\n")
    for mode in display.MODES:
        result, transcript = run(mode)
        directory = base / f"mode{mode}"
        directory.mkdir()
        (directory / "result.json").write_text(
            json.dumps(result, indent=2) + "\n",
        )
        (directory / "console.bin").write_bytes(transcript)
    with patch.object(display.acceptance, "audit_directory", return_value=[]):
        report = display.build_report(observation_path)
        if display.audit_report(report) != report:
            raise AssertionError("retained display report changed")
        broken = copy.deepcopy(report)
        broken["modes"][0]["geometry"] = "edited"
        try:
            display.audit_report(broken)
        except display.DisplayError:
            pass
        else:
            raise AssertionError("edited display report was accepted")
        observation_path.write_text(observation_path.read_text() + " ")
        try:
            display.audit_report(report)
        except display.DisplayError:
            pass
        else:
            raise AssertionError("changed display observation was accepted")


def main() -> int:
    schema = json.loads((
        ROOT / "physical/display-observation.schema.json"
    ).read_text())
    if schema.get("title") != \
            "Juku CP/M Plus four-mode physical display observations":
        raise AssertionError("display observation schema differs")
    with tempfile.TemporaryDirectory(prefix="display-acceptance.") as name:
        base = Path(name)
        doc = document(base)
        pairs = {mode: run(mode) for mode in display.MODES}
        results = {mode: pair[0] for mode, pair in pairs.items()}
        transcripts = {mode: pair[1] for mode, pair in pairs.items()}
        report = display.accept(doc, results, transcripts, base)
        if report.get("status") != "pass" or len(report["modes"]) != 4:
            raise AssertionError("display acceptance summary differs")

        broken = copy.deepcopy(doc)
        broken["observations"][1]["cursor_blinked"] = False
        rejected(broken, results, transcripts, base, "static cursor")
        broken = copy.deepcopy(doc)
        broken["observations"][3]["joined_cp437"] = "not-applicable"
        rejected(broken, results, transcripts, base, "unjoined CP437")
        broken = copy.deepcopy(doc)
        broken["observations"][0]["edges_visible"] = False
        rejected(broken, results, transcripts, base, "unexplained cropping")
        broken = copy.deepcopy(results)
        broken[2]["artifacts"]["host_server"]["sha256"] = "different"
        rejected(doc, broken, transcripts, base, "mixed host")
        broken_transcripts = copy.deepcopy(transcripts)
        broken_transcripts[1] = broken_transcripts[1].replace(b"Mode 1", b"Mode X")
        rejected(doc, results, broken_transcripts, base, "wrong mode page")
        broken = copy.deepcopy(doc)
        broken["observations"][0]["photos"][0]["path"] = "../outside.jpg"
        rejected(broken, results, transcripts, base, "escaping photo path")
        broken = copy.deepcopy(doc)
        broken["observations"][0]["mode"] = []
        rejected(broken, results, transcripts, base, "malformed mode")
        photo = base / "mode0.jpg"
        photo.write_bytes(b"tampered")
        rejected(doc, results, transcripts, base, "changed photograph")
    with tempfile.TemporaryDirectory(prefix="display-report.") as name:
        retained_report_test(Path(name))
    print("DISPLAY-ACCEPTANCE-TEST: PASS (modes, observations, photo negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
