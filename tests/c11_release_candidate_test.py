#!/usr/bin/env python3
"""Prove the C11 burn-ready candidate package is reproducible and bound."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/package_release_candidate.py"
CANDIDATE = "cpm-plus-3.1-juku-c11-post-raster-candidate"
EXPECTED_STATUS = "desk-qualified and ready for focused physical programming"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(path: Path) -> Path:
    subprocess.run(
        ["python3", str(SCRIPT), "--variant", "c11", "--output", str(path)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    return Path(str(path) + ".tar")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cpm-plus-c11-package-") as name:
        temporary = Path(name)
        first = temporary / f"one/{CANDIDATE}"
        second = temporary / f"two/{CANDIDATE}"
        first_tar, second_tar = build(first), build(second)
        if first_tar.read_bytes() != second_tar.read_bytes():
            raise AssertionError("C11 candidate archives are not byte-identical")

        manifest = json.loads((first / "manifest.json").read_text())
        if manifest.get("candidate") != CANDIDATE or \
                manifest.get("rom_abi") != "1.4" or \
                manifest.get("status") != EXPECTED_STATUS or \
                manifest.get("physical_programming_ready") is not True or \
                manifest.get("physical_programming_authorized") is not None:
            raise AssertionError("C11 package identity/readiness differs")
        expected_order = [
            "juku-network-rom-abi1.4-c11-d15.bin",
            "juku-network-rom-abi1.4-c11-d16.bin",
        ]
        if manifest.get("programmer_order") != expected_order:
            raise AssertionError("C11 programmer order differs")
        readme = (first / "README.txt").read_text()
        if "Program D15-low" not in readme or "D16-high" not in readme or \
                "physical EPROM programming is not authorized" in readme:
            raise AssertionError("C11 package bench instructions differ")
        for filename, record in manifest["files"].items():
            path = first / filename
            if record != {"bytes": path.stat().st_size,
                          "sha256": digest(path)}:
                raise AssertionError(f"C11 file binding differs: {filename}")

        stem = "juku-network-rom-abi1.4-c11"
        metadata = json.loads((first / f"{stem}.json").read_text())
        video = metadata.get("video_enable", {})
        clear = metadata.get("console", {}).get(
            "physical_raster_clear_bytes", {})
        if metadata.get("status") != \
                "deterministic POST/raster simulator candidate; C10 remains immutable" or \
                video.get("release_after") != \
                "deterministic-320x241-checkerboard" or \
                video.get("checkerboard") != "8x8-full-raster" or \
                clear.get("implementation_envelope") != 9648:
            raise AssertionError("C11 ROM raster metadata differs")
        if (first / f"{stem}-d15.bin").read_bytes() + \
                (first / f"{stem}-d16.bin").read_bytes() != \
                (first / f"{stem}.bin").read_bytes():
            raise AssertionError("C11 D15/D16 order differs")

        build_map = json.loads((first / "memory-map.json").read_text())
        if build_map["ram"].get("transient") != \
                "0100h..9BFFh (39680 bytes)" or \
                not build_map["ram"].get("adapter", "").startswith("C200h") or \
                not build_map["ram"].get(
                    "physical_raster_clear", "").startswith("D800h..FDAFh") or \
                build_map.get("tpa_gain_over_frozen_ram_bios") != 8704:
            raise AssertionError("C11 package memory map differs")
        boot = json.loads((first / "cpm-plus-juku-c11-manifest.json").read_text())
        if boot.get("requirements", {}).get("rom_abi") != "1.4" or \
                boot.get("rom", {}).get("candidate") != \
                "network-first-abi1.4-c11-post-raster-candidate":
            raise AssertionError("packaged C11 boot manifest differs")
        if not (first / "cpm-plus-juku-c11-full.img").is_file():
            raise AssertionError("C11 package omits STATUS/DIAG volume")
        for filename in (
                "c11-physical-acceptance-worksheet.md",
                "c11-cold.json", "c11-display.json", "c11-full.json"):
            if not (first / filename).is_file():
                raise AssertionError(
                    f"C11 package omits burn-day input {filename}"
                )
        print(
            "C11-RELEASE-CANDIDATE: PASS "
            f"(reproducible tar {digest(first_tar)}, burn-ready bound files)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
