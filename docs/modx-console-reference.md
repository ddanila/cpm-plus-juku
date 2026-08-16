# MODX compact-console reference

Status: **CORRECTED SOURCE-FONT ORACLE AND BIOS FRAMEBUFFER PASS IN SIMULATION**

Evidence date: **2026-08-15**

## Why this is the reference

The network-first ROM needs a compact console that is historically appropriate
and does not consume CP/M's transient RAM. The period MODX binary is the
geometry and timing oracle; contemporary prose is useful corroboration but is
not allowed to override executed code or framebuffer arithmetic.

The source disk is `8080-cosim/media/disks/J3KUTIL4.JUK`, SHA-256
`d7a0b766a00c80ac487e24f48499386249534418ccb42739bae83a9e5a075de3`.
Converting its physical Juku ordering with `juku_image_to_volume` and extracting
the CP/M files produced:

| file | bytes | SHA-256 |
| --- | ---: | --- |
| `MODX.COM` | 3,584 | `0271f0301113e236b4759de32a107a8782f4c559399e1f195f93508520df71c2` |
| `LF.COM` | 2,048 | `392f7b5bafce6df921c30725cb0220e64818c4905b420dcc76425503b275fac5` |
| `ASCII` | 896 | `a260ca4d300ab22d02c7cc19f496db0643708061df3e8d2b31d22c7867065fe3` |
| `EST` | 896 | `ac2ae3d8fcb5a7daf60c7efbfbf2787f6006878d18a09342c143b4f4655291de` |
| `RUS` | 896 | `125bc68e3ecf8047420622b0f5492a4be6cc84dd9c89aafd058d2e7263dabbb2` |

Static disassembly identifies the installed resident module at file offset
`0267h`, length `09E4h`, assembled at origin zero. Its video programming
sequence is exact and ordered:

```text
OUT 17h,73h
OUT 11h,14h
OUT 12h,03h
OUT 15h,1Ah
OUT 15h,01h
OUT 16h,45h
```

The resident code uses framebuffer base `D800h`, a 50-byte raster stride, 192
visible scanlines, and 400-byte text rows. Glyphs have seven painted scanlines
and an eighth blank/cursor line. The executable geometry is therefore 400x192
pixels and **80 columns by 24 rows**.

The translated 1989 EKDOS 2.30 note calls MODX an 80x25 driver. That label is
recorded as period terminology, not silently corrected, but it conflicts with
the binary's 24-row framebuffer arithmetic. The implementation follows the
binary. A later compatibility mode may preserve the 80x25 name for users; it
must not invent a twenty-fifth framebuffer row.

## Shared implementation

`juku-common/platform/ram-console.asm` now provides the shared 80x24 renderer:

- the exact six MODX PIT writes;
- packed five-pixel read/modify/write cells across byte boundaries;
- 5x7 glyphs plus an eighth blank scanline;
- CR, LF, backspace, wrapping, scrolling, and `ESC L` clear;
- a five-pixel blinking underline cursor driven by the polled console-status
  path, independent of firmware interrupts;
- mode-3 framebuffer access with mode-1 restoration only for the transitional
  RomBios consumer.

The replacement ASCII font is generated from domsson's CC0 “oldschool” 5x7
bitmap. The source PNG SHA-256 is
`cf7d942a052f451a2bd24e02f193ea96433eeceeb705c8b0b2d2296f3ce57708`.
The checked generator validates that hash and reproduces all 95 glyphs from
U+0020 through U+007E as 665 assembler bytes. This avoids copying an
unestablished license from the period disk while retaining the proven MODX
geometry. Font source and license:
<https://opengameart.org/content/ascii-bitmap-font-oldschool>.

## Regression contract

The original generator used the correct 7-pixel horizontal pitch but an
incorrect 8-pixel vertical pitch. The source sheet actually starts its six
glyph rows at y=1,10,19,28,37,46. That one-pixel-per-row drift left the first
18 characters valid and deterministically corrupted later glyphs. A
stock-ROM/manual-resume CS00015 run exposed the defect before the network ROM
was burned.

`ram-console-font-reference.txt` now records every source glyph as readable
five-pixel rows. `ram_console_oracle.py` parses that reference independently of
the generator and assembly table. It rejects the old table first at U+0032 row
zero (`00h` instead of `70h`).

The C machine model remains in the stock 320x241 view until it observes the
complete ordered MODX signature, then reports a 50-byte/192-line view. The
CP/Mish console test independently renders the captured transcript into packed
pixels and compares all 9,600 framebuffer bytes. It also asserts the modeled
MODX state, all-RAM ownership, keyboard-driven `DIR`, and the underline at the
current prompt.

The ROM ABI regression now adds two test-only resident variants around the
unchanged production image. One calls the public console-status vector
exactly 1,024 times and proves the underline bytes are erased; the other calls
it 2,048 times and proves the original underline is restored. Both finish in
mode 1 with the same glyph framebuffer and passing ABI state. This closes the
explicit visible/hidden phase requirement in simulation.

The CP/M Plus regression now also captures its complete 875-byte boot/command
transcript, renders it pixel-by-pixel from the source-glyph reference, and
compares all 9,600 bytes with the actual BIOS framebuffer. The corrected run
matches exactly (SHA-256
`c5810fe73fe76199ae9e33241fcc3ef87aa3c49ddac63d3242d5034d7ecbe73d`).

The earlier transcript oracle parsed `ram-console-font.asm`; it therefore
proved packing and control-character policy but could not detect a bad font
generator. ROM-vs-RAM framebuffer parity had the same blind spot. The new
source-font comparison closes both gaps.

The oracle also found a real first-draft renderer defect: the packed cell-address
calculation reused `DE`, causing glyph selection from a column offset instead
of the character. The corrected shared routine passes the byte-exact 51K
RAM-BIOS test. The same oracle now covers the ROM ABI implementation and both
cursor phases. Physical phase timing remains part of CS00015 qualification.

## Follow-on improvements

- Add selectable English, Estonian, and Russian translation/font banks without
  duplicating the packed renderer.
- Keep font data in resident ROM and mutable cursor/position state in RAM.
- Consider a ROM-assisted bulk scroll or clear only if its call-gate overhead
  beats the RAM helper and preserves network service timing.
- Add a small machine-specific key remap table for dead or nonstandard keys.
- Retain a readable ASCII fallback and a test glyph for every bank.
- Measure the physical cursor phase on CS00015; tune the poll counter by
  measured CPU rate rather than changing the geometry or relying on IRQs.
