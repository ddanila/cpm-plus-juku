#!/usr/bin/env python3
"""Generate the host-visible native CP/M Plus boot/media manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "cpm-plus-juku-boot-manifest-v1"
SYSTEM_MAGIC = b"JUKURM1\x1a"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def crc16_ibm(data: bytes) -> int:
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def image_record(path: Path) -> tuple[dict[str, object], bytes]:
    data = path.read_bytes()
    return {
        "file": path.name,
        "bytes": len(data),
        "sha256": digest(data),
    }, data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", type=Path, required=True)
    parser.add_argument("--fast-stage", type=Path, required=True)
    parser.add_argument("--fallback-system", type=Path, required=True)
    parser.add_argument("--fallback-fast-stage", type=Path, required=True)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--rom-metadata", type=Path)
    parser.add_argument("--rom-abi", default="1.0")
    parser.add_argument("--identity-prefix", default="native")
    parser.add_argument("--primary-slot-name", default="native")
    parser.add_argument(
        "--volume", action="append", nargs=2, type=Path,
        metavar=("IMAGE", "REPORT"), default=[],
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    system, system_data = image_record(args.system)
    if system_data[:8] != SYSTEM_MAGIC or len(system_data) < 512:
        raise ValueError("system is not a JUKURM1 container")
    load = int.from_bytes(system_data[8:10], "little")
    entry = int.from_bytes(system_data[10:12], "little")
    length = int.from_bytes(system_data[12:14], "little")
    expected_crc = int.from_bytes(system_data[14:16], "little")
    if len(system_data) != 512 + length or \
            crc16_ibm(system_data[512:]) != expected_crc:
        raise ValueError("system length or CRC differs from its header")
    system.update({
        "format": "JUKURM1",
        "load_address": load,
        "entry_address": entry,
        "payload_bytes": length,
        "payload_crc16_ibm": f"{expected_crc:04X}",
    })

    fast_stage, fast_data = image_record(args.fast_stage)
    fast_version = {b"JF15": 15, b"JF16": 16}.get(fast_data[3:7])
    if fast_version is None:
        raise ValueError("fast stage is not Juku fastboot v15/v16")
    fast_stage.update({"format": f"JF{fast_version}",
                       "version": fast_version})
    fallback_system, fallback_system_data = image_record(args.fallback_system)
    if fallback_system_data[:8] != SYSTEM_MAGIC or \
            len(fallback_system_data) < 512:
        raise ValueError("fallback system is not a JUKURM1 container")
    fallback_length = int.from_bytes(fallback_system_data[12:14], "little")
    fallback_crc = int.from_bytes(fallback_system_data[14:16], "little")
    if len(fallback_system_data) != 512 + fallback_length or \
            crc16_ibm(fallback_system_data[512:]) != fallback_crc:
        raise ValueError("fallback system length or CRC differs from its header")
    fallback_system.update({
        "format": "JUKURM1",
        "load_address": int.from_bytes(fallback_system_data[8:10], "little"),
        "entry_address": int.from_bytes(fallback_system_data[10:12], "little"),
        "payload_bytes": fallback_length,
        "payload_crc16_ibm": f"{fallback_crc:04X}",
    })
    fallback_fast_stage, fallback_fast_data = image_record(
        args.fallback_fast_stage,
    )
    if fallback_fast_data[3:7] != b"JF15":
        raise ValueError("fallback fast stage is not Juku fastboot v15")
    fallback_fast_stage.update({"format": "JF15", "version": 15})

    volumes: list[dict[str, object]] = []
    for image_path, report_path in args.volume:
        image, image_data = image_record(image_path)
        report = json.loads(report_path.read_text())
        if report.get("schema") != "cpm-plus-juku-volume-report-v1" or \
                report.get("image_sha256") != image["sha256"] or \
                report.get("image_bytes") != len(image_data):
            raise ValueError(f"volume report differs for {image_path}")
        drive = "B" if report.get("output_layout") == \
            "juku-cylinder-head" else "A"
        image.update({
            "drive": drive,
            "profile": report["profile"],
            "geometry": report["geometry"],
            "layout": report["output_layout"],
            "recommended_media_mode": "read-only" if drive == "B" \
                else "snapshot",
        })
        volumes.append(image)

    if (args.rom is None) != (args.rom_metadata is None):
        raise ValueError("ROM image and metadata must be supplied together")
    rom = None
    if args.rom is not None and args.rom_metadata is not None:
        rom, rom_data = image_record(args.rom)
        rom_metadata_data = args.rom_metadata.read_bytes()
        rom_metadata = json.loads(rom_metadata_data)
        if rom_metadata.get("schema") != "juku-network-rom-abi1-v1" or \
                rom_metadata.get("image_bytes") != len(rom_data) or \
                rom_metadata.get("image_sha256") != rom["sha256"]:
            raise ValueError("ROM metadata differs from the ROM image")
        abi = rom_metadata.get("abi")
        metadata_abi = None if not isinstance(abi, dict) else \
            f"{abi.get('major')}.{abi.get('minor')}"
        if metadata_abi != args.rom_abi:
            raise ValueError("ROM metadata ABI differs from requested ABI")
        rom.update({
            "metadata_file": args.rom_metadata.name,
            "metadata_bytes": len(rom_metadata_data),
            "metadata_sha256": digest(rom_metadata_data),
            "abi": args.rom_abi,
            "candidate": rom_metadata.get("candidate"),
            "status": rom_metadata.get("status"),
        })

    manifest = {
        "schema": SCHEMA,
        "build_identity": f"{args.identity_prefix}-{system['sha256'][:16]}",
        "system": system,
        "fast_stage": fast_stage,
        "system_slots": [
            {
                "name": args.primary_slot_name,
                "system": system,
                "fast_stage": fast_stage,
            },
            {
                "name": "c4-compatibility",
                "system": fallback_system,
                "fast_stage": fallback_fast_stage,
            },
        ],
        "requirements": {
            "cpu": "Intel 8080",
            "rom_abi": args.rom_abi,
            "fastboot": fast_version,
            "bootstrap_baud": 19200,
            "bootstrap_framing": "8N1",
            "netdisk": 3,
            "disk_baud": 19200,
            "disk_framing": "8O1",
            "features": [
                "console", "time", "status", "diagnostics",
                "capability-query", "bootstrap-report",
            ],
        },
        "volumes": sorted(volumes, key=lambda item: (
            item["drive"], item["profile"], item["file"],
        )),
    }
    if rom is not None:
        manifest["rom"] = rom
        if args.rom_abi == "1.2":
            required = {
                "bounded-console-span", "netdisk-multi", "raw-keyboard",
                "sound",
            }
            services = rom_metadata.get("resident_services", [])
            if not isinstance(services, list) or not required.issubset(services):
                raise ValueError("ABI 1.2 ROM lacks required resident services")
            manifest["requirements"]["features"].extend(sorted(required))
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"wrote {args.output} ({manifest['build_identity']}, "
        f"{len(volumes)} volumes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
