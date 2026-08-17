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
    if fast_data[3:7] != b"JF15":
        raise ValueError("fast stage is not Juku fastboot v15")
    fast_stage.update({"format": "JF15", "version": 15})

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

    manifest = {
        "schema": SCHEMA,
        "build_identity": f"native-{system['sha256'][:16]}",
        "system": system,
        "fast_stage": fast_stage,
        "requirements": {
            "cpu": "Intel 8080",
            "rom_abi": "1.0",
            "fastboot": 15,
            "bootstrap_baud": 19200,
            "bootstrap_framing": "8N1",
            "netdisk": 3,
            "disk_baud": 19200,
            "disk_framing": "8O1",
            "features": ["console", "time", "status", "diagnostics"],
        },
        "volumes": sorted(volumes, key=lambda item: (
            item["drive"], item["profile"], item["file"],
        )),
    }
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"wrote {args.output} ({manifest['build_identity']}, "
        f"{len(volumes)} volumes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
