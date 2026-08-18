#!/usr/bin/env python3
"""Independent screen transcript and framebuffer oracle for VIDTEST.COM."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMON_TOOLS = ROOT / "third_party" / "juku-common" / "tools"
sys.path.insert(0, str(COMMON_TOOLS))

from creep_console_oracle import render_transcript  # noqa: E402

GEOMETRIES = ((40, 24), (53, 24), (64, 20), (80, 24))
MODE_LINES = (
    b"Mode 0: 40x24, 8x10 cells",
    b"Mode 1: 53x24, 6x10 cells",
    b"Mode 2: 64x20, 6x10 cells",
    b"Mode 3: 80x24, 5x8 cells",
)
LOCALE_LINES = (
    b"Locale 0: English + CP437 UI",
    b"Locale 1: Estonian ISO-8859-1",
    b"Locale 2: Russian CP866",
    b"Locale 3: English/remap fallback",
)
LOCALE_SAMPLES = (
    b"Locale sample: Juku 2026",
    b"Locale: \xC4\xD5\xD6\xDC\xE4\xF5\xF6\xFC",
    b"Locale: \x80\x81\x82\x83\x84\x85\x86\x87",
    b"Locale sample: Juku 2026",
)
ASCII_UPPER = b"ASCII: ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ASCII_LOWER = b"Digits: 0123456789  lower: abcxyz"
GRAPHICS_TEXT = b"Boundary: ASCII fallback in wide mode"
GRAPHICS_CP437 = b"CP437: \xDA\xC4\xC2\xC4\xBF \xB3\xC5\xB3 \xC0\xC4\xC1\xC4\xD9"
READY = b"VIDTEST READY"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def transcript(mode: int, locale: int) -> bytes:
    """Return the documented bytes emitted after VIDTEST clears the screen."""
    require(mode in range(4), f"invalid video mode: {mode}")
    require(locale in range(4), f"invalid locale: {locale}")
    columns, rows = GEOMETRIES[mode]
    if mode == 3:
        top_left, top_right = 0xDA, 0xBF
        bottom_left, horizontal, vertical = 0xC0, 0xC4, 0xB3
        graphics = GRAPHICS_CP437
    else:
        top_left = top_right = bottom_left = ord("+")
        horizontal, vertical = ord("-"), ord("|")
        graphics = GRAPHICS_TEXT

    output = bytearray(b"\x1bL")
    output.extend(bytes((top_left,)))
    output.extend(bytes((horizontal,)) * (columns - 2))
    output.extend(bytes((top_right,)))

    named = (
        b"Juku Vidtest 1.0",
        MODE_LINES[mode],
        LOCALE_LINES[locale],
        ASCII_UPPER,
        ASCII_LOWER,
        LOCALE_SAMPLES[locale],
        graphics,
    )
    for content in named + (b"",) * (rows - 9):
        require(len(content) <= columns - 2,
                f"VIDTEST row exceeds mode {mode}: {content!r}")
        output.extend(bytes((vertical,)))
        output.extend(content)
        output.extend(b" " * (columns - 2 - len(content)))
        output.extend(bytes((vertical,)))

    output.extend(bytes((bottom_left,)))
    output.extend(bytes((horizontal,)) * (columns - 2 - len(READY)))
    output.extend(READY)
    require(len(output) - 2 == rows * columns - 1,
            "VIDTEST transcript does not leave exactly one cursor cell")
    return bytes(output)


def framebuffer(mode: int, locale: int, *, cursor: bool) -> bytes:
    return render_transcript(
        transcript(mode, locale), mode=mode, locale=locale, cursor=cursor,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=int)
    parser.add_argument("--locale", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    selected_modes = range(4) if args.mode is None else (args.mode,)
    selected_locales = range(4) if args.locale is None else (args.locale,)
    records = []
    for mode in selected_modes:
        for locale in selected_locales:
            hidden = framebuffer(mode, locale, cursor=False)
            visible = framebuffer(mode, locale, cursor=True)
            require(len(hidden) == len(visible) == 9600,
                    "framebuffer size differs")
            require(hidden != visible, "cursor phases are identical")
            records.append(
                f"m{mode}l{locale}:"
                f"{hashlib.sha256(hidden).hexdigest()[:12]}/"
                f"{hashlib.sha256(visible).hexdigest()[:12]}"
            )
            if args.output:
                args.output.mkdir(parents=True, exist_ok=True)
                (args.output / f"vidtest-m{mode}-l{locale}-hidden.bin").write_bytes(hidden)
                (args.output / f"vidtest-m{mode}-l{locale}-visible.bin").write_bytes(visible)
    print("VIDTEST-ORACLE: PASS " + " ".join(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
