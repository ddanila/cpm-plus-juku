#!/usr/bin/env python3
"""Prove that the C6 simulator-candidate directory and tar are reproducible."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/package_release_candidate.py"
CANDIDATE = "cpm-plus-3.1-juku-c6-simulator"
EXPECTED_STATUS = "simulator-qualified; physical promotion pending"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(path: Path) -> Path:
    subprocess.run(
        ["python3", str(SCRIPT), "--variant", "c6", "--output", str(path)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    archive = Path(str(path) + ".tar")
    if archive.name != f"{CANDIDATE}.tar":
        raise AssertionError("C6 release archive name differs")
    return archive


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cpm-plus-c6-package-") as name:
        temporary = Path(name)
        first = temporary / f"one/{CANDIDATE}"
        second = temporary / f"two/{CANDIDATE}"
        first_tar = build(first)
        second_tar = build(second)
        if first_tar.read_bytes() != second_tar.read_bytes():
            raise AssertionError("C6 release archives are not byte-identical")

        manifest = json.loads((first / "manifest.json").read_text())
        if manifest.get("schema") != "cpm-plus-juku-release-candidate-v1" or \
                manifest.get("candidate") != CANDIDATE or \
                manifest.get("rom_abi") != "1.2" or \
                manifest.get("status") != EXPECTED_STATUS:
            raise AssertionError("C6 release status or ABI differs")
        for file_name, record in manifest["files"].items():
            path = first / file_name
            if record != {"bytes": path.stat().st_size, "sha256": digest(path)}:
                raise AssertionError(f"C6 release file binding differs: {file_name}")
        memory_map = json.loads((first / manifest["build_map"]).read_text())
        if memory_map["ram"].get("transient") != \
                "0100h..99FFh (39168 bytes)" or \
                memory_map.get("tpa_gain_over_frozen_ram_bios") != 8192 or \
                memory_map["rom"].get("abi_vectors", {}).get("keyboard_raw") != \
                "FF59":
            raise AssertionError("C6 release memory/ABI map differs")

        boot_manifest = json.loads(
            (first / "cpm-plus-juku-c6-manifest.json").read_text()
        )
        if boot_manifest["requirements"].get("rom_abi") != "1.2":
            raise AssertionError("packaged C6 boot manifest does not require ABI 1.2")
        services = set(boot_manifest["requirements"].get("features", []))
        required = {
            "bounded-console-span", "netdisk-multi", "raw-keyboard", "sound",
        }
        if not required.issubset(services):
            raise AssertionError("packaged C6 manifest omits ABI 1.2 services")
        for slot in boot_manifest["system_slots"]:
            for artifact_name in ("system", "fast_stage"):
                record = slot[artifact_name]
                path = first / record["file"]
                if not path.is_file() or record["sha256"] != digest(path):
                    raise AssertionError(
                        f"packaged slot differs: {slot['name']} {artifact_name}"
                    )
        stem = "juku-network-rom-abi1.2-c6"
        d15 = first / f"{stem}-d15.bin"
        d16 = first / f"{stem}-d16.bin"
        combined = first / f"{stem}.bin"
        if d15.read_bytes() + d16.read_bytes() != combined.read_bytes():
            raise AssertionError("packaged C6 EPROM halves differ from combined ROM")
        print(
            "C6-RELEASE-CANDIDATE: PASS "
            f"(reproducible tar {digest(first_tar)[:16]}, ABI 1.2 bound files)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
