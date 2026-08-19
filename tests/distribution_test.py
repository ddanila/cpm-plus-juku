#!/usr/bin/env python3
"""Regression checks for licensed, reproducible CP/M volume profiles."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/build_volume.py"
CASES = {
    "recovery": (
        ROOT / "volume/profiles/recovery.json",
        ROOT / "out/cpm-plus-juku-recovery.img",
        ROOT / "out/cpm-plus-juku-recovery.report.json",
        {"CCP.COM", "DIAG.COM", "WBOOT.COM", "README.TXT"},
        409600,
    ),
    "full": (
        ROOT / "volume/profiles/full.json",
        ROOT / "out/cpm-plus-juku-full.img",
        ROOT / "out/cpm-plus-juku-full.report.json",
        {
            "CCP.COM", "DIAG.COM", "WBOOT.COM", "README.TXT", "PIP.COM",
            "SHOW.COM", "SET.COM", "DEVICE.COM", "DATE.COM", "SUBMIT.COM",
            "SETDEF.COM", "DUMP.COM", "HELP.COM", "HELP.HLP", "STATUS.COM",
            "KEYTEST.COM", "VIDTEST.COM", "CRC.COM", "CMP.COM", "MEM.COM", "WC.COM",
            "FIND.COM", "STRINGS.COM", "HIST.COM", "TOOLS.TXT",
        },
        409600,
    ),
    "dev": (
        ROOT / "volume/profiles/dev.json",
        ROOT / "out/cpm-plus-juku-dev.img",
        ROOT / "out/cpm-plus-juku-dev.report.json",
        {
            "CCP.COM", "DIAG.COM", "WBOOT.COM", "README.TXT", "PIP.COM",
            "SHOW.COM", "SET.COM", "DEVICE.COM", "DATE.COM", "SUBMIT.COM",
            "SETDEF.COM", "DUMP.COM", "HELP.COM", "HELP.HLP", "STATUS.COM",
            "KEYTEST.COM", "VIDTEST.COM", "CRC.COM", "CMP.COM", "MEM.COM", "WC.COM",
            "FIND.COM", "STRINGS.COM", "HIST.COM", "TOOLS.TXT", "HEXCOM.COM",
            "PATCH.COM", "SID.COM", "ED.COM",
            "HELLO.ASM", "HELLO.HEX",
        },
        409600,
    ),
    "native-recovery": (
        ROOT / "volume/profiles/native-recovery.json",
        ROOT / "out/cpm-plus-juku-native-recovery.img",
        ROOT / "out/cpm-plus-juku-native-recovery.report.json",
        {
            "CCP.COM", "DIAG.COM", "WBOOT.COM", "README.TXT", "STATUS.COM",
            "KEYTEST.COM",
        },
        409600,
    ),
    "apps": (
        ROOT / "volume/profiles/apps.json",
        ROOT / "out/cpm-plus-juku-apps.juk",
        ROOT / "out/cpm-plus-juku-apps.report.json",
        {"README.TXT", "DIAG.COM"},
        819200,
    ),
    "demo": (
        ROOT / "volume/profiles/demo.json",
        ROOT / "out/cpm-plus-juku-museum-demo.img",
        ROOT / "out/cpm-plus-juku-museum-demo.report.json",
        {
            "CCP.COM", "DIAG.COM", "WBOOT.COM", "README.TXT", "PIP.COM",
            "SHOW.COM", "SET.COM", "DEVICE.COM", "DATE.COM", "SUBMIT.COM",
            "SETDEF.COM", "DUMP.COM", "HELP.COM", "HELP.HLP", "STATUS.COM",
            "KEYTEST.COM", "VIDTEST.COM", "CRC.COM", "CMP.COM", "MEM.COM", "WC.COM",
            "FIND.COM", "STRINGS.COM", "HIST.COM", "TOOLS.TXT",
            "PROFILE.SUB",
        },
        409600,
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def cpm_names(image: Path, geometry: str) -> set[str]:
    environment = {**os.environ, "DISKDEFS": str(ROOT / "diskdefs")}
    result = subprocess.run(
        ["cpmls", "-f", geometry, "-d", str(image)],
        cwd=ROOT, env=environment, check=True, capture_output=True, text=True,
    )
    names: set[str] = set()
    for line in result.stdout.splitlines():
        for item in line.split(":"):
            parts = item.split()
            if len(parts) == 2:
                names.add(f"{parts[0]}.{parts[1]}")
    return names


def juku_image_to_logical(image: bytes) -> bytes:
    track_bytes = 40 * 128
    tracks_per_side = 80
    require(len(image) == 2 * tracks_per_side * track_bytes,
            "native Juku image size differs")
    logical = bytearray(len(image))
    for cylinder in range(tracks_per_side):
        for side in range(2):
            source = (cylinder * 2 + side) * track_bytes
            target = (side * tracks_per_side + cylinder) * track_bytes
            logical[target:target + track_bytes] = image[
                source:source + track_bytes
            ]
    return bytes(logical)


def generated_profiles_are_stable() -> None:
    with tempfile.TemporaryDirectory(prefix="cpm-plus-distribution-test.") as name:
        directory = Path(name)
        for case, (profile, image, report, expected, size) in CASES.items():
            recorded = json.loads(report.read_text())
            require(recorded["schema"] == "cpm-plus-juku-volume-report-v1",
                    f"{case} report schema differs")
            require(recorded["image_bytes"] == size == image.stat().st_size,
                    f"{case} image size differs")
            require(recorded["image_sha256"] == sha256(image),
                    f"{case} report image hash differs")
            require(recorded["free_bytes"] > 0,
                    f"{case} has no reported free space")
            destinations = {
                item["destination"].split(":", 1)[1]
                for item in recorded["files"]
            }
            require(destinations == expected,
                    f"{case} report contents differ: {destinations}")
            for item in recorded["files"]:
                require(set(item["provenance"]) ==
                        {"source", "version", "license"},
                        f"{case} provenance differs for {item['destination']}")
            geometry = recorded["geometry"]
            inspected_image = image
            if recorded["output_layout"] == "juku-cylinder-head":
                inspected_image = directory / f"{case}-logical.img"
                inspected_image.write_bytes(juku_image_to_logical(
                    image.read_bytes()
                ))
            require(cpm_names(inspected_image, geometry) == expected,
                    f"{case} CP/M directory differs")

            rebuilt = directory / f"{case}.img"
            rebuilt_report = directory / f"{case}.json"
            subprocess.run(
                ["python3", str(TOOL), "--profile", str(profile),
                 "--output", str(rebuilt), "--report", str(rebuilt_report)],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            require(rebuilt.read_bytes() == image.read_bytes(),
                    f"{case} volume is not reproducible")
            require(json.loads(rebuilt_report.read_text()) == recorded,
                    f"{case} report is not reproducible")

    require(
        (ROOT / "out/cpm-plus-juku-recovery.img").read_bytes() ==
        (ROOT / "prebuilt/cpm-plus-juku.img").read_bytes(),
        "named recovery A: changed the immutable C4 qualification volume",
    )
    require(
        (ROOT / "out/cpm-plus-juku.img").read_bytes() ==
        (ROOT / "out/cpm-plus-juku-recovery.img").read_bytes(),
        "compatibility A: alias differs from named recovery A:",
    )


def malformed_profiles_fail_closed() -> None:
    original = json.loads((ROOT / "volume/profiles/recovery.json").read_text())
    with tempfile.TemporaryDirectory(prefix="cpm-plus-profile-negative.") as name:
        directory = Path(name)
        for label, mutation in (
            ("checksum", lambda value: value["files"][0].__setitem__(
                "sha256", "0" * 64)),
            ("escape", lambda value: value["files"][0].__setitem__(
                "source", "/etc/passwd")),
            ("duplicate", lambda value: value["files"].append(
                dict(value["files"][0]))),
            ("attributes", lambda value: value["files"][0].__setitem__(
                "attributes", "system")),
        ):
            candidate = json.loads(json.dumps(original))
            mutation(candidate)
            profile = directory / f"{label}.json"
            profile.write_text(json.dumps(candidate))
            result = subprocess.run(
                ["python3", str(TOOL), "--profile", str(profile),
                 "--output", str(directory / f"{label}.img")],
                cwd=ROOT, capture_output=True, text=True,
            )
            require(result.returncode != 0,
                    f"malformed {label} profile was accepted")

        parent = "recovery.json"
        for label, override in (
            ("orphan-override", {
                "source": "build/diag.cim",
                "destination": "0:MISSING.COM",
                "override": True,
            }),
            ("typed-override", {
                "source": "build/diag.cim",
                "destination": "0:DIAG.COM",
                "override": "yes",
            }),
        ):
            candidate = {
                "schema": "cpm-plus-juku-volume-profile-v1",
                "extends": parent,
                "name": label,
                "description": "negative inherited override fixture",
                "files": [override],
            }
            with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json",
                    dir=ROOT / "volume/profiles") as profile:
                json.dump(candidate, profile)
                profile.flush()
                result = subprocess.run(
                    ["python3", str(TOOL), "--profile", profile.name,
                     "--output", str(directory / f"{label}.img")],
                    cwd=ROOT, capture_output=True, text=True,
                )
            require(result.returncode != 0,
                    f"malformed {label} profile was accepted")


def main() -> int:
    generated_profiles_are_stable()
    malformed_profiles_fail_closed()
    print(
        "DISTRIBUTION: PASS "
        "(recovery/full/dev/native-B profiles and reports)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
