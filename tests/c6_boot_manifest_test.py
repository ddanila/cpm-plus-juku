#!/usr/bin/env python3
"""Check that C6 binds the ABI 1.2 ROM, system, services, and fallback."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COSIM = Path(os.environ.get("JUKU_COSIM_ROOT", ROOT.parent / "8080-cosim"))
MANIFEST = ROOT / "out/cpm-plus-juku-c6-manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    requirements = manifest.get("requirements", {})
    if manifest.get("schema") != "cpm-plus-juku-boot-manifest-v1" or \
            requirements.get("rom_abi") != "1.2" or \
            not {
                "bounded-console-span", "netdisk-multi", "raw-keyboard",
                "sound",
            }.issubset(requirements.get("features", [])):
        raise AssertionError("C6 manifest ABI or required services differ")
    if requirements.get("fastboot") != 16 or \
            manifest.get("fast_stage", {}).get("format") != "JF16":
        raise AssertionError("C6 manifest does not bind resident-loader v16")

    rom_dir = COSIM / "spinoffs/jukuravi/network-rom"
    rom_path = rom_dir / "juku-network-rom-abi1.2-c6.bin"
    metadata_path = rom_dir / "juku-network-rom-abi1.2-c6.json"
    rom = manifest.get("rom", {})
    if rom.get("sha256") != digest(rom_path) or \
            rom.get("metadata_sha256") != digest(metadata_path) or \
            rom.get("candidate") != "network-first-abi1.2-c6-simulator":
        raise AssertionError("C6 manifest ROM binding differs")
    metadata = json.loads(metadata_path.read_text())
    embedded = ROOT / "build/fastboot-extension-rom-v16.cim"
    core = ROOT / "build/fastboot-core-v16.cim"
    rom_data = rom_path.read_bytes()
    embedded_bytes = metadata.get("embedded_fastboot_extension_bytes")
    expected_core = bytearray(core.read_bytes().ljust(128, b"\0"))
    # The generic V16 core advertises that no executable extension is carried
    # on the wire; both ROM and bundle builders patch the assembler sentinel.
    expected_core[9:11] = b"\0\0"
    if not isinstance(embedded_bytes, int) or embedded_bytes <= 0 or \
            metadata.get("fastboot_extension_bytes") != 0 or \
            metadata.get("fastboot_protocol") != 16 or \
            metadata.get("target_ready_byte") != "C7" or \
            rom_data[0x600:0x600 + embedded_bytes] != embedded.read_bytes() or \
            rom_data[0xF00:0xF80] != bytes(expected_core):
        raise AssertionError("C6 ROM does not contain the exact V16 loader")

    system = ROOT / \
        "out/cpm-plus-juku-network-rom-extended-native-system.bin"
    fast_stage = ROOT / \
        "out/cpm-plus-juku-network-rom-extended-native-fastboot-v16.bin"
    if manifest["system"]["sha256"] != digest(system) or \
            manifest["fast_stage"]["sha256"] != digest(fast_stage):
        raise AssertionError("C6 manifest CP/M binding differs")
    c5_system = ROOT / \
        "out/cpm-plus-juku-network-rom-locale-native-system.bin"
    if manifest["system"]["sha256"] == digest(c5_system):
        raise AssertionError("C6 manifest accepted the ABI 1.1 CP/M system")

    slots = {slot["name"]: slot for slot in manifest["system_slots"]}
    if set(slots) != {"c6-native", "c4-compatibility"}:
        raise AssertionError("C6 system slots differ")
    identity = f"c6-{digest(system)[:16]}"
    if manifest.get("build_identity") != identity:
        raise AssertionError("C6 deterministic identity differs")
    c6_volumes = [
        volume for volume in manifest.get("volumes", [])
        if volume.get("profile") == "c6-recovery-a"
    ]
    if len(c6_volumes) != 1:
        raise AssertionError("C6 recovery volume is not uniquely advertised")
    print("C6-BOOT-MANIFEST: PASS (ABI 1.2 services, binding, fallback, media)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
