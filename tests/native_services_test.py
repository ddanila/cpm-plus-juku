#!/usr/bin/env python3
"""Structural and behavioral checks for the native CP/M 3 BIOS slice."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "cpm3-native-services.asm"
SESSION = ROOT / "src" / "cpm3-session.asm"
HOT_DIRECTORY = ROOT / "src" / "cpm3-hot-directory.asm"
ADAPTER = ROOT / "src" / "platform-adapter.asm"
BIOS = ROOT / "src" / "cpm3-bios.asm"
SYSTEM = ROOT / "out" / "cpm-plus-juku-network-rom-native-system.bin"
FASTBOOT = ROOT / "out" / "cpm-plus-juku-network-rom-native-fastboot-v15.bin"
SESSION_ADAPTER = ROOT / "build" / "adapter-romabi-session-native.bin"


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
        "call    NCBOOT",
        "call    NCCAPS",
        "call    NCCFG",
        "sta     NSCAPDONE",
        "call    NSCAPINIT",
        "db      'J','N','S','1'",
        "db      1,1",
        "mvi     d,01fh                  ; NSINFO feature flags",
        "mvi     a,0ffh                  ; authoritative local output is ready",
        "xra     a                       ; no separately assigned AUX source",
    )
    for marker in required:
        if marker not in source:
            raise AssertionError(f"native service marker missing: {marker}")
    session = SESSION.read_text()
    hot_directory = HOT_DIRECTORY.read_text()
    makefile = (ROOT / "Makefile").read_text()
    for marker in (
        "SESSOWNER     equ     0c5a2h",
        "SESSLEN       equ     0c5a6h",
        "SESSDATA      equ     0d3c0h",
        "extrn   NSMOVE",
        "jm      NSSESSTOOBIG",
        "sta     SESSLEN",
    ):
        if marker not in session:
            raise AssertionError(f"volatile-session marker missing: {marker}")
    for marker in (
        "SESSLEN         equ     0c5a6h",
        "HOTDATA1        equ     0c5c0h",
        "HOTDATA2        equ     0d3c0h",
        "HDSEL1:",
        "jnz     HDMISS",
    ):
        if marker not in hot_directory:
            raise AssertionError(f"session/cache arbitration missing: {marker}")
    if "-P0xd440 $(BUILD)/cpm3-session.rel" not in makefile:
        raise AssertionError(
            "volatile-session service is not linked in the session profile"
        )
    adapter = ADAPTER.read_text()
    if "mvi     a,04eh" not in adapter:
        raise AssertionError("native adapter presence marker is missing")
    if "mvi     a,050h                  ; first disk transaction confirms CP/M" \
            not in adapter:
        raise AssertionError("native adapter bootstrap confirmation is missing")
    if not re.search(r"NSFLUSH:\s+xra\s+a\s+ret", source):
        raise AssertionError("FLUSH is not explicitly successful")
    bios = BIOS.read_text()
    ccp_loader = bios.split("load$ccp:", 1)[1].split("clear$fcb:", 1)[0]
    if not re.search(
            r"mvi\s+e,1\s+mvi\s+c,44\s+call\s+bdos", ccp_loader):
        raise AssertionError(
            "CCP loader does not restore single-record BDOS reads",
        )
    wboot = (ROOT / "src" / "wboot-user.asm").read_text()
    if not re.search(
            r"mvi\s+e,1\s+mvi\s+c,32\s+call\s+0005h\s+jmp\s+0000h",
            wboot):
        raise AssertionError("WBOOT does not exercise a nonzero-user return")

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
    adapter = SESSION_ADAPTER.read_bytes()
    if len(adapter) > 0x1571:
        raise AssertionError(
            "extended adapter overlaps CCP history at D571h"
        )
    session_record = adapter[0x1440:0x14C0]
    if not any(session_record) or any(session_record[119:]):
        raise AssertionError(
            "volatile-session service does not fit D440h..D4BFh"
        )
    if not any(adapter[0x14C0:]):
        raise AssertionError("hot-directory service is missing at D4C0h")
    print(
        "CPM3-NATIVE-SERVICES: PASS "
        "(nonzero-user CCP reload, device, MULTIO, FLUSH, MOVE, TIME, USERF, "
        "status/diag publish, keyed volatile session)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
