#!/usr/bin/env python3
"""Prove the C10 burn-ready candidate package is reproducible and bound."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/package_release_candidate.py"
CANDIDATE = "cpm-plus-3.1-juku-c10-pof-release-candidate"
EXPECTED_STATUS = "desk-qualified and ready for physical programming"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(path: Path) -> Path:
    subprocess.run(
        ["python3", str(SCRIPT), "--variant", "c10", "--output", str(path)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    return Path(str(path) + ".tar")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cpm-plus-c10-package-") as name:
        temporary = Path(name)
        first = temporary / f"one/{CANDIDATE}"
        second = temporary / f"two/{CANDIDATE}"
        first_tar, second_tar = build(first), build(second)
        if first_tar.read_bytes() != second_tar.read_bytes():
            raise AssertionError("C10 candidate archives are not byte-identical")

        manifest = json.loads((first / "manifest.json").read_text())
        if manifest.get("candidate") != CANDIDATE or \
                manifest.get("rom_abi") != "1.4" or \
                manifest.get("status") != EXPECTED_STATUS or \
                manifest.get("physical_programming_ready") is not True or \
                manifest.get("physical_programming_authorized") is not None:
            raise AssertionError("C10 package identity/readiness differs")
        expected_order = [
            "juku-network-rom-abi1.4-c10-d15.bin",
            "juku-network-rom-abi1.4-c10-d16.bin",
        ]
        if manifest.get("programmer_order") != expected_order:
            raise AssertionError("C10 programmer order differs")
        readme = (first / "README.txt").read_text()
        if "Program D15-low" not in readme or "D16-high" not in readme or \
                "physical EPROM programming is not authorized" in readme:
            raise AssertionError("C10 package bench instructions differ")
        for filename, record in manifest["files"].items():
            path = first / filename
            if record != {"bytes": path.stat().st_size,
                          "sha256": digest(path)}:
                raise AssertionError(f"C10 file binding differs: {filename}")

        stem = "juku-network-rom-abi1.4-c10"
        metadata = json.loads((first / f"{stem}.json").read_text())
        if metadata.get("status") != \
                "desk-qualified POF-release successor; physical acceptance pending" or \
                metadata.get("video_enable", {}).get(
                    "successful_runtime_port_c") != "01":
            raise AssertionError("C10 ROM readiness/POF metadata differs")
        if (first / f"{stem}-d15.bin").read_bytes() + \
                (first / f"{stem}-d16.bin").read_bytes() != \
                (first / f"{stem}.bin").read_bytes():
            raise AssertionError("C10 D15/D16 order differs")
        build_map = json.loads((first / "memory-map.json").read_text())
        if build_map["ram"].get("transient") != \
                "0100h..9BFFh (39680 bytes)" or \
                not build_map["ram"].get("adapter", "").startswith("C200h") or \
                build_map.get("tpa_gain_over_frozen_ram_bios") != 8704:
            raise AssertionError("C10 package memory map differs")
        boot = json.loads((first / "cpm-plus-juku-c10-manifest.json").read_text())
        if boot.get("requirements", {}).get("rom_abi") != "1.4" or \
                boot.get("rom", {}).get("candidate") != \
                "network-first-abi1.4-c10-pof-release-candidate":
            raise AssertionError("packaged C10 boot manifest differs")
        if not (first / "cpm-plus-juku-c10-full.img").is_file():
            raise AssertionError("C10 package omits STATUS/DIAG volume")
        for filename in (
                "c10-physical-acceptance-worksheet.md",
                "c10-cold.json", "c10-display.json", "c10-full.json"):
            if not (first / filename).is_file():
                raise AssertionError(
                    f"C10 package omits burn-day input {filename}"
                )
        print(
            "C10-RELEASE-CANDIDATE: PASS "
            f"(reproducible tar {digest(first_tar)}, burn-ready bound files)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
