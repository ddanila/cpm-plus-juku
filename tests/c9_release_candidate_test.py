#!/usr/bin/env python3
"""Prove that the C9 simulator candidate package is reproducible and bound."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/package_release_candidate.py"
CANDIDATE = "cpm-plus-3.1-juku-c9-bounded-host-simulator"
EXPECTED_STATUS = "simulator/HDL-qualified; physical programming not authorized"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(path: Path) -> Path:
    subprocess.run(
        ["python3", str(SCRIPT), "--variant", "c9", "--output", str(path)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    return Path(str(path) + ".tar")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cpm-plus-c9-package-") as name:
        temporary = Path(name)
        first = temporary / f"one/{CANDIDATE}"
        second = temporary / f"two/{CANDIDATE}"
        first_tar = build(first)
        second_tar = build(second)
        if first_tar.read_bytes() != second_tar.read_bytes():
            raise AssertionError("C9 candidate archives are not byte-identical")

        manifest = json.loads((first / "manifest.json").read_text())
        if manifest.get("candidate") != CANDIDATE or \
                manifest.get("rom_abi") != "1.4" or \
                manifest.get("status") != EXPECTED_STATUS or \
                manifest.get("physical_programming_authorized") is not False or \
                "programmer_order" in manifest:
            raise AssertionError("C9 package identity/status differs")
        readme = (first / "README.txt").read_text()
        if "physical EPROM programming is not authorized" not in readme or \
                "Program D15" in readme:
            raise AssertionError("C9 package has unsafe bench instructions")
        for filename, record in manifest["files"].items():
            path = first / filename
            if record != {"bytes": path.stat().st_size,
                          "sha256": digest(path)}:
                raise AssertionError(f"C9 file binding differs: {filename}")

        stem = "juku-network-rom-abi1.4-c9"
        rom_metadata = json.loads((first / f"{stem}.json").read_text())
        if "physical programming not authorized" not in \
                rom_metadata.get("status", ""):
            raise AssertionError("C9 ROM metadata omits its physical boundary")
        if (first / f"{stem}-d15.bin").read_bytes() + \
                (first / f"{stem}-d16.bin").read_bytes() != \
                (first / f"{stem}.bin").read_bytes():
            raise AssertionError("C9 D15/D16 order differs")
        build_map = json.loads((first / "memory-map.json").read_text())
        if build_map["ram"].get("transient") != \
                "0100h..9BFFh (39680 bytes)" or \
                not build_map["ram"].get("adapter", "").startswith("C200h") or \
                build_map.get("tpa_gain_over_frozen_ram_bios") != 8704 or \
                build_map["rom"].get("abi_vectors", {}).get(
                    "host_services") != "FF5C":
            raise AssertionError("C9 package memory/ABI map differs")
        boot = json.loads(
            (first / "cpm-plus-juku-c9-manifest.json").read_text()
        )
        if boot.get("requirements", {}).get("rom_abi") != "1.4" or \
                boot.get("rom", {}).get("candidate") != \
                "network-first-abi1.4-c9-bounded-host-simulator":
            raise AssertionError("packaged C9 boot manifest differs")
        if not (first / "cpm-plus-juku-c9-full.img").is_file():
            raise AssertionError("C9 package omits its STATUS 1.4 volume")
        print(
            "C9-RELEASE-CANDIDATE: PASS "
            f"(reproducible tar {digest(first_tar)[:16]}, ABI 1.4 bound files)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
