#!/usr/bin/env python3
"""Prove the C12 simulator package is reproducible, bound, and non-physical."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/package_release_candidate.py"
CANDIDATE = "cpm-plus-3.1-juku-c12-runtime-console-simulator"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(path: Path) -> Path:
    subprocess.run(
        ["python3", str(SCRIPT), "--variant", "c12", "--output", str(path)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    return Path(str(path) + ".tar")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cpm-plus-c12-package-") as name:
        temporary = Path(name)
        first = temporary / f"one/{CANDIDATE}"
        second = temporary / f"two/{CANDIDATE}"
        first_tar, second_tar = build(first), build(second)
        if first_tar.read_bytes() != second_tar.read_bytes():
            raise AssertionError("C12 candidate archives are not byte-identical")

        manifest = json.loads((first / "manifest.json").read_text())
        if manifest.get("candidate") != CANDIDATE or \
                manifest.get("rom_abi") != "1.5" or \
                manifest.get("physical_programming_authorized") is not False or \
                manifest.get("physical_programming_ready") is not None:
            raise AssertionError("C12 package identity/safety boundary differs")
        expected_order = [
            "juku-network-rom-abi1.5-c12-d15.bin",
            "juku-network-rom-abi1.5-c12-d16.bin",
        ]
        if manifest.get("rom_half_order") != expected_order:
            raise AssertionError("C12 ROM-half order differs")
        readme = (first / "README.txt").read_text()
        if "physical EPROM programming is not authorized" not in readme:
            raise AssertionError("C12 package omits the non-physical warning")
        for filename, record in manifest["files"].items():
            path = first / filename
            if record != {"bytes": path.stat().st_size,
                          "sha256": digest(path)}:
                raise AssertionError(f"C12 file binding differs: {filename}")

        stem = "juku-network-rom-abi1.5-c12"
        metadata = json.loads((first / f"{stem}.json").read_text())
        if metadata.get("abi", {}).get("minor") != 5 or \
                metadata.get("feature_bits", {}).get("console_config") != \
                "1000" or metadata.get("abi_vectors", {}).get(
                    "console_config") != "FF5F" or \
                metadata.get("boot_discovery", {}).get("frame") != \
                "4A 42 0C 01 05" or \
                metadata.get("runtime_console", {}).get(
                    "keyboard_transition") != {
                        "pending_state": "discard", "key_remap": "preserve",
                    }:
            raise AssertionError("C12 ROM ABI/runtime metadata differs")
        if (first / f"{stem}-d15.bin").read_bytes() + \
                (first / f"{stem}-d16.bin").read_bytes() != \
                (first / f"{stem}.bin").read_bytes():
            raise AssertionError("C12 D15/D16 order differs")

        build_map = json.loads((first / "memory-map.json").read_text())
        if build_map["ram"].get("transient") != \
                "0100h..9BFFh (39680 bytes)" or \
                not build_map["ram"].get("adapter", "").startswith("C200h") or \
                not build_map["ram"].get(
                    "physical_raster_clear", "").startswith("D800h..FDAFh") or \
                build_map.get("tpa_gain_over_frozen_ram_bios") != 8704:
            raise AssertionError("C12 package memory map differs")
        boot = json.loads((first / "cpm-plus-juku-c12-manifest.json").read_text())
        if boot.get("requirements", {}).get("rom_abi") != "1.5" or \
                boot.get("rom", {}).get("candidate") != \
                "network-first-abi1.5-c12-runtime-console-candidate":
            raise AssertionError("packaged C12 boot manifest differs")
        if not (first / "cpm-plus-juku-c12-full.img").is_file():
            raise AssertionError("C12 package omits its runtime-console volume")

        print(
            "C12-SIMULATOR-CANDIDATE: PASS "
            f"(reproducible tar {digest(first_tar)}, physical burn disabled)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
