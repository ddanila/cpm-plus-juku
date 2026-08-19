#!/usr/bin/env python3
"""Independent transcript and framebuffer oracle for PANEL.COM."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMON_TOOLS = ROOT / "third_party" / "juku-common" / "tools"
sys.path.insert(0, str(COMMON_TOOLS))

from creep_console_oracle import load_reference, render_transcript  # noqa: E402

READY = b"PANEL READY"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def hexbyte(value: int) -> bytes:
    require(0 <= value <= 0xFF, f"byte outside range: {value}")
    return f"{value:02X}".encode("ascii")


def transcript(*, s21: int = 0x07, abi_major: int = 1,
               abi_minor: int = 2, boot_stage: int = 0x50,
               boot_retries: int = 0, reconnects: int = 0,
               disk_status: int = 0) -> bytes:
    """Return the exact 80x24 byte stream emitted while PANEL waits."""

    locale = (s21 >> 3) & 3
    if locale == 1:
        top_left = top_right = bottom_left = ord("+")
        horizontal = ord("-")
        vertical = ord("|")
    else:
        top_left, top_right, bottom_left = 0xDA, 0xBF, 0xC0
        horizontal, vertical = 0xC4, 0xB3

    def interior(content: bytes) -> bytes:
        require(len(content) <= 78, f"PANEL row is too long: {content!r}")
        return bytes((vertical,)) + content.ljust(78) + bytes((vertical,))

    separator = interior(b"")
    locales = (
        b" Locale: English        local I/O authoritative",
        b" Locale: Estonian       local I/O authoritative",
        b" Locale: Russian CP866  local I/O authoritative",
        b" Locale: English/remap  local I/O authoritative",
    )
    rows = [
        bytes((top_left,)) + bytes((horizontal,)) * 78
        + bytes((top_right,)),
        interior(b" Juku Control Panel 1.0"),
        separator,
        interior(b" System"),
        interior(b" CP/M Plus 3.1          CPU: strict Intel 8080"),
        interior(b" TPA: 0100h-99FFh       39168 bytes"),
        interior(
            b" ROM ABI: " + hexbyte(abi_major) + b"."
            + hexbyte(abi_minor) + b"             network-first C6"
        ),
        separator,
        interior(b" Console"),
        interior(b" S21: " + hexbyte(s21) + b"h               mode: 80x24"),
        interior(locales[locale]),
        interior(b""),
        separator,
        interior(b" Network"),
        interior(b" NetDisk v3             serial: 19200 8N1"),
        interior(
            b" Boot stage: " + hexbyte(boot_stage)
            + b"h        retries: " + hexbyte(boot_retries) + b"h"
        ),
        interior(
            b" Reconnects: " + hexbyte(reconnects)
            + b"h         disk status: " + hexbyte(disk_status) + b"h"
        ),
        interior(b""),
        separator,
        interior(b" Safety"),
        interior(b" Writes: synchronous    recovery: C4/C5 retained"),
        interior(b" Press any key to return to CP/M"),
        interior(b""),
    ]
    require(len(rows) == 23 and all(len(row) == 80 for row in rows),
            "PANEL complete-row count differs")
    bottom = bytes((bottom_left,)) + bytes((horizontal,)) * 67 + READY
    require(len(bottom) == 79, "PANEL cursor cell is not reserved")
    return b"\x1bL" + b"".join(rows) + bottom


def framebuffer(*, cursor: bool, **values: int) -> bytes:
    locale = (values.get("s21", 0x07) >> 3) & 3
    return render_transcript(
        transcript(**values), mode=3, locale=locale, cursor=cursor,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    glyphs = load_reference()
    for code in (0xB3, 0xBF, 0xC0, 0xC4, 0xDA):
        require(code in glyphs, f"PANEL border glyph {code:02X} is absent")
    hidden = framebuffer(cursor=False)
    visible = framebuffer(cursor=True)
    require(len(hidden) == len(visible) == 9600,
            "PANEL framebuffer size differs")
    require(hidden != visible, "PANEL cursor phases are identical")
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "panel-hidden.bin").write_bytes(hidden)
        (args.output / "panel-visible.bin").write_bytes(visible)
    print(
        "PANEL-ORACLE: PASS "
        f"{hashlib.sha256(hidden).hexdigest()[:12]}/"
        f"{hashlib.sha256(visible).hexdigest()[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
