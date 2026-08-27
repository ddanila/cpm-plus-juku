#!/usr/bin/env python3
"""Verify the deterministic C9 ABI 1.4 ROM/system/package boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
COSIM = ROOT.parent / "8080-cosim"
ROM_DIR = COSIM / "spinoffs" / "jukuravi" / "network-rom"
ROM = ROM_DIR / "juku-network-rom-abi1.4-c9.bin"
D15 = ROM_DIR / "juku-network-rom-abi1.4-c9-d15.bin"
D16 = ROM_DIR / "juku-network-rom-abi1.4-c9-d16.bin"
METADATA = ROM.with_suffix(".json")
SYSTEM = ROOT / "out" / "cpm-plus-juku-network-rom-c9-system.bin"
FASTBOOT = ROOT / "out" / "cpm-plus-juku-network-rom-c9-fastboot-v16.bin"
VOLUME = ROOT / "out" / "cpm-plus-juku-c9-full.img"
MANIFEST = ROOT / "out" / "cpm-plus-juku-c9-manifest.json"

C8_ROM_SHA256 = "a54cb877edfe25e939e05ada0e98783acb53cfc8969071c63928b119c8e09e46"
C8_SYSTEM_SHA256 = "ec9b7fd00db2d8e70258aae74500fa261f987b6b04bddfdb5ab44e56ca2ba3f1"
C8_FASTBOOT_SHA256 = "44735bf468a2014bbcf327d5d0770d9fcf21a3c33704499282180ad6c95898ea"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    rom = ROM.read_bytes()
    d15 = D15.read_bytes()
    d16 = D16.read_bytes()
    metadata = json.loads(METADATA.read_text())
    system = SYSTEM.read_bytes()
    fastboot = FASTBOOT.read_bytes()
    volume = VOLUME.read_bytes()
    manifest = json.loads(MANIFEST.read_text())

    require(len(rom) == 0x4000 and len(d15) == len(d16) == 0x2000,
            "C9 ROM/half sizes differ")
    require(d15 + d16 == rom, "C9 D15 followed by D16 differs from combined")
    require(metadata["image_sha256"] == sha256(rom) and
            metadata["d15_sha256"] == sha256(d15) and
            metadata["d16_sha256"] == sha256(d16),
            "C9 ROM metadata hashes differ")
    require(sum(rom) & 0xFF == 0 and sum(rom[0x1800:]) & 0xFF == 0,
            "C9 complete/resident ROM checksum differs")
    require(rom[0x3F00:0x3F0A] == b"JUKUABI\0\x01\x04",
            "C9 ABI manifest/version differs")
    require(metadata["abi"] == {"base": "FF00", "major": 1, "minor": 4} and
            metadata["abi_vectors"].get("host_services") == "FF5C" and
            metadata["feature_bits"].get("value") == "0FFF",
            "C9 ABI/vector/features differ")
    require(metadata["boot_policy"] == {
        "s21_bit": 0,
        "behavior": "reserved; unconditional network boot",
    }, "C9 boot policy metadata differs")
    require(metadata["resident_host"].get("state_bytes") == 4 and
            set(metadata["resident_host"]["failure_reasons"]) ==
            {"00", "01", "02", "03", "04", "05", "06"},
            "C9 host state/reason metadata differs")

    require(system[:8] == b"JUKURM1\x1a", "C9 system magic differs")
    load = int.from_bytes(system[8:10], "little")
    entry = int.from_bytes(system[10:12], "little")
    payload = int.from_bytes(system[12:14], "little")
    require((load, entry, payload) == (0x9000, 0xBE00, 0x4600),
            "C9 RAM container map differs")
    loader = entry - 0x2200
    bdos = entry - 0x1F00
    adapter = entry + 0x400
    require((loader, bdos, adapter, loader - 1) ==
            (0x9C00, 0x9F00, 0xC200, 0x9BFF),
            "C9 relocation/TPA arithmetic differs")
    require(loader - 0x0100 == 39680, "C9 TPA is not 39,680 bytes")
    require(fastboot[3:7] == b"JF16", "C9 stage is not Fastboot v16")

    require(manifest["build_identity"].startswith("c9-"),
            "C9 manifest identity differs")
    require(manifest["system"]["sha256"] == sha256(system) and
            manifest["fast_stage"]["sha256"] == sha256(fastboot) and
            manifest["rom"]["sha256"] == sha256(rom),
            "C9 manifest artifact hashes differ")
    c9_volume = next((item for item in manifest["volumes"]
                      if item["file"] == VOLUME.name), None)
    require(c9_volume is not None and c9_volume["sha256"] == sha256(volume) and
            c9_volume["profile"] == "c9-full-a",
            "C9 manifest volume binding differs")

    require(sha256((ROM_DIR / "juku-network-rom-abi1.3-c8.bin").read_bytes()) ==
            C8_ROM_SHA256, "C9 work changed the immutable C8 ROM")
    require(sha256((ROOT / "out/cpm-plus-juku-network-rom-c8-system.bin")
                   .read_bytes()) == C8_SYSTEM_SHA256,
            "C9 work changed the immutable C8 system")
    require(sha256((ROOT / "out/cpm-plus-juku-network-rom-c8-fastboot-v16.bin")
                   .read_bytes()) == C8_FASTBOOT_SHA256,
            "C9 work changed the immutable C8 Fastboot stage")

    print(
        "C9-LAYOUT-TEST: PASS "
        f"ROM {sha256(rom)}; TPA 0100h..9BFFh; ABI 1.4; C8 immutable"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
