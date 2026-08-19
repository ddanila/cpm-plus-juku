#!/usr/bin/env python3
"""Check that the C5 manifest binds only its matching ABI 1.1 artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COSIM = Path(os.environ.get("JUKU_COSIM_ROOT", ROOT.parent / "8080-cosim"))
MANIFEST = ROOT / "out/cpm-plus-juku-c5-manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    requirements = manifest.get("requirements", {})
    if manifest.get("schema") != "cpm-plus-juku-boot-manifest-v1" or \
            requirements.get("rom_abi") != "1.1" or \
            manifest.get("build_identity") != \
            "c5-86b36bd70156d10b":
        raise AssertionError("C5 manifest identity or ABI differs")

    rom_dir = COSIM / "spinoffs/jukuravi/network-rom"
    rom_path = rom_dir / "juku-network-rom-abi1.1-c5.bin"
    metadata_path = rom_dir / "juku-network-rom-abi1.1-c5.json"
    rom = manifest.get("rom", {})
    if rom.get("sha256") != digest(rom_path) or \
            rom.get("metadata_sha256") != digest(metadata_path) or \
            rom.get("candidate") != "network-first-abi1.1-cs00015-c5-desk":
        raise AssertionError("C5 manifest ROM binding differs")

    system = ROOT / "out/cpm-plus-juku-network-rom-locale-native-system.bin"
    fast_stage = \
        ROOT / "out/cpm-plus-juku-network-rom-locale-native-fastboot-v15.bin"
    if manifest["system"]["sha256"] != digest(system) or \
            manifest["fast_stage"]["sha256"] != digest(fast_stage):
        raise AssertionError("C5 manifest CP/M binding differs")
    if manifest["system"]["sha256"] == digest(
            ROOT / "out/cpm-plus-juku-network-rom-native-system.bin"):
        raise AssertionError("C5 manifest accepted the ABI 1.0 native system")

    slots = {slot["name"]: slot for slot in manifest["system_slots"]}
    if set(slots) != {"c5-native", "c4-compatibility"}:
        raise AssertionError("C5 system slots differ")
    print("C5-BOOT-MANIFEST: PASS (ROM ABI, CP/M binding, fallback, media)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
