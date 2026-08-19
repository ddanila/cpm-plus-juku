#!/usr/bin/env python3
"""Verify the C8 resident-host image pair and its measured 512-byte TPA gain."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
COSIM = ROOT.parent / "8080-cosim"
SYSTEM = ROOT / "out" / "cpm-plus-juku-network-rom-c8-system.bin"
FASTBOOT = ROOT / "out" / "cpm-plus-juku-network-rom-c8-fastboot-v16.bin"
MANIFEST = ROOT / "out" / "cpm-plus-juku-c8-manifest.json"
ROM = COSIM / "spinoffs" / "jukuravi" / "network-rom" / \
    "juku-network-rom-abi1.3-c8.bin"
ROM_METADATA = ROM.with_suffix(".json")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    system = SYSTEM.read_bytes()
    fastboot = FASTBOOT.read_bytes()
    manifest = json.loads(MANIFEST.read_text())
    rom = ROM.read_bytes()
    metadata = json.loads(ROM_METADATA.read_text())

    require(system[:8] == b"JUKURM1\x1a", "C8 system magic differs")
    load = int.from_bytes(system[8:10], "little")
    entry = int.from_bytes(system[10:12], "little")
    payload = int.from_bytes(system[12:14], "little")
    require((load, entry, payload) == (0x9000, 0xBE00, 0x4600),
            "C8 RAM container map differs")
    adapter = entry + 0x400
    bdos = entry - 0x1F00
    loader = entry - 0x2200
    tpa_top = loader - 1
    require((loader, bdos, adapter, tpa_top) ==
            (0x9C00, 0x9F00, 0xC200, 0x9BFF),
            "C8 relocation arithmetic differs")
    require(tpa_top - 0x0100 + 1 == 39680,
            "C8 TPA is not 39,680 bytes")
    require((tpa_top - 0x99FF) == 0x200,
            "C8 did not gain exactly 512 bytes over C6/C7")

    require(fastboot[3:7] == b"JF16", "C8 stage is not Fastboot v16")
    require(metadata["abi"] == {"base": "FF00", "major": 1, "minor": 3},
            "C8 ROM metadata ABI differs")
    require(metadata["abi_vectors"].get("host_services") == "FF5C",
            "C8 host-service vector differs")
    require(metadata["feature_bits"].get("value") == "0FFF",
            "C8 feature mask differs")
    require(sum(rom[0x1800:]) & 0xFF == 0,
            "C8 resident D800h..FFFFh checksum differs")
    require(metadata["post_audio"] == {
        "C1": "short-short-long",
        "C2": "short-long-short",
        "C3": "short-long-long",
        "C4": "long-short-short",
        "C5": "long-short-long",
        "success_and_host_wait": "silent",
    }, "C8 POST audio vocabulary differs")

    require(manifest["build_identity"].startswith("c8-"),
            "C8 manifest identity differs")
    require(manifest["system"]["entry_address"] == entry,
            "C8 manifest entry differs")
    require(manifest["system"]["sha256"] == sha256(system),
            "C8 manifest system hash differs")
    require(manifest["fast_stage"]["sha256"] == sha256(fastboot),
            "C8 manifest fastboot hash differs")
    require(manifest["rom"]["sha256"] == sha256(rom),
            "C8 manifest ROM hash differs")

    print(
        "C8-LAYOUT-TEST: PASS "
        "TPA 0100h..9BFFh (39,680 bytes, +512); "
        "BDOS 9F00h; BIOS BE00h; adapter C200h; ABI 1.3"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
