#!/usr/bin/env python3
"""Check the generated native boot and media manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "out/cpm-plus-juku-native-manifest.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("schema") != "cpm-plus-juku-boot-manifest-v1":
        raise AssertionError("boot manifest schema differs")
    system = manifest["system"]
    system_path = ROOT / "out" / system["file"]
    if hashlib.sha256(system_path.read_bytes()).hexdigest() != \
            system["sha256"]:
        raise AssertionError("manifest system hash differs")
    if (system["load_address"], system["entry_address"],
            system["payload_bytes"]) != (0x9000, 0xBC00, 0x4600):
        raise AssertionError("manifest native memory layout differs")
    requirements = manifest["requirements"]
    if requirements["rom_abi"] != "1.0" or \
            requirements["netdisk"] != 3 or \
            requirements["disk_baud"] != 19200 or \
            "capability-query" not in requirements["features"] or \
            "bootstrap-report" not in requirements["features"]:
        raise AssertionError("manifest protocol requirements differ")
    slots = {slot["name"]: slot for slot in manifest["system_slots"]}
    if set(slots) != {"native", "c4-compatibility"} or \
            slots["native"]["system"] != manifest["system"] or \
            slots["native"]["fast_stage"] != manifest["fast_stage"] or \
            slots["c4-compatibility"]["system"]["sha256"] != \
            hashlib.sha256(
                (ROOT / "out/cpm-plus-juku-network-rom-system.bin").read_bytes()
            ).hexdigest():
        raise AssertionError("manifest system-slot set differs")
    profiles = {item["profile"]: item for item in manifest["volumes"]}
    if set(profiles) != {
        "native-recovery-a", "full-a", "museum-demo-a", "approved-apps-b",
    }:
        raise AssertionError(f"manifest volume set differs: {set(profiles)}")
    if profiles["approved-apps-b"]["drive"] != "B" or \
            profiles["approved-apps-b"]["recommended_media_mode"] != \
            "read-only" or any(
                item["recommended_media_mode"] != "snapshot"
                for name, item in profiles.items() if name != "approved-apps-b"
            ):
        raise AssertionError("manifest media policy differs")
    print("BOOT-MANIFEST: PASS (layout, protocols, hashes, volumes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
