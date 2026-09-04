#!/usr/bin/env python3
"""Verify the deterministic C12 ABI/system/media boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROM_DIR = ROOT.parent / "8080-cosim/spinoffs/jukuravi/network-rom"
STEM = "juku-network-rom-abi1.5-c12"
ROM = ROM_DIR / f"{STEM}.bin"
D15 = ROM_DIR / f"{STEM}-d15.bin"
D16 = ROM_DIR / f"{STEM}-d16.bin"
METADATA = ROM_DIR / f"{STEM}.json"
SYSTEM = ROOT / "out/cpm-plus-juku-network-rom-c12-system.bin"
FASTBOOT = ROOT / "out/cpm-plus-juku-network-rom-c12-fastboot-v16.bin"
VOLUME = ROOT / "out/cpm-plus-juku-c12-full.img"
REPORT = ROOT / "out/cpm-plus-juku-c12-full.report.json"
MANIFEST = ROOT / "out/cpm-plus-juku-c12-manifest.json"
C11_SHA256 = "b93428bb33cd7e31c2d9b2b84aa07ea17edda76c9d53ab73b3cb8687e8d53dfd"


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
    report = json.loads(REPORT.read_text())
    manifest = json.loads(MANIFEST.read_text())

    require(len(rom) == 0x4000 and len(d15) == len(d16) == 0x2000,
            "C12 ROM/half sizes differ")
    require(d15 + d16 == rom, "C12 D15 followed by D16 differs")
    require(metadata["image_sha256"] == digest(rom) and
            metadata["d15_sha256"] == digest(d15) and
            metadata["d16_sha256"] == digest(d16),
            "C12 ROM metadata hashes differ")
    require(sum(rom) & 0xFF == 0 and sum(rom[0x1800:]) & 0xFF == 0,
            "C12 complete/resident checksums differ")
    require(rom[0x3F00:0x3F0A] == b"JUKUABI\0\x01\x05" and
            int.from_bytes(rom[0x3F0C:0x3F0E], "little") == 0x1FFF and
            rom[0x3F5F] == 0xC3,
            "C12 ABI manifest/features/vector differ")
    require(metadata.get("candidate") ==
            "network-first-abi1.5-c12-runtime-console-candidate" and
            metadata.get("gate_bytes") == 224 and
            metadata.get("boot_discovery", {}).get("frame") ==
            "4A 42 0C 01 05",
            "C12 candidate/gate/discovery metadata differs")
    require(b"JukuNet C12 ROM ABI 1.5 runtime console" in rom,
            "C12 resident identity differs")

    c11_system = (ROOT / "out/cpm-plus-juku-network-rom-c11-system.bin") \
        .read_bytes()
    c11_fastboot = \
        (ROOT / "out/cpm-plus-juku-network-rom-c11-fastboot-v16.bin") \
        .read_bytes()
    require(system != c11_system and len(system) == len(c11_system) and
            system[:8] == b"JUKURM1\x1a" and
            tuple(int.from_bytes(system[offset:offset + 2], "little")
                  for offset in (8, 10, 12)) == (0x9000, 0xBE00, 0x4600),
            "C12 ABI-aware system does not retain the C11 memory map")
    require(fastboot != c11_fastboot and fastboot[3:7] == b"JF16",
            "C12 Fastboot does not bind the ABI-aware system")
    require(digest((ROM_DIR / "juku-network-rom-abi1.4-c11.bin")
                   .read_bytes()) == C11_SHA256,
            "C12 work changed immutable C11 ROM")

    require(report["profile"] == "c12-full-a" and
            report["image_sha256"] == digest(volume),
            "C12 full-volume report differs")
    files = {item["destination"]: item for item in report["files"]}
    for destination, source in (
            ("0:CONSOLE.COM", "src/console.asm"),
            ("0:STATUS.COM", "src/status.asm"),
            ("0:DIAG.COM", "src/diag.asm and pinned juku-common diagnostics")):
        require(destination in files and
                files[destination]["provenance"]["source"] == source,
                f"C12 volume lacks {destination} provenance")

    require(manifest["build_identity"].startswith("c12-") and
            manifest["system"]["sha256"] == digest(system) and
            manifest["fast_stage"]["sha256"] == digest(fastboot) and
            manifest["rom"]["sha256"] == digest(rom),
            "C12 manifest artifact bindings differ")
    record = next((item for item in manifest["volumes"]
                   if item["file"] == VOLUME.name), None)
    require(record is not None and record["sha256"] == digest(volume) and
            record["profile"] == "c12-full-a",
            "C12 full-volume manifest binding differs")

    print(
        "C12-LAYOUT-TEST: PASS "
        f"ROM {digest(rom)}; ABI 1.5; TPA 0100h..9BFFh; "
        "C11 memory map retained; CONSOLE/STATUS/DIAG present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
