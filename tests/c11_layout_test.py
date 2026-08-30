#!/usr/bin/env python3
"""Verify the deterministic C11 POST-pattern/raster-clear boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROM_DIR = ROOT.parent / "8080-cosim/spinoffs/jukuravi/network-rom"
STEM = "juku-network-rom-abi1.4-c11"
ROM = ROM_DIR / f"{STEM}.bin"
D15 = ROM_DIR / f"{STEM}-d15.bin"
D16 = ROM_DIR / f"{STEM}-d16.bin"
METADATA = ROM_DIR / f"{STEM}.json"
SYSTEM = ROOT / "out/cpm-plus-juku-network-rom-c11-system.bin"
FASTBOOT = ROOT / "out/cpm-plus-juku-network-rom-c11-fastboot-v16.bin"
VOLUME = ROOT / "out/cpm-plus-juku-c11-full.img"
MANIFEST = ROOT / "out/cpm-plus-juku-c11-manifest.json"
C10_STEM = "juku-network-rom-abi1.4-c10"
C10_SHA256 = "fbf9baaad9027a5335e3549da3a396eb999bbaae1a1f3f5f6e2f36798848a6bc"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    rom, d15, d16 = ROM.read_bytes(), D15.read_bytes(), D16.read_bytes()
    metadata = json.loads(METADATA.read_text())
    system, fastboot, volume = (
        SYSTEM.read_bytes(), FASTBOOT.read_bytes(), VOLUME.read_bytes()
    )
    manifest = json.loads(MANIFEST.read_text())

    require(len(rom) == 0x4000 and len(d15) == len(d16) == 0x2000,
            "C11 ROM/half sizes differ")
    require(d15 + d16 == rom, "C11 D15 followed by D16 differs")
    require(metadata["image_sha256"] == digest(rom) and
            metadata["d15_sha256"] == digest(d15) and
            metadata["d16_sha256"] == digest(d16),
            "C11 ROM metadata hashes differ")
    require(sum(rom) & 0xFF == 0 and sum(rom[0x1800:]) & 0xFF == 0,
            "C11 complete/resident checksums differ")
    require(rom[0x3F00:0x3F0A] == b"JUKUABI\0\x01\x04",
            "C11 ABI manifest/version differs")
    require(metadata.get("candidate") ==
            "network-first-abi1.4-c11-post-raster-candidate" and
            metadata.get("abi") == {"base": "FF00", "major": 1, "minor": 4},
            "C11 candidate/ABI differs")
    require(metadata.get("checker_helper_bytes") == 47 and
            metadata.get("helper_bytes") == 128,
            "C11 low-RAM helper sizes differ")
    require(metadata["hardware_init"][0] ==
            "ppi0-82-checker-pc7-high-then-low",
            "C11 checker/POF ordering metadata differs")
    require(metadata.get("video_enable", {}).get("release_after") ==
            "deterministic-320x241-checkerboard" and
            metadata.get("video_enable", {}).get("checkerboard") ==
            "8x8-full-raster",
            "C11 deterministic checker metadata differs")
    require(metadata.get("console", {}).get("physical_raster_clear_bytes") == {
        "00": 9640, "01": 9640, "10": 9648, "11": 9600,
        "implementation_envelope": 9648,
    }, "C11 physical-raster clear metadata differs")
    require(b"JukuNet C11 ROM ABI 1.4 deterministic POST raster" in rom,
            "C11 resident identity differs")

    require(system == (ROOT / "out/cpm-plus-juku-network-rom-c10-system.bin").read_bytes(),
            "C11 loaded system differs from C10 carry-forward")
    require(fastboot ==
            (ROOT / "out/cpm-plus-juku-network-rom-c10-fastboot-v16.bin").read_bytes(),
            "C11 Fastboot differs from C10 carry-forward")
    require(volume == (ROOT / "out/cpm-plus-juku-c10-full.img").read_bytes(),
            "C11 qualification volume differs from C10 carry-forward")

    require(manifest["build_identity"].startswith("c11-"),
            "C11 manifest identity differs")
    require(manifest["system"]["sha256"] == digest(system) and
            manifest["fast_stage"]["sha256"] == digest(fastboot) and
            manifest["rom"]["sha256"] == digest(rom),
            "C11 manifest artifact bindings differ")
    record = next((item for item in manifest["volumes"]
                   if item["file"] == VOLUME.name), None)
    require(record is not None and record["sha256"] == digest(volume) and
            record["profile"] == "c11-full-a",
            "C11 full-volume binding differs")

    require(digest((ROM_DIR / f"{C10_STEM}.bin").read_bytes()) == C10_SHA256,
            "C11 work changed immutable C10 ROM")
    print(
        "C11-LAYOUT-TEST: PASS "
        f"ROM {digest(rom)}; D15 {digest(d15)}; D16 {digest(d16)}; "
        "checker helper 47 bytes; clear envelope 9648; C10 carry-forward exact"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
