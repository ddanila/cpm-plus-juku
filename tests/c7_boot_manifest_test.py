#!/usr/bin/env python3
"""Check the exact C7 ROM/CP/M/media binding and immutable C6 boundary."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COSIM = Path(os.environ.get("JUKU_COSIM_ROOT", ROOT.parent / "8080-cosim"))
MANIFEST = ROOT / "out/cpm-plus-juku-c7-manifest.json"
C6_SHA256 = "0487d5150f9b662a193b3f031aadd90002ee232477d355d3877a757a247c2f09"
C7_SHA256 = "a05c74d948d9f01c5a89dc3ea69bfeb4fdf9ac48b3e37845d1edbf03e6e203b8"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    requirements = manifest.get("requirements", {})
    if manifest.get("schema") != "cpm-plus-juku-boot-manifest-v1" or \
            requirements.get("rom_abi") != "1.2" or \
            requirements.get("fastboot") != 16 or \
            not {"raw-keyboard", "netdisk-multi", "sound"}.issubset(
                requirements.get("features", []),
            ):
        raise AssertionError("C7 manifest ABI, V16, or services differ")

    rom_dir = COSIM / "spinoffs/jukuravi/network-rom"
    c6 = rom_dir / "juku-network-rom-abi1.2-c6.bin"
    c7 = rom_dir / "juku-network-rom-abi1.2-c7.bin"
    metadata_path = rom_dir / "juku-network-rom-abi1.2-c7.json"
    rom = manifest.get("rom", {})
    if digest(c6) != C6_SHA256 or digest(c7) != C7_SHA256 or \
            rom.get("sha256") != C7_SHA256 or \
            rom.get("metadata_sha256") != digest(metadata_path) or \
            rom.get("candidate") != \
            "network-first-abi1.2-c7-modified-raw-simulator":
        raise AssertionError("C7 binding or immutable C6 boundary differs")

    system = ROOT / "out/cpm-plus-juku-network-rom-extended-native-system.bin"
    fast_stage = ROOT / \
        "out/cpm-plus-juku-network-rom-extended-native-fastboot-v16.bin"
    if manifest["system"]["sha256"] != digest(system) or \
            manifest["fast_stage"]["sha256"] != digest(fast_stage) or \
            manifest.get("build_identity") != f"c7-{digest(system)[:16]}":
        raise AssertionError("C7 CP/M/V16 identity differs")
    slots = {slot["name"] for slot in manifest["system_slots"]}
    if slots != {"c7-native", "c4-compatibility"}:
        raise AssertionError("C7 system slots differ")
    recovery = [volume for volume in manifest.get("volumes", [])
                if volume.get("profile") == "c6-recovery-a"]
    if len(recovery) != 1:
        raise AssertionError("C7 has no unique raw-key recovery volume")
    print("C7-BOOT-MANIFEST: PASS (exact C7, immutable C6, V16 and media)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
