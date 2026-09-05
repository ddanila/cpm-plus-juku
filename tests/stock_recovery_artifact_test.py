#!/usr/bin/env python3
"""Verify the reset-safe, all-9600 stock-ROM boot artifact pair."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "out/cpm-plus-juku-stock-recovery-system.bin"
FASTBOOT = ROOT / "out/cpm-plus-juku-stock-recovery-fastboot-v17.bin"
CORE = ROOT / "build/fastboot-core-v17.cim"
EXTENSION = ROOT / "build/fastboot-extension-v17.cim"
ZX0 = ROOT / "build/bin/zx0"


def crc16_ibm(data: bytes, initial: int = 0) -> int:
    crc = initial
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def main() -> int:
    system = SYSTEM.read_bytes()
    fastboot = FASTBOOT.read_bytes()
    core = CORE.read_bytes()
    extension = EXTENSION.read_bytes()

    assert len(system) == 512 + 0x4000
    assert system[:8] == b"JUKURM1\x1a"
    assert system[8:14] == bytes.fromhex("00 70 00 9c 00 40")
    body = system[512:]
    assert int.from_bytes(system[14:16], "little") == crc16_ibm(body)
    assert b"NetDisk v3, 9600" in body
    assert b"N3 19200" not in body and b"NetDisk v3, 19200" not in body
    # Check the downloaded adapter as well as the loader: CP/M has its own
    # serial handoff, and a stale count-four setup stalls physical boards.
    assert bytes.fromhex("3e 1f d3 1b 3e 08 d3 18") in body
    assert bytes.fromhex("3e 15 d3 1b 3e 04 d3 18") not in body

    assert len(core) <= 128 and len(extension) == 267
    assert core[3:7] == b"JF17"
    assert core[7] == 1
    assert core[9:11] == bytes.fromhex("5a a5")
    # Explicit PIT D57 mode-3/BCD/count-8 plus 8251 8O1 setup.
    assert bytes.fromhex("3e 1f d3 1b 3e 08 d3 18") in core
    assert bytes.fromhex("3e 5e d3 09") in core

    padded_core = fastboot[:128]
    expected_core = bytearray(core)
    expected_core[9:11] = len(extension).to_bytes(2, "little")
    expected_core[74:76] = len(extension).to_bytes(2, "little")
    assert padded_core[:len(core)] == expected_core
    assert int.from_bytes(padded_core[9:11], "little") == len(extension)
    assert padded_core[len(core):] == bytes(128 - len(core))
    bundled_extension = fastboot[128:128 + len(extension)]
    descriptor_at = 128 + len(extension)
    descriptor = fastboot[descriptor_at:descriptor_at + 8]
    compressed = fastboot[descriptor_at + 8:]
    assert descriptor[:2] == b"ZH"
    assert int.from_bytes(descriptor[2:4], "big") == crc16_ibm(body)
    assert int.from_bytes(descriptor[4:6], "big") == len(compressed)
    assert int.from_bytes(descriptor[6:8], "big") == crc16_ibm(compressed)
    # JR, protocol 17, rate 0, XOR checksum.
    ready = bytes((ord("J"), ord("R"), 17, 0,
                   ord("J") ^ ord("R") ^ 17))
    assert ready in bundled_extension

    with tempfile.TemporaryDirectory(prefix="stock-recovery-") as directory:
        rebuilt = Path(directory) / FASTBOOT.name
        subprocess.run(
            [
                "python3", str(ROOT / "tools/build_fastboot.py"),
                str(CORE), str(EXTENSION), str(SYSTEM), str(ZX0),
                str(rebuilt),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        assert rebuilt.read_bytes() == fastboot

    print(
        "STOCK-RECOVERY-ARTIFACT-TEST: PASS "
        f"(system={len(system)} sha256={hashlib.sha256(system).hexdigest()}, "
        f"JF17={len(fastboot)} sha256={hashlib.sha256(fastboot).hexdigest()})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
