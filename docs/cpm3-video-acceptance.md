# CP/M Plus display acceptance

Status: **DESK COMPLETE; FOUR PHYSICAL DISPLAY OBSERVATIONS PENDING**

`VIDTEST.COM` is the deterministic display acceptance utility for the current
post-C6 CP/M Plus system. It is included in the full, development, and museum
profiles, but deliberately not in the small recovery images. It uses standard
CP/M 3 BDOS function 50 to read the native `JNS1` status record; it has no
fixed BIOS address and its 1,086-byte COM image passes the flow-aware strict
Intel-8080 audit with only the BDOS gate as a runtime dependency.

## Acceptance page

`VIDTEST` clears the local screen and derives its geometry and active locale
from the reset-latched S21 value. It draws:

- the first, last, leftmost, and rightmost display-cell boundaries;
- upper-case, lower-case, digit, and punctuation samples;
- representative bytes from the selected English, Estonian, CP866, or
  English/remap-fallback bank;
- an edge-connected CP437 border and junction sample in 80x24 mode;
- `VIDTEST READY` beside the final empty cell, where the normal BIOS underline
  cursor continues blinking.

Pressing any local or N4 key clears the page, prints `Juku Vidtest 1.0 DONE`,
and returns to CCP. The program does not write video RAM directly: every pixel
passes through the production BDOS/BIOS/ROM console path being accepted.

## Desk evidence

`make vidtest-cosim-check` runs the exact immutable C6 ROM, V16 stream,
post-C6 system, and generated full A: image. It covers English in 40x24,
53x24, 64x20, and 80x24, then the Estonian, CP866, and fallback banks in
80x24. During each live `VIDTEST` wait it repeatedly checkpoints the actual
9,600-byte framebuffer until it has captured both cursor phases.

Every capture must equal the independent source-font renderer byte for byte.
The standalone oracle additionally constructs both cursor phases for all
sixteen video/locale combinations. The seven executable cases also perform
`DIR`, paginated `TYPE`, `DIAG CPU`, warm boot, and write/erase around the
display test. All pass with zero NetDisk retries, zero resident USART
overruns, and strict-8080 fetched opcodes.

This is stronger than comparing a screenshot or applying OCR: it proves every
framebuffer bit, the selected raster geometry, locale mapping, joined UI
glyphs, and actual blink transitions. It does not prove that the analog monitor
shows the generated pixels correctly.

## Physical procedure

No EPROM change is required. Keep S21 bit 0 enabled for automatic network boot
and select English locale. Run the display workload once for each raw S21
value:

| raw S21 | geometry | switches added to auto-boot bit |
| --- | --- | --- |
| `01h` | 40x24 | none |
| `03h` | 53x24 | video bit 1 |
| `05h` | 64x20 | video bit 2 |
| `07h` | 80x24 | video bits 2:1 |

For example, start the 40x24 run before powering or resetting CS00015:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py run /dev/ttyUSB0 --profile display --output out/physical-CS00015-display-40x24
```

The runner waits at `VIDTEST READY` for 60 seconds before sending Enter. During
that interval observe:

1. all four edges are visible and the reported mode matches S21;
2. ordinary glyphs are separated and readable;
3. the active locale sample is stable;
4. in 80x24, the CP437 border and junctions have no cell gaps;
5. the underline cursor alternates visibly between shown and hidden;
6. any missing edge caused only by monitor width/centering is recorded as
   monitor cropping, not silently called a framebuffer failure.

Use a distinct result directory for every S21 setting. The retained runner
bundle proves that the exact C6 target produced and exited the corresponding
page; the human observation or photograph is the separate physical/analog
evidence.

Record all four observations in one JSON document conforming to
[`physical/display-observation.schema.json`](../physical/display-observation.schema.json).
Keep the document, photographs, and four result directories below the same
directory so their relative paths remain a portable evidence bundle. It binds
each observation to the raw S21 value and geometry, records monitor identity,
edge visibility or explained monitor cropping, readable glyphs, stable locale,
both cursor phases, the 80x24 joined CP437 sample, and every photograph hash.
Then produce the independent decision:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/display_acceptance.py out/physical-CS00015-display-observations.json --output out/physical-CS00015-display-acceptance.json
```

The auditor rechecks each physical result, reconstructs the exact `VIDTEST`
reply from `console.bin`, and requires the current system, V16 Fastboot, C6
ROM, full volume, display workload, and one shared host across all four runs.
It accepts a cropped analog edge only with an explicit monitor note; it never
turns a correct pixel oracle into a claim about the monitor. Only a passing
four-mode report closes M3. `make display-acceptance-check` exercises this
contract and its tamper cases without claiming that the physical observations
already exist. The resulting report is then combined with the independent
blind closure by `tools/physical_promotion.py`, as documented in
[`cpm3-physical-acceptance.md`](cpm3-physical-acceptance.md); neither evidence
class substitutes for the other.
