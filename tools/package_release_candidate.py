#!/usr/bin/env python3
"""Build a deterministic CP/M Plus 3.1 / C5 desk release candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "cpm-plus-3.1-juku-c5-desk"
SCHEMA = "cpm-plus-juku-release-candidate-v1"


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


def build(output: Path, cosim: Path) -> tuple[Path, Path]:
    out = ROOT / "out"
    rom_dir = cosim / "spinoffs/jukuravi/network-rom"
    boot_manifest_path = out / "cpm-plus-juku-c5-manifest.json"
    boot_manifest = json.loads(boot_manifest_path.read_text())
    if boot_manifest.get("schema") != "cpm-plus-juku-boot-manifest-v1" or \
            boot_manifest.get("requirements", {}).get("rom_abi") != "1.1":
        raise ValueError("C5 boot manifest is missing or has the wrong ABI")

    rom = rom_dir / "juku-network-rom-abi1.1-c5.bin"
    d15 = rom_dir / "juku-network-rom-abi1.1-c5-d15.bin"
    d16 = rom_dir / "juku-network-rom-abi1.1-c5-d16.bin"
    rom_metadata = rom_dir / "juku-network-rom-abi1.1-c5.json"
    system = out / "cpm-plus-juku-network-rom-locale-native-system.bin"
    fast_stage = out / "cpm-plus-juku-network-rom-locale-native-fastboot-v15.bin"
    if d15.read_bytes() + d16.read_bytes() != rom.read_bytes():
        raise ValueError("D15 followed by D16 does not reproduce the C5 ROM")
    verify_record(boot_manifest.get("rom"), rom)
    verify_record(boot_manifest.get("system"), system)
    verify_record(boot_manifest.get("fast_stage"), fast_stage)

    sources = [
        rom, d15, d16, rom_metadata, system, fast_stage, boot_manifest_path,
        out / "cpm-plus-juku-native-recovery.img",
        out / "cpm-plus-juku-native-recovery.report.json",
        out / "cpm-plus-juku-full.img",
        out / "cpm-plus-juku-full.report.json",
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
            out / "cpm-plus-juku-native-recovery.img",
            out / "cpm-plus-juku-full.img",
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

        readme = temporary / "README.txt"
        readme.write_text(
            "CP/M Plus 3.1 for Juku, C5 desk release candidate\n"
            "==================================================\n\n"
            "This immutable set binds the ABI 1.1 C5 ROM, its D15/D16 halves,\n"
            "the matching locale-native CP/M Plus system and fastboot stage,\n"
            "and the published A:/B: media profiles. It passes the complete\n"
            "desk/simulator gate. It is not yet a promoted physical release.\n"
            "C5 still requires the complete CS00015 cold/warm boot, disk, host\n"
            "reconnect, and monitor-assisted display/cursor/keyboard matrix.\n\n"
            "Program D15-low from juku-network-rom-abi1.1-c5-d15.bin and\n"
            "D16-high from juku-network-rom-abi1.1-c5-d16.bin. Verify every\n"
            "file against manifest.json before bench use.\n"
        )

        files = {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(temporary.iterdir()) if path.is_file()
        }
        package_manifest = {
            "schema": SCHEMA,
            "candidate": CANDIDATE,
            "status": "desk-qualified; complete C5 physical acceptance pending",
            "boot_manifest": boot_manifest_path.name,
            "build_identity": boot_manifest["build_identity"],
            "rom_abi": "1.1",
            "target": "Juku CS00015",
            "programmer_order": [
                "juku-network-rom-abi1.1-c5-d15.bin",
                "juku-network-rom-abi1.1-c5-d16.bin",
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
    parser.add_argument(
        "--output", type=Path, default=ROOT / "out" / CANDIDATE,
    )
    parser.add_argument(
        "--cosim", type=Path, default=ROOT.parent / "8080-cosim",
    )
    args = parser.parse_args()
    output, archive = build(args.output, args.cosim.resolve())
    print(f"RELEASE-CANDIDATE: {CANDIDATE}")
    print(f"  directory: {output}")
    print(f"  archive: {archive}")
    print(f"  sha256: {sha256(archive)}")
    print("  status: desk-qualified; complete C5 physical acceptance pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
