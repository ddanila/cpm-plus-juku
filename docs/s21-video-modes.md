# S21-selected CP/M Plus video modes

Status: **IMPLEMENTED; ALL MODES SIMULATED; 53x24 AND 64x20 PHYSICALLY CHECKED**

The all-RAM CP/M Plus console samples the keyboard's eight-position S21 bank
at cold console initialization. Drawing-derived scan order is S21.1..S21.8 to
logical bits 7..0; a closed/ON contact is logical one after complementing the
active-low `CONTRDAT` input. Thus logical bit 0 is S21.8.

Bits 2:1 select the historical console geometry:

| raw bits 2:1 | switch closed | geometry | cell | byte stride |
| --- | --- | --- | --- | ---: |
| `00` | neither S21.6 nor S21.7 | 40x24 | 8x10 | 40 |
| `01` | S21.7 | 53x24 | 6x10 | 40 |
| `10` | S21.6 | 64x20 | 6x10 | 48 |
| `11` | S21.6 and S21.7 | 80x24 | 5x8 | 50 |

The first two use the stock 320x241 timing sequence. Mode `10` uses the
EktaSoft 384x201 sequence, and mode `11` uses the exact MODX 400x192 writes.
Each text surface owns exactly 9,600 framebuffer bytes. Bit 0 is reserved for
the final ROM auto-netboot policy and is ignored by the present CP/M console.
Bits 4:3 are assigned to the character bank, while bits 7:5 remain reserved:

| raw bits 4:3 | character bank |
| --- | --- |
| `00` | English ASCII plus CP437 UI glyphs |
| `01` | English plus ISO-8859-1 Estonian `ÄÕÖÜäõöü` |
| `10` | English plus Russian CP866 |
| `11` | English/user-remap fallback |

CP866 keeps B0h..DFh for the connected CP437 pseudographics. `juku-common`
now provides these sparse banks and a single S21-selecting renderer behind the
`RAMLOCALEFONTS` build option. The compact 4 KiB compatibility adapter keeps
that option off: its four fixed modules already occupy 3,989 bytes, while the
locale-enabled set needs 4,678 bytes. The production integration therefore
belongs in the network-first ROM's reserved 2 KiB F000h..F7FFh font bank,
without shrinking the 39,168-byte TPA. The shared keyboard similarly provides
an optional four-pair persistent substitution table for dead or nonstandard
per-machine keys; exposing both facilities remains ABI-minor work.

The active base font is an adaptation of the MIT-licensed Creep 0.31 BDF.
Ordinary
letters and digits keep the fifth pixel blank, preventing adjacent characters
from sticking together. The 80x24 mode additionally exposes a compact subset
at standard CP437 byte values. Box strokes are deliberately edge-connected:
repeating horizontal glyphs fills all five pixels and vertically stacked
glyphs occupy both the top and bottom scanlines, forming solid lines. The
earlier corrected CC0 font remains in `juku-common` as a reference/future
wider-mode asset but is not embedded in the 4 KiB adapter.
The eight Estonian glyphs come from the same pinned Creep release. The 66
Russian glyphs come from u8g2's pinned public-domain Unicode 4x6 BDF and are
padded into the common seven-row cell. Both source hashes and readable glyph
references live in `juku-common` and are checked by independent oracles.

The console's underline phase is 512 idle status polls, half the physically
observed slow baseline. Cursor painting uses XOR so it does not destroy a
pseudographic connection on the eighth scanline.

The regression boots the real CP/M Plus image once in each S21 mode and runs
`DIR`, paginated `TYPE README.TXT`, `DIAG CPU`, `WBOOT`, and
`ERA README.TXT`. All four modes complete with 53 reads, one write, zero disk
retries, and zero resident USART overruns. For each mode an independent Python
renderer reproduces all 9,600 framebuffer bytes (accepting either cursor blink
phase). A stock-Ekta4401 `TN` simulation with raw S21=`02h` proves the same
53x24 path through the exact wrapper subsequently exercised on CS00015.

The ABI 1 resident-ROM compatibility console remains fixed at 80x24. This is
intentional: the all-RAM implementation establishes the switch policy and
geometry baseline without changing the published ROM ABI. A later ABI minor
extension can expose the ROM-latched raw byte and share mode policy during
automatic-ROM boot.

## CS00015 physical result

On 2026-08-16 CS00015 booted this all-RAM image through its existing stock
Ekta4401 `TN` path with raw S21=`02h`. The final V15 reply was received, the
first NetDisk request arrived at boot+8.811 seconds, and `A>` appeared without
the earlier I/O-error loop. The user judged the 53x24 mode correct, the font
spacing perfect, and the faster cursor correct. `DIR`, `DIAG`, and `WBOOT`
completed; host request sequence advanced through `30h`, always with status
zero and no retry. `TYPE README.TXT` was not run because the physical Space key
still produced no character. Space also failed in the machine's existing ROM
monitor, confirming that this was outside the CP/M driver and keymap. Subsequent
mechanical inspection found the cause: the keycap had been installed in the
wrong position, leaving its pushers above rather than below the contact
actuators, so pressing it could not close the contacts. After repositioning
the keycap, a multimeter confirms contact operation. A powered ROM/CP/M typing
check remains pending before the Space key is called physically qualified.

A second cold stock-`TN` run used raw S21=`04h` (only S21.6 closed). The host
learned station `01 -> 04`, received the final V15 reply, attached NetDisk, and
observed its first read at boot+11.976 seconds. The user confirmed that the
64x20 mode and font were correct and that `DIR` completed. This is especially
useful because 64x20 uses
the distinct 384x201 timing sequence; 40x24 adds no new raster timing beyond
the already qualified 53x24 family. The user's analog monitor did not expose
the complete wider raster, but every visible part was correct; this is a
monitor width/centering limitation rather than missing framebuffer content.
S21 was returned to `02h`, whose 53x24 picture fits that monitor perfectly.
