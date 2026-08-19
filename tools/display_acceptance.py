#!/usr/bin/env python3
"""Audit four human-observed CS00015 display result bundles and photographs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import physical_acceptance as acceptance
import physical_closure as closure
import physical_performance as performance


SCHEMA = "cpm-plus-juku-display-observations-v1"
REPORT_SCHEMA = "cpm-plus-juku-display-acceptance-v1"
DISPLAY_WORKLOAD = \
    "145670b7a8183a97c56cab3c0397c230a17b6956e0b633cb7f79686afc314f18"
MODES = {
    0: ("01", "40x24", "Mode 0: 40x24, 8x10 cells"),
    1: ("03", "53x24", "Mode 1: 53x24, 6x10 cells"),
    2: ("05", "64x20", "Mode 2: 64x20, 6x10 cells"),
    3: ("07", "80x24", "Mode 3: 80x24, 5x8 cells"),
}
LOCALE = "Locale 0: English + CP437 UI"


class DisplayError(RuntimeError):
    """The retained visual evidence does not close display acceptance."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DisplayError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundled_path(base: Path, value: Any, label: str) -> Path:
    require(isinstance(value, str) and bool(value.strip()),
            f"{label} path is absent")
    relative = Path(value)
    require(not relative.is_absolute(), f"{label} path must be relative")
    path = (base / relative).resolve()
    require(path.is_relative_to(base.resolve()),
            f"{label} path escapes the evidence bundle")
    return path


def artifact_hash(result: dict[str, Any], name: str) -> Any:
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    record = artifacts.get(name)
    return record.get("sha256") if isinstance(record, dict) else None


def command_response(result: dict[str, Any], transcript: bytes) -> bytes:
    commands = result.get("commands")
    require(isinstance(commands, list) and len(commands) == 1,
            "display run does not contain exactly one command")
    command = commands[0]
    require(isinstance(command, dict) and command.get("name") == "vidtest" and
            command.get("command") == "VIDTEST" and
            command.get("result") == "pass",
            "display VIDTEST command did not pass")
    start = command.get("response_start")
    end = command.get("response_end")
    require(isinstance(start, int) and isinstance(end, int) and
            0 <= start <= end <= len(transcript),
            "display command transcript offsets differ")
    return transcript[start:end]


def summarize_run(result: dict[str, Any], transcript: bytes,
                  mode: int) -> dict[str, Any]:
    raw_s21, geometry, mode_marker = MODES[mode]
    require(result.get("status") == "pass" and
            result.get("profile") == "display",
            f"display mode {mode} run did not pass")
    require(result.get("board") == "CS00015",
            f"display mode {mode} board differs")
    require(artifact_hash(result, "system") == performance.OPTIMIZED_SYSTEM,
            f"display mode {mode} system differs")
    require(artifact_hash(result, "fast_stage") == performance.OPTIMIZED_FASTBOOT,
            f"display mode {mode} Fastboot differs")
    require(artifact_hash(result, "rom") == closure.ROM,
            f"display mode {mode} ROM differs")
    require(artifact_hash(result, "volume") == closure.FULL_VOLUME,
            f"display mode {mode} full volume differs")
    workload = result.get("workload")
    require(isinstance(workload, dict) and
            workload.get("sha256") == DISPLAY_WORKLOAD,
            f"display mode {mode} workload differs")
    response = command_response(result, transcript)
    for marker in (
        "Juku Vidtest 1.0", mode_marker, LOCALE,
        "VIDTEST READY", "Juku Vidtest 1.0 DONE",
    ):
        require(marker.encode("ascii") in response,
                f"display mode {mode} transcript lacks {marker!r}")
    return {
        "mode": mode,
        "raw_s21": raw_s21,
        "geometry": geometry,
        "board": "CS00015",
        "system_sha256": performance.OPTIMIZED_SYSTEM,
        "fastboot_sha256": performance.OPTIMIZED_FASTBOOT,
        "rom_sha256": closure.ROM,
        "volume_sha256": closure.FULL_VOLUME,
        "workload_sha256": DISPLAY_WORKLOAD,
        "host_server_sha256": artifact_hash(result, "host_server"),
        "response_sha256": hashlib.sha256(response).hexdigest(),
    }


def validate_observation(observation: dict[str, Any], mode: int,
                         base: Path) -> dict[str, Any]:
    raw_s21, geometry, _ = MODES[mode]
    require(observation.get("raw_s21") == raw_s21,
            f"display mode {mode} raw S21 differs")
    require(observation.get("geometry") == geometry,
            f"display mode {mode} geometry differs")
    for field in ("glyphs_readable", "locale_stable", "cursor_blinked"):
        require(observation.get(field) is True,
                f"display mode {mode} {field} did not pass")
    require(observation.get("framebuffer_fault") is False,
            f"display mode {mode} reports a framebuffer fault")
    edges_visible = observation.get("edges_visible")
    require(isinstance(edges_visible, bool),
            f"display mode {mode} edge observation is absent")
    cropping = observation.get("monitor_cropping")
    require(isinstance(cropping, str),
            f"display mode {mode} cropping note is absent")
    require(edges_visible or bool(cropping.strip()),
            f"display mode {mode} hides edges without a cropping record")
    joined = observation.get("joined_cp437")
    if mode == 3:
        require(joined is True,
                "display mode 3 CP437 border did not join")
    else:
        require(joined == "not-applicable",
                f"display mode {mode} CP437 result must be not-applicable")
    photos = observation.get("photos")
    require(isinstance(photos, list) and photos,
            f"display mode {mode} has no photograph")
    photo_records = []
    for number, photo in enumerate(photos, 1):
        require(isinstance(photo, dict),
                f"display mode {mode} photo {number} is malformed")
        path = bundled_path(base, photo.get("path"),
                            f"display mode {mode} photo {number}")
        require(path.is_file(), f"display mode {mode} photo is missing: {path}")
        digest = sha256(path)
        require(photo.get("sha256") == digest,
                f"display mode {mode} photo hash differs: {path}")
        photo_records.append({
            "path": str(path), "bytes": path.stat().st_size, "sha256": digest,
        })
    return {
        "edges_visible": edges_visible,
        "glyphs_readable": True,
        "locale_stable": True,
        "cursor_blinked": True,
        "joined_cp437": joined,
        "framebuffer_fault": False,
        "monitor_cropping": cropping,
        "notes": str(observation.get("notes", "")),
        "photos": photo_records,
    }


