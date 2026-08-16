#!/usr/bin/env python3
"""Package one deterministic network-first ROM bench candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


CANDIDATE = "network-first-abi1-cs00015-c1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cosim", type=Path, default=Path("../8080-cosim"))
    parser.add_argument("--output", type=Path,
                        default=Path("out") / CANDIDATE)
    args = parser.parse_args()

    rom_dir = args.cosim.resolve() / "spinoffs/jukuravi/network-rom"
    rom_metadata = json.loads(
        (rom_dir / "juku-network-rom-abi1.json").read_text()
    )
    if rom_metadata.get("candidate") != CANDIDATE or \
            rom_metadata.get("status") != \
            "CS00015 bench candidate; physical qualification pending":
        raise SystemExit("ROM metadata is not the matching C1 bench release")

    inputs = {
        "combined-rom.bin": rom_dir / "juku-network-rom-abi1.bin",
        "D15-low-8K.bin": rom_dir / "juku-network-rom-abi1-d15.bin",
        "D16-high-8K.bin": rom_dir / "juku-network-rom-abi1-d16.bin",
        "rom-metadata.json": rom_dir / "juku-network-rom-abi1.json",
        "cpm-plus-system.bin":
            Path("out/cpm-plus-juku-network-rom-system.bin"),
        "fastboot-v15.bin":
            Path("out/cpm-plus-juku-network-rom-fastboot-v15.bin"),
        "network-disk.img": Path("out/cpm-plus-juku.img"),
    }
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing candidate inputs: " + ", ".join(missing))

    combined = inputs["combined-rom.bin"].read_bytes()
    d15 = inputs["D15-low-8K.bin"].read_bytes()
    d16 = inputs["D16-high-8K.bin"].read_bytes()
    if len(combined) != 16384 or len(d15) != 8192 or len(d16) != 8192:
        raise SystemExit("candidate ROM geometry differs from 16K / 8K / 8K")
    if d15 + d16 != combined:
        raise SystemExit("D15 followed by D16 does not reproduce combined ROM")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict[str, object]] = {}
    for name, source in inputs.items():
        destination = output / name
        shutil.copyfile(source, destination)
        files[name] = {
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        }

    manifest = {
        "schema": "juku-network-first-bench-candidate-v1",
        "candidate": CANDIDATE,
        "status": "physical qualification pending",
        "target": "Juku CS00015",
        "programmer_order": ["D15-low-8K.bin", "D16-high-8K.bin"],
        "serial": {
            "bootstrap": "19200 8N1 direct V15",
            "network_disk": "19200 8O1 NetDisk v3",
        },
        "memory_map": {
            "transient": "0100h..99FFh (39168 bytes)",
            "loader": "9A00h..9CFFh",
            "bdos": "9D00h..BBFFh",
            "bios": "BC00h..BFFFh",
            "ram_adapter": "C000h..C38Fh",
            "resident_rom": "D800h..FFFFh",
            "abi": "FF00h, JUKUABI 1.0",
        },
        "host_options": [
            "--network-rom", "--disk-baud", "19200",
            "--disk-protocol", "3", "--writable", "--timeout", "86400",
        ],
        "qualification": {
            "simulator": "passed",
            "physical": "pending",
        },
        "files": files,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(f"BENCH-CANDIDATE: {CANDIDATE}")
    for name, details in files.items():
        print(f"  {details['sha256']}  {name}")
    print(f"  manifest: {output / 'manifest.json'}")
    print("  status: physical qualification pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
