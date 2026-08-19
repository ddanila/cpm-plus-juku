#!/usr/bin/env python3
"""Build a deterministic CP/M Plus 3.1 / Juku release candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "cpm-plus-3.1-juku-c5-desk"
SCHEMA = "cpm-plus-juku-release-candidate-v1"


VARIANTS = {
    "c5": {
        "candidate": CANDIDATE,
        "abi": "1.1",
        "rom_stem": "juku-network-rom-abi1.1-c5",
        "manifest": "cpm-plus-juku-c5-manifest.json",
        "system": "cpm-plus-juku-network-rom-locale-native-system.bin",
        "fast_stage": "cpm-plus-juku-network-rom-locale-native-fastboot-v15.bin",
        "recovery": "cpm-plus-juku-native-recovery",
        "adapter": "adapter-romabi-locale-native.bin",
        "status": "blind hardware matrix passed; display acceptance pending",
        "target": "Juku CS00015",
        "qualification": (
            "It passes the complete desk/simulator gate and the monitorless "
            "CS00015 hardware matrix.\nIt is not yet a promoted physical "
            "release: C5 still requires a\nmonitor-assisted display/cursor "
            "check and a short physical check\nof the corrected Status 1.3 "
            "and buffered Keytest 1.1 utilities."
        ),
    },
    "c6": {
        "candidate": "cpm-plus-3.1-juku-c6-simulator",
        "abi": "1.2",
        "rom_stem": "juku-network-rom-abi1.2-c6",
        "manifest": "cpm-plus-juku-c6-manifest.json",
        "system": "cpm-plus-juku-network-rom-extended-native-system.bin",
        "fast_stage": "cpm-plus-juku-network-rom-extended-native-fastboot-v16.bin",
        "recovery": "cpm-plus-juku-c6-recovery",
        "adapter": "adapter-romabi-extended-native.bin",
        "status": "simulator-qualified; physical promotion pending",
        "target": "Juku family; CS00015 is the physical promotion reference",
        "qualification": (
            "It passes deterministic ABI, boot, console, keyboard, disk, "
            "recovery,\nand long read/write/reconnect simulator gates. "
            "Physical qualification is\na later promotion step and is not "
            "claimed by this simulator candidate."
        ),
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_record(record: object, path: Path) -> None:
    if not isinstance(record, dict) or \
            record.get("file") != path.name or \
            record.get("bytes") != path.stat().st_size or \
            record.get("sha256") != sha256(path):
        raise ValueError(f"manifest differs for {path.name}")


def add_tar_entry(archive: tarfile.TarFile, path: Path, arcname: str) -> None:
    info = archive.gettarinfo(str(path), arcname)
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mode = 0o755 if path.is_dir() else 0o644
    if path.is_dir():
        archive.addfile(info)
    else:
        with path.open("rb") as source:
            archive.addfile(info, source)


def build(output: Path, cosim: Path, variant: str = "c5") -> tuple[Path, Path]:
    config = VARIANTS[variant]
    out = ROOT / "out"
    rom_dir = cosim / "spinoffs/jukuravi/network-rom"
    boot_manifest_path = out / config["manifest"]
    boot_manifest = json.loads(boot_manifest_path.read_text())
    if boot_manifest.get("schema") != "cpm-plus-juku-boot-manifest-v1" or \
            boot_manifest.get("requirements", {}).get("rom_abi") != config["abi"]:
        raise ValueError(
            f"{variant.upper()} boot manifest is missing or has the wrong ABI"
        )

    rom = rom_dir / f"{config['rom_stem']}.bin"
    d15 = rom_dir / f"{config['rom_stem']}-d15.bin"
    d16 = rom_dir / f"{config['rom_stem']}-d16.bin"
    rom_metadata = rom_dir / f"{config['rom_stem']}.json"
    rom_metadata_record = json.loads(rom_metadata.read_text())
    system = out / config["system"]
    fast_stage = out / config["fast_stage"]
    adapter = ROOT / "build" / config["adapter"]
    fallback_system = out / "cpm-plus-juku-network-rom-system.bin"
    fallback_fast_stage = out / "cpm-plus-juku-network-rom-fastboot-v15.bin"
    if d15.read_bytes() + d16.read_bytes() != rom.read_bytes():
        raise ValueError(
            f"D15 followed by D16 does not reproduce the {variant.upper()} ROM"
        )
    verify_record(boot_manifest.get("rom"), rom)
    verify_record(boot_manifest.get("system"), system)
    verify_record(boot_manifest.get("fast_stage"), fast_stage)

    sources = [
        rom, d15, d16, rom_metadata, system, fast_stage, adapter,
        fallback_system, fallback_fast_stage, boot_manifest_path,
        out / f"{config['recovery']}.img",
        out / f"{config['recovery']}.report.json",
        out / "cpm-plus-juku-full.img",
        out / "cpm-plus-juku-full.report.json",
        out / "cpm-plus-juku-dev.img",
        out / "cpm-plus-juku-dev.report.json",
        out / "cpm-plus-juku-museum-demo.img",
        out / "cpm-plus-juku-museum-demo.report.json",
        out / "cpm-plus-juku-apps.juk",
        out / "cpm-plus-juku-apps.report.json",
        ROOT / "LICENSE", ROOT / "NOTICE.md",
    ]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing release inputs: " + ", ".join(missing))

    manifest_volumes = {
        record["file"]: record for record in boot_manifest.get("volumes", [])
    }
    for image in [
            out / f"{config['recovery']}.img",
            out / "cpm-plus-juku-full.img",
            out / "cpm-plus-juku-dev.img",
            out / "cpm-plus-juku-museum-demo.img",
            out / "cpm-plus-juku-apps.juk"]:
        verify_record(manifest_volumes.get(image.name), image)

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
            prefix=f".{output.name}-", dir=output.parent) as temporary_name:
        temporary = Path(temporary_name) / output.name
        temporary.mkdir()
        for source in sources:
            shutil.copyfile(source, temporary / source.name)

        build_map_path = temporary / "memory-map.json"
        adapter_end = 0xC000 + adapter.stat().st_size - 1
        ram_map = {
            "transient": "0100h..99FFh (39168 bytes)",
            "loader": "9A00h..9CFFh",
            "bdos": "9D00h..BB9Bh",
            "scb": "BB9Ch..BBFFh",
            "bios": "BC00h..BFFFh",
            "adapter": (
                f"C000h..{adapter_end:04X}h "
                f"({adapter.stat().st_size} bytes)"
            ),
            "resident_work": "D600h..D7FFh (512 bytes)",
            "call_gate": "D620h",
            "framebuffer_helper": "D700h",
            "resident_state": "D780h",
            "framebuffer": "D800h..FD7Fh (9600 bytes, mode 3 RAM)",
        }
        if variant == "c6":
            ram_map.update({
                "netdisk_hot_directory_state": "C5A0h..C5A1h (2 bytes)",
                "netdisk_hot_directory_data": (
                    "C5C0h..C63Fh + D3C0h..D4BFh (384 bytes)"
                ),
                "netdisk_hot_directory_code": "D4C0h..D570h (177 bytes)",
                "resident_self_test_stack_guard": "D5C0h..D5FFh (reserved)",
            })
        build_map_path.write_text(json.dumps({
            "schema": "cpm-plus-juku-memory-map-v1",
            "candidate": config["candidate"],
            "rom": {
                "combined": "0000h..3FFFh (16384 bytes)",
                "boot_only": "0000h..17FFh (6144 bytes)",
                "resident_runtime": "D800h..FFFFh (10240 bytes)",
                "boot_code_bytes": rom_metadata_record["boot_code_bytes"],
                "resident_bytes": rom_metadata_record["resident_bytes"],
                "abi_vectors": rom_metadata_record["abi_vectors"],
            },
            "ram": ram_map,
            "tpa_gain_over_frozen_ram_bios": 8192,
            "bindings": {
                "rom_sha256": sha256(rom),
                "system_sha256": sha256(system),
                "fast_stage_sha256": sha256(fast_stage),
            },
        }, indent=2) + "\n")

        readme = temporary / "README.txt"
        readme.write_text(
            f"CP/M Plus 3.1 for Juku, {variant.upper()} release candidate\n"
            "========================================================\n\n"
            f"This immutable set binds the ABI {config['abi']} "
            f"{variant.upper()} ROM, its D15/D16 halves,\n"
            "the matching CP/M Plus system and fastboot stage, and the\n"
            f"published A:/B: media profiles. {config['qualification']}\n\n"
            f"Program D15-low from {config['rom_stem']}-d15.bin and\n"
            f"D16-high from {config['rom_stem']}-d16.bin. Verify every\n"
            "file against manifest.json before bench use.\n"
        )

        files = {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(temporary.iterdir()) if path.is_file()
        }
        package_manifest = {
            "schema": SCHEMA,
            "candidate": config["candidate"],
            "status": config["status"],
            "boot_manifest": boot_manifest_path.name,
            "build_map": build_map_path.name,
            "build_identity": boot_manifest["build_identity"],
            "rom_abi": config["abi"],
            "target": config["target"],
            "programmer_order": [
                f"{config['rom_stem']}-d15.bin",
                f"{config['rom_stem']}-d16.bin",
            ],
            "files": files,
        }
        (temporary / "manifest.json").write_text(
            json.dumps(package_manifest, indent=2) + "\n"
        )

        if output.exists():
            shutil.rmtree(output)
        temporary.replace(output)

    archive_path = Path(str(output) + ".tar")
    temporary_archive = Path(str(archive_path) + ".tmp")
    with tarfile.open(temporary_archive, "w", format=tarfile.PAX_FORMAT) as archive:
        add_tar_entry(archive, output, output.name)
        for path in sorted(output.iterdir()):
            add_tar_entry(archive, path, f"{output.name}/{path.name}")
    temporary_archive.replace(archive_path)
    checksum_path = Path(str(archive_path) + ".sha256")
    checksum_path.write_text(f"{sha256(archive_path)}  {archive_path.name}\n")
    return output, archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="c5")
    parser.add_argument(
        "--output", type=Path,
    )
    parser.add_argument(
        "--cosim", type=Path,
        default=Path(os.environ.get(
            "JUKU_COSIM_ROOT", ROOT.parent / "8080-cosim",
        )),
    )
    args = parser.parse_args()
    config = VARIANTS[args.variant]
    output_path = args.output or ROOT / "out" / config["candidate"]
    output, archive = build(output_path, args.cosim.resolve(), args.variant)
    print(f"RELEASE-CANDIDATE: {config['candidate']}")
    print(f"  directory: {output}")
    print(f"  archive: {archive}")
    print(f"  sha256: {sha256(archive)}")
    print(f"  status: {config['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
