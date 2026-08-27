#!/usr/bin/env python3
"""Verify the deterministic C10 POF-release ROM/system/media boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COSIM = ROOT.parent / "8080-cosim"
ROM_DIR = COSIM / "spinoffs/jukuravi/network-rom"
STEM = "juku-network-rom-abi1.4-c10"
ROM = ROM_DIR / f"{STEM}.bin"
D15 = ROM_DIR / f"{STEM}-d15.bin"
D16 = ROM_DIR / f"{STEM}-d16.bin"
METADATA = ROM_DIR / f"{STEM}.json"
SYSTEM = ROOT / "out/cpm-plus-juku-network-rom-c10-system.bin"
FASTBOOT = ROOT / "out/cpm-plus-juku-network-rom-c10-fastboot-v16.bin"
VOLUME = ROOT / "out/cpm-plus-juku-c10-full.img"
MANIFEST = ROOT / "out/cpm-plus-juku-c10-manifest.json"
C9_ROM = ROM_DIR / "juku-network-rom-abi1.4-c9.bin"
C9_SYSTEM = ROOT / "out/cpm-plus-juku-network-rom-c9-system.bin"
C9_FASTBOOT = ROOT / "out/cpm-plus-juku-network-rom-c9-fastboot-v16.bin"
C9_SHA256 = "352417fafcf1ceaef40b8d39916acdaee6de03d914eafe2b54185ccbabe35530"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    rom, d15, d16 = ROM.read_bytes(), D15.read_bytes(), D16.read_bytes()
    metadata = json.loads(METADATA.read_text())
    system, fastboot = SYSTEM.read_bytes(), FASTBOOT.read_bytes()
    volume = VOLUME.read_bytes()
    manifest = json.loads(MANIFEST.read_text())

    require(len(rom) == 0x4000 and len(d15) == len(d16) == 0x2000,
            "C10 ROM/half sizes differ")
    require(d15 + d16 == rom, "C10 D15 followed by D16 differs from combined")
    require(metadata["image_sha256"] == digest(rom) and
            metadata["d15_sha256"] == digest(d15) and
            metadata["d16_sha256"] == digest(d16),
            "C10 ROM metadata hashes differ")
    require(sum(rom) & 0xFF == 0 and sum(rom[0x1800:]) & 0xFF == 0,
            "C10 complete/resident checksums differ")
    require(rom[0x3F00:0x3F0A] == b"JUKUABI\0\x01\x04",
            "C10 ABI manifest/version differs")
    require(metadata.get("candidate") ==
            "network-first-abi1.4-c10-pof-release-candidate" and
            metadata.get("abi") == {"base": "FF00", "major": 1, "minor": 4},
            "C10 candidate/ABI differs")
    require(metadata.get("video_enable") == {
        "ppi0_port_c_bit": 7,
        "signal": "POF",
        "post_state": "high-picture-suppressed",
        "runtime_state": "low-picture-enabled",
        "successful_runtime_port_c": "01",
        "ordered_control_writes": ["82", "0F", "0E"],
        "physical_evidence":
            "CS00000 C9 live 0E write restored local video 2026-08-27",
    }, "C10 POF contract metadata differs")
    require(metadata["hardware_init"][0] == "ppi0-82-pc7-high-then-low",
            "C10 hardware initialization metadata omits POF release")
    require(b"JukuNet C10 ROM ABI 1.4 physical POF release" in rom,
            "C10 resident identity differs")

    require(system == C9_SYSTEM.read_bytes(),
            "C10 loaded system differs from qualified C9 carry-forward")
    require(fastboot == C9_FASTBOOT.read_bytes(),
            "C10 Fastboot differs from qualified C9 carry-forward")
    require(system[:8] == b"JUKURM1\x1a" and fastboot[3:7] == b"JF16",
            "C10 system/Fastboot formats differ")
    load = int.from_bytes(system[8:10], "little")
    entry = int.from_bytes(system[10:12], "little")
    payload = int.from_bytes(system[12:14], "little")
    require((load, entry, payload) == (0x9000, 0xBE00, 0x4600),
            "C10 RAM container map differs")
    require(entry - 0x2200 - 0x0100 == 39680,
            "C10 TPA is not 39,680 bytes")

    require(manifest["build_identity"].startswith("c10-"),
            "C10 manifest identity differs")
    require(manifest["system"]["sha256"] == digest(system) and
            manifest["fast_stage"]["sha256"] == digest(fastboot) and
            manifest["rom"]["sha256"] == digest(rom),
            "C10 manifest artifact bindings differ")
    record = next((item for item in manifest["volumes"]
                   if item["file"] == VOLUME.name), None)
    require(record is not None and record["sha256"] == digest(volume) and
            record["profile"] == "c10-full-a",
            "C10 full-volume binding differs")

    require(digest(C9_ROM.read_bytes()) == C9_SHA256,
            "C10 work changed immutable C9 ROM")
    print(
        "C10-LAYOUT-TEST: PASS "
        f"ROM {digest(rom)}; D15 {digest(d15)}; D16 {digest(d16)}; "
        "TPA 0100h..9BFFh; C9 system/Fastboot exact"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
