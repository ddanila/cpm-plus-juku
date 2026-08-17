#!/usr/bin/env python3
"""Structural and behavioral checks for the native CP/M 3 BIOS slice."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "cpm3-native-services.asm"
ADAPTER = ROOT / "src" / "platform-adapter.asm"
SYSTEM = ROOT / "out" / "cpm-plus-juku-network-rom-native-system.bin"
FASTBOOT = ROOT / "out" / "cpm-plus-juku-network-rom-native-fastboot-v15.bin"


def memmove_fixture(data: bytes, source: int, destination: int,
                    count: int) -> bytes:
    result = bytearray(data)
    result[destination:destination + count] = \
        bytes(result[source:source + count])
    return bytes(result)


def main() -> int:
    source = SOURCE.read_text()
    required = (
        "db      'JUKU  ',3,0",
        "sta     NSLASTMULTIO",
        "NSMOVEBACK1:",
        "NSMOVEFORWARD:",
        "call    NCTIME",
        "call    NCPUBLISH",
        "call    NCDIAG",
        "call    NCCAPS",
        "call    NCCFG",
        "sta     NSCAPDONE",
        "call    NSCAPINIT",
        "db      'J','N','S','1'",
        "mvi     a,0ffh                  ; authoritative local output is ready",
        "xra     a                       ; no separately assigned AUX source",
    )
    for marker in required:
        if marker not in source:
            raise AssertionError(f"native service marker missing: {marker}")
    if "mvi     a,04eh" not in ADAPTER.read_text():
        raise AssertionError("native adapter presence marker is missing")
    if not re.search(r"NSFLUSH:\s+xra\s+a\s+ret", source):
        raise AssertionError("FLUSH is not explicitly successful")

    fixture = bytes(range(32))
    cases = ((0, 8, 8), (8, 0, 8), (0, 4, 16), (4, 0, 16),
             (5, 5, 12), (0, 31, 0))
    for src, dst, count in cases:
        actual = memmove_fixture(fixture, src, dst, count)
        expected = bytearray(fixture)
        temporary = fixture[src:src + count]
        expected[dst:dst + count] = temporary
        if actual != bytes(expected):
            raise AssertionError(f"MOVE oracle failed {src=} {dst=} {count=}")

    if SYSTEM.stat().st_size != 0x4800:  # 512-byte JUKURM1 header + 4600h RAM
        raise AssertionError("native system container changed size")
    if FASTBOOT.read_bytes()[4:7] != b"F15":
        raise AssertionError("native V15 bootstrap header is missing")
    print(
        "CPM3-NATIVE-SERVICES: PASS "
        "(device, MULTIO, FLUSH, MOVE, TIME, USERF, status/diag publish)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