def accept(document: dict[str, Any], results: dict[int, dict[str, Any]],
           transcripts: dict[int, bytes], base: Path) -> dict[str, Any]:
    require(document.get("schema") == SCHEMA,
            "display observation schema differs")
    require(document.get("board") == "CS00015",
            "display observation board differs")
    monitor = document.get("monitor")
    require(isinstance(monitor, dict), "display monitor identity is absent")
    for field in ("manufacturer", "model", "input"):
        require(isinstance(monitor.get(field), str) and
                bool(monitor[field].strip()),
                f"display monitor {field} is absent")
    observations = document.get("observations")
    require(isinstance(observations, list) and len(observations) == 4,
            "display observation count differs")
    require(all(isinstance(record, dict) and
                isinstance(record.get("mode"), int)
                for record in observations),
            "display observation mode record is malformed")
    mapped = {record["mode"]: record for record in observations}
    require(set(mapped) == set(MODES),
            "display modes are missing or duplicated")
    require(set(results) == set(MODES) and set(transcripts) == set(MODES),
            "display result set differs")
    accepted = []
    for mode in MODES:
        run = summarize_run(results[mode], transcripts[mode], mode)
        observed = validate_observation(mapped[mode], mode, base)
        accepted.append({**run, "observation": observed})
    hosts = {record["host_server_sha256"] for record in accepted}
    require(len(hosts) == 1 and None not in hosts,
            "display runs use different host servers")
    return {
        "schema": REPORT_SCHEMA,
        "status": "pass",
        "decision": (
            "all four exact display runs and human analog observations pass"
        ),
        "board": "CS00015",
        "monitor": {
            "manufacturer": monitor["manufacturer"],
            "model": monitor["model"],
            "input": monitor["input"],
            "notes": str(monitor.get("notes", "")),
        },
        "modes": accepted,
    }


def observation_directories(document: dict[str, Any], base: Path) \
        -> dict[int, Path]:
    observations = document.get("observations")
    require(isinstance(observations, list), "display observations are absent")
    directories: dict[int, Path] = {}
    for record in observations:
        require(isinstance(record, dict) and isinstance(record.get("mode"), int)
                and isinstance(record.get("result_directory"), str),
                "display result-directory record is malformed")
        directories[record["mode"]] = bundled_path(
            base, record["result_directory"],
            f"display mode {record['mode']} result directory",
        )
    require(set(directories) == set(MODES), "display result directories differ")
    return directories


def build_report(observation_path: Path) -> dict[str, Any]:
    observation_path = observation_path.resolve()
    document = json.loads(observation_path.read_text())
    require(isinstance(document, dict), "display observations are not an object")
    directories = observation_directories(document, observation_path.parent)
    for mode, directory in directories.items():
        failures = acceptance.audit_directory(directory)
        require(not failures, f"display mode {mode} audit failed: {failures}")
    results = {
        mode: json.loads((directory / "result.json").read_text())
        for mode, directory in directories.items()
    }
    transcripts = {
        mode: (directory / "console.bin").read_bytes()
        for mode, directory in directories.items()
    }
    report = accept(
        document, results, transcripts, observation_path.parent.resolve(),
    )
    report["inputs"] = {
        "observations": {
            "path": str(observation_path), "sha256": sha256(observation_path),
        },
        "results": {
            str(mode): {
                "directory": str(directory),
                "result_sha256": sha256(directory / "result.json"),
            }
            for mode, directory in directories.items()
        },
    }
    return report


def audit_report(report: dict[str, Any]) -> dict[str, Any]:
    require(report.get("schema") == REPORT_SCHEMA and
            report.get("status") == "pass",
            "display acceptance report identity differs")
    inputs = report.get("inputs")
    require(isinstance(inputs, dict), "display acceptance inputs are absent")
    observations = inputs.get("observations")
    require(isinstance(observations, dict) and
            isinstance(observations.get("path"), str) and
            isinstance(observations.get("sha256"), str),
            "display observation input is malformed")
    path = Path(observations["path"]).resolve()
    require(sha256(path) == observations["sha256"],
            "display observation hash differs")
    expected = build_report(path)
    require(report == expected, "display acceptance report differs from evidence")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.observations)
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(args.output)
    print("DISPLAY-ACCEPTANCE: PASS (40x24, 53x24, 64x20, 80x24)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DisplayError, OSError, ValueError) as error:
        print(f"display-acceptance: {error}")
        raise SystemExit(1)
