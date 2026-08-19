#!/usr/bin/env python3
"""Build an exact-length ZX0 Fast stage v9 and later bundle."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

CORE_SIZE = 128
SYSTEM_PREFIX = 512
SYSTEM_SIZE = 6656
COMPRESSED_LIMIT = 0x1800
V15_COMPRESSED_LIMIT = 0x2800
VERSIONS = {
    b"JFV9": (9, b"Z9"),
    b"JF10": (10, b"ZA"),
    b"JF11": (11, b"ZB"),
    b"JF12": (12, b"ZC"),
    b"JF13": (13, b"ZD"),
    b"JF14": (14, b"ZE"),
    b"JF15": (15, b"ZF"),
    b"JF16": (16, b"ZG"),
}
EXTENSION_LENGTH_SENTINEL = bytes.fromhex("01 5A A5")
LENGTH_SENTINEL = bytes.fromhex("21 5A A5 22")
CRC_HIGH_SENTINEL = bytes.fromhex("FE A5 C2")
CRC_LOW_SENTINEL = bytes.fromhex("00 FE 5A C2")
BUFFERED_LENGTH_SENTINEL = bytes.fromhex("01 5A A5")
BUFFERED_CRC_HIGH_SENTINEL = bytes.fromhex("3E A5 BA")
BUFFERED_CRC_LOW_SENTINEL = bytes.fromhex("3E 5A BB")


def crc16_ibm(data: bytes, initial: int = 0) -> int:
    crc = initial
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def patch_unique(image: bytearray, sentinel: bytes, offset: int,
                 replacement: bytes, name: str) -> None:
    if image.count(sentinel) != 1:
        raise ValueError(
            f"fastboot {name} sentinel is missing or ambiguous"
        )
    start = image.index(sentinel) + offset
    image[start:start + len(replacement)] = replacement


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("core", type=Path)
    parser.add_argument("extension", type=Path)
    parser.add_argument("system", type=Path)
    parser.add_argument("compressor", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    core = bytearray(args.core.read_bytes())
    extension = bytearray(args.extension.read_bytes())
    system_image = args.system.read_bytes()
    magic = bytes(core[3:7])
    if magic not in VERSIONS or core[7:11] != b"\x01\x00\x5a\xa5":
        raise ValueError("exact fastboot core metadata is missing or malformed")
    version, payload_magic = VERSIONS[magic]
    if len(core) > CORE_SIZE:
        raise ValueError(
            f"fastboot v{version} core is {len(core)} bytes, limit {CORE_SIZE}"
        )
    if not 256 <= len(extension) <= 0xFFFF:
        raise ValueError(
            f"fastboot v{version} extension has invalid size {len(extension)}"
        )
    if version in (15, 16):
        if not system_image.startswith(b"JUKURM1\x1a"):
            raise ValueError(
                f"fastboot v{version} requires a JUKURM1 system image"
            )
        if system_image[8:12] not in (
            bytes.fromhex("00 b0 00 c6"),
            bytes.fromhex("00 70 00 9c"),
            bytes.fromhex("00 90 00 bc"),
            bytes.fromhex("00 90 00 be"),
        ):
            raise ValueError(
                f"fastboot v{version} requires a supported Juku RAM layout"
            )
        system_size = int.from_bytes(system_image[12:14], "little")
        if len(system_image) != SYSTEM_PREFIX + system_size:
            raise ValueError(
                f"fastboot v{version} JUKURM1 length is inconsistent"
            )
        system = system_image[SYSTEM_PREFIX:]
    else:
        if len(system_image) != 10240 or \
                system_image[:SYSTEM_PREFIX] != bytes((0xE5,)) * SYSTEM_PREFIX:
            raise ValueError(
                f"fastboot v{version} requires a 10 KiB JUKUSYS system image"
            )
        system = system_image[SYSTEM_PREFIX:SYSTEM_PREFIX + SYSTEM_SIZE]

    extension_size = 0 if version == 16 else len(extension)
    core[9:11] = extension_size.to_bytes(2, "little")
    if version != 16:
        patch_unique(
            core, EXTENSION_LENGTH_SENTINEL, 1,
            extension_size.to_bytes(2, "little"), "extension length",
        )

    with tempfile.TemporaryDirectory(
        prefix=f"juku-fastboot-v{version}-"
    ) as directory:
        raw_path = Path(directory) / "system.bin"
        compressed_path = Path(directory) / "system.zx0"
        raw_path.write_bytes(system)
        subprocess.run(
            [str(args.compressor), "-f", "-c", str(raw_path),
             str(compressed_path)],
            check=True,
        )
        compressed = compressed_path.read_bytes()

    compressed_limit = V15_COMPRESSED_LIMIT \
        if version in (15, 16) else COMPRESSED_LIMIT
    if len(compressed) < 0x100 or len(compressed) >= compressed_limit:
        raise ValueError(
            f"fastboot v{version} compressed system is {len(compressed)} bytes, "
            f"required range 256..{compressed_limit - 1}"
        )
    compressed_crc = crc16_ibm(compressed)
    if version != 16:
        length_sentinel = BUFFERED_LENGTH_SENTINEL \
            if version in (14, 15) else LENGTH_SENTINEL
        crc_high_sentinel = BUFFERED_CRC_HIGH_SENTINEL \
            if version in (14, 15) else CRC_HIGH_SENTINEL
        crc_low_sentinel = BUFFERED_CRC_LOW_SENTINEL \
            if version in (14, 15) else CRC_LOW_SENTINEL
        patch_unique(
            extension, length_sentinel, 1,
            len(compressed).to_bytes(2, "little"), "length",
        )
        patch_unique(
            extension, crc_high_sentinel, 1,
            bytes((compressed_crc >> 8,)), "CRC high",
        )
        patch_unique(
            extension, crc_low_sentinel, 1 if version in (14, 15) else 2,
            bytes((compressed_crc & 0xFF,)), "CRC low",
        )
    system_crc = crc16_ibm(system)
    descriptor = (
        payload_magic
        + system_crc.to_bytes(2, "big")
        + len(compressed).to_bytes(2, "big")
        + compressed_crc.to_bytes(2, "big")
    )
    bundle = bytes(core).ljust(CORE_SIZE, b"\0") + \
        (b"" if version == 16 else bytes(extension)) + descriptor + compressed
    args.output.write_bytes(bundle)
    extension_detail = (
        f"embedded-extension={len(extension)} bytes, wire-extension=0, "
        if version == 16 else f"extension={len(extension)} exact bytes, "
    )
    print(
        f"Fastboot v{version} bundle: core={len(core)}/{CORE_SIZE}, "
        f"{extension_detail}"
        f"system={len(system)}->{len(compressed)}, "
        f"compressed CRC16/IBM={compressed_crc:04X}, "
        f"system CRC16/IBM={system_crc:04X}, total={len(bundle)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
