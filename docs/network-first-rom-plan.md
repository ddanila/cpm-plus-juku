# Network-first 16 KiB ROM plan

Status: **IN PROGRESS — AUTOMATIC BOOT AND 8 KiB TPA GAIN PROVEN**

Decision date: **2026-08-15**

## Decision

Build a new Juku ROM for the network CP/M Plus machine rather than keep adding
operator commands to the EktaSoft monitor. On reset it will run a very small,
bounded self-test and then boot from the network automatically at the
physically proven 19,200-baud setting. The first version needs no monitor menu,
floppy boot, local-disk boot, or keypress: network boot is the product.

The ROM will also become the common Juku platform layer. Stable code and
read-only tables should live in ROM once their RAM implementations are proven,
leaving only CP/M-specific policy, mutable state, buffers, and small call gates
in RAM. This is the main route to a larger CP/M Plus TPA.

CP/M Plus remains a separate port in this repository. CP/Mish is a useful
working reference and may consume the same Juku platform services, but it is
not being evolved into CP/M Plus and does not own this ROM. Hardware-common
assembler belongs in `juku-common`; firmware and machine integration belong in
`8080-cosim`; CP/M Plus BIOS bindings and memory policy belong here.

This work does not replace the current compatibility baseline. The present
RAM-BIOS system and the stock-ROM `TN` route remain frozen reference paths
until the new ROM passes the same simulator and physical tests.

## Hardware memory constraint

Juku has two 8 KiB EPROMs, but their 16 KiB contents are not all resident in
the normal runtime view:

```text
ROM file 0000h..17FFh   6 KiB boot-only; CPU 0000h..17FFh in reset mode 0
ROM file 1800h..3FFFh  10 KiB at CPU 1800h..3FFFh in reset mode 0,
                              remapped to D800h..FFFFh in runtime mode 1
```

Mode 1 leaves `0000h..D7FFh` as RAM and maps read-only ROM at
`D800h..FFFFh`; writes into that overlay are rejected rather than reaching the
framebuffer underneath. Mode 3 exposes all RAM but hides the resident ROM.
Consequently the practical design is:

- use the lower 6 KiB for reset, quick POST, automatic link acquisition, and
  initial loading;
- use the mapped upper 10 KiB for callable runtime services and constant
  tables;
- keep a small, fixed RAM call gate and stack below `D800h` for services that
  must cross memory modes;
- route every framebuffer mutation through a deliberately small helper copied
  to low RAM; it alone may hide the resident ROM in mode 3, update pixels,
  restore mode 1, and return;
- keep all mutable state, disk buffers, decompression destinations, and CP/M
  structures in RAM.

The ROM byte budget and the RAM saving are therefore separate measurements.
Filling all 16 KiB does not imply 16 KiB of callable runtime code.

## Proposed ROM contents

### Boot-only lower 6 KiB

1. Reset and deterministic hardware initialization: stack, PPI memory mode,
   PIC mask, D57, D11, and a known video/sound state.
2. A quick, bounded, non-interactive POST. Initially this should cover the
   already-small CPU register/ALU signature, a destructive scratch-RAM test in
   a region about to be overwritten, basic PIT/USART register progress, and
   ROM integrity. It must complete quickly enough that normal boot does not
   feel delayed.
3. Automatic 19,200/8N1 direct bootstrap using D57 mode 2/count 4. This is the
   proven electrical setting; the stock 9,600-baud Janet discovery stage and
   station-name entry are absent.
4. Checked reception and decompression of the CP/M Plus system, followed by a
   defined 19,200/8O1 NetDisk-v3 handoff.
5. Self-recovery: bounded packet waits, resynchronization, and automatic retry
   when the server is absent or a transfer is damaged. Failure indication must
   be useful but unobtrusive; a missing server must not require RESET.

### Runtime upper 10 KiB

Move code here only after its RAM version has a passing reference test:

- the native compact console, based on MODX's binary-proven 80x24 packed layout
  and 5x7 fonts (period prose calls it 80x25), its control-character handling,
  scrolling, and blinking underline cursor; the extracted binary is the final
  geometry oracle;
- keyboard matrix scanning, debounce/repeat policy, and translation tables;
- D57/D11 setup and the low-level polled serial primitives;
- NetDisk-v3 framing, CRC, retry/resynchronization, descriptor decoding, and
  the code portions of read-ahead;
- small common diagnostics and machine-identification services;
- common beeper/music primitives where their ROM cost displaces more RAM than
  it consumes;
- memory-mode, PIC, and platform-initialization helpers.

Disk cache data, DMA state, DPH/DPB structures, keyboard and cursor state,
protocol sequence state, and work stacks remain RAM objects. Large optional
diagnostics and user programs remain files on A:, not permanent ROM residents.

## Placement and migration policy

The objective is not merely to fill the EPROM. Every candidate must reduce RAM
use, remove duplication, or make reset/recovery possible. Use this order:

1. Put one-shot reset, POST, link acquisition, and system loading in the lower
   6 KiB. Do not spend resident space on code that cannot be called after boot.
2. Put immutable tables and platform services shared by boot, CP/M Plus, and
   later CP/Mish consumers in the resident 10 KiB.
3. Prefer services that replace more RAM than their fixed call gate and state
   require. Console/font, keyboard, serial, memory-mode control, and NetDisk
   framing are the first candidates.
4. Keep CP/M policy, buffers, caches, DMA/DPH/DPB data, protocol sequence state,
   cursor/keyboard state, and stacks in RAM.
5. Keep large, infrequent, or optional facilities such as exhaustive board
   diagnostics and demos as network-disk programs.

Migration is deliberately incremental: retain the working RAM implementation,
add a ROM-ABI implementation, compare both against the same simulator oracle,
then remove the RAM copy and relink. A source move without a measured TPA gain
does not count as progress.

The ABI should offer block operations where they amortize the mode-switch and
call-gate cost. In particular, a string/cell-span console operation and a
bounded multi-record NetDisk operation are preferable to forcing CP/M to cross
the ROM boundary once per character or 128-byte record. Simple byte calls stay
available for compatibility and diagnostics.

## ROM service ABI

The resident half needs an explicit ABI rather than calls to incidental ROM
addresses. Reserve a fixed, versioned table containing:

- a signature, ABI major/minor version, ROM build identity, and feature bits;
- fixed entry vectors for console init/status/input/output, serial init and
  byte I/O, bounded block/string output, NetDisk single- and multi-record
  transactions, keyboard scan, sound, and diagnostics;
- documented register preservation, interrupt state, memory mode, stack, and
  timeout contracts for every entry;
- a way for RAM software to reject an incompatible ROM cleanly.

The ABI and its tests belong in `juku-common`. The ROM implementation belongs
with the Juku machine/firmware code in `8080-cosim`; CP/M Plus owns only its
thin BIOS bindings and memory layout. CP/Mish may consume the same ABI later,
but it is not a prerequisite for the CP/M Plus ROM.

## CP/M Plus memory objective

The relink milestone is now measured. The frozen system's live page-zero chain
places its loader at `7A00h` and BDOS at `7D00h`, leaving `0100h..79FFh`
(30,976 bytes) for transient programs. The resident-ROM system places its
loader at `9A00h`, BDOS at `9D00h`, BIOS at `BC00h`, and thin adapter at
`C000h`, leaving `0100h..99FFh` (39,168 bytes). The exact gain is 8,192 bytes.
The before/after record contains:

- highest TPA address and total TPA bytes;
- RAM bytes used by BIOS vectors/bindings, mutable state, cache, stacks, and
  mode-switch helpers;
- ROM bytes used in the boot-only and resident windows;
- framebuffer and reserved hardware workspace boundaries;
- worst-case stack and buffer non-overlap proofs.

The simulator checks the live page-zero loader/BDOS vectors and the real
prompt, directory, transient diagnostic, framebuffer, keyboard, and NetDisk
path. The gain is therefore not inferred merely from source placement.

## Execution plan

1. **Freeze the reference.** Complete and record the corrected RAM-BIOS
   CS00015 qualification. Keep the stock-ROM path and its prebuilt artifacts
   reproducible.
2. **Finish the native console in RAM.** Extract MODX behavior from the period
   binary and documentation, implement the compact font and blinking underline
   cursor in `juku-common`, and add framebuffer/transcript regressions. This
   becomes the behavioral oracle for the later ROM copy.
3. **Inventory and budget.** Produce a call-graph/size report for console,
   keyboard, serial, NetDisk, diagnostics, and boot code. Choose what fits the
   6 KiB boot and 10 KiB resident windows without duplicating large routines.
4. **Define and prove the ROM ABI.** Implement fixed service vectors and a RAM
   call gate. Add simulator tests for mode switching, stack safety, register
   preservation, interrupt ownership, overlay-write rejection, low-RAM
   framebuffer helper access, and calls made while network traffic is active.
5. **Build automatic network boot.** Reset, run quick POST, acquire the host at
   19,200, validate and load CP/M Plus, switch to NetDisk-v3 framing, and reach
   `A>` without keyboard input. The target should explicitly announce that it
   is ready so a server started before reset cannot pollute the receive stream.
   The host must remain identity-agnostic.
6. **Move common services incrementally.** Replace one RAM implementation at a
   time with its ROM ABI call, retaining old/new comparison fixtures. Migrate
   serial/memory-mode primitives first, then keyboard, console/font, and
   NetDisk framing/batching. Relink CP/M Plus after each meaningful RAM
   reduction and record the memory map.
7. **Qualify recovery.** Simulate absent host, corrupt/truncated blocks,
   delayed replies, duplicate frames, USART overrun, reset during transfer,
   and server restart. The ROM must resynchronize and boot without another
   manual RESET once a valid server appears.
8. **Physical qualification.** Burn named D15/D16 images, record their hashes
   and board identity, then repeat cold boot, warm boot, `DIR`, sequential
   reads, `DIAG`, keyboard, compact console/cursor, server-loss recovery, and
   repeated boot timing on CS00015.
9. **Promote only after parity.** The network-first ROM becomes the preferred
   CP/M Plus configuration only after it matches the frozen RAM-BIOS behavior
   and improves the measured TPA. Stock ROM and RAM BIOS remain recovery and
   comparison configurations.

## Progress ledger

| step | status | evidence / remaining work |
| --- | --- | --- |
| 1. Freeze reference | Reference frozen | Corrected resident NetDisk-v3, stock-ROM route, timing failures, and the remaining stock-`TN` final-handoff issue are recorded. Final physical parity remains part of step 8. |
| 2. Native RAM console | Complete; 53x24 and 64x20 physically checked | Authentic timing for 40x24, 53x24, 64x20, and MODX-compatible 80x24 is selected by S21 bits 2:1. The Creep-derived font reserves a separator column while its CP437 UI subset joins across cell edges. Independent 9,600-byte oracles exercise all four modes; cursor phases are 512/1,024 polls. CS00015 physically confirms 53x24 and 64x20, glyph spacing, and cursor speed. See [`modx-console-reference.md`](modx-console-reference.md) and [`s21-video-modes.md`](s21-video-modes.md). |
| 3. Inventory and budget | Complete | `make rom-budget-check` measures linked shared modules, enforces exact 6 KiB/10 KiB envelopes, and records the mode-crossing call graph. The conservative target was exceeded by the measured 38.25 KiB transient span. See [`rom-budget.md`](rom-budget.md). |
| 4. ROM ABI | ABI 1.0 frozen; 1.1 desk-qualified | `juku-common` defines immutable ABI 1.0 at `FF00h` and a fixed 196-byte gate at `D620h`. The separate ABI 1.1 C5 image appends configuration and four-pair key-remap vectors, uses a 214-byte gate and 128-byte geometry-aware helper, and keeps every 1.0 address/contract unchanged. Executable tests cover manifests, registers, stack guards, DI/PIC ownership, all four S21 video modes, overlay rejection, exact locale pixels, remapping, and bit-0 boot policy. |
| 5. Automatic network boot | Complete in simulation | Reset establishes PPI/PIC and stock raster/refresh state; POST has distinct C1..C5 failures and reaches C4 target readiness in 725,602 cycles. Identity-free V15 rejects a corrupt extension, recovers, and boots the real CP/M Plus image without keys; `A>`, `DIR`, and `DIAG CPU` pass with zero retries/overruns. The host also recovers when its one-shot C4 observation was missed. See [`network-first-rom-auto-boot.md`](network-first-rom-auto-boot.md). |
| 6. Move services / relink | Complete in simulation | Resident serial, keyboard, console/font, and the 676-byte NetDisk-v3 read-ahead/write-through service pass. The regenerated system moves loader/BDOS/BIOS to `9A00h`/`9D00h`/`BC00h`; the packed 928-byte adapter at `C000h` yields a measured 39,168-byte transient span, exactly 8 KiB over baseline. The real system completes `DIR`, paginated `TYPE README.TXT`, `DIAG CPU`, explicit `WBOOT`, and `ERA README.TXT` with 53 reads, one write, zero retries/overruns, and byte-exact screen parity. |
| 7. Recovery matrix | Complete in simulation | Absent-host and missed-ready recovery, corrupt bootstrap rejection, target reset amid stale extension bytes, truncated/delayed/duplicate/bad-CRC disk replies, deliberate modeled 8251 overrun, idempotent request replay, and stateless server restart both during bootstrap and after `A>` pass. Every path completes `DIR`, paginated `TYPE README.TXT`, `DIAG CPU`, explicit `WBOOT`, and `ERA README.TXT`. A 16-cycle post-reconnect soak completes 271 reads and one write without retry or overrun. See [`network-first-rom-recovery.md`](network-first-rom-recovery.md). |
| 8. Physical qualification | Blind matrix complete; resident local console pending | Three physical CS00015 cold boots completed the full automated `DIR`/sequential-read/`DIAG CPU`/`WBOOT`/erase matrix at 6.068--6.070 seconds. After host loss, a corrected replacement host delivered `DIR` and returned to `A>` without RESET; tracing proved the earlier apparent failure was a host PTY flush while Juku continued valid polls. Exact resident 80x24 display, cursor, and local keyboard remain to observe with a monitor. See [`network-first-rom-bench-candidate.md`](network-first-rom-bench-candidate.md) and the [blind-run evidence](cs00015-c4-blind-qualification-20260817.md). |
| 9. Acceptance audit | Pending local console evidence | Maps, immutable artifact hashes, repeat timings, command transcripts, and reconnect diagnosis are published. Promotion waits only for the exact resident display/cursor/local-keyboard observation and final recorder audit. |

## Post-baseline results and remaining experiments

- V15 uses ZX0 compression after end-to-end timing experiments; the stable
  production rate remains 19,200 baud after separately named higher-rate tests.
- NetDisk operation 26h provides explicit protocol capabilities, and C5 uses
  independent eight-record A:/B: read-ahead with write invalidation.
- The checksummed host manifest binds load/entry addresses, protocol and ABI
  requirements, build identity, two system slots, and all advertised media
  without Janet station identity. Last-known-good promotion requires the first
  valid disk request.
- Bounded operations 24h, 25h, and 27h publish status, diagnostics, and the C5
  retained D610h..D613h POST/bootstrap/retry record without stalling ordinary
  disk or local console service.
- C5 implements the concealed local-`N` recovery gate when S21 bit 0 is clear;
  no mandatory ROM menu was added.
- Cryptographic authentication remains deliberately deferred until its EPROM,
  wire, and strict-8080 decode costs are measured. Reproducible hashes,
  Fletcher/CRC guards, and manifest validation remain mandatory meanwhile.

### Keyboard S21 configuration

The new identity-free network protocol no longer needs S21's stock station
number fields, so the eight keyboard DIP bits become a machine configuration
byte shared by ROM and the loaded operating system. The all-RAM CP/M console
implements bits 2:1, and the separately named ABI 1.1 C5 ROM applies the same
table to its resident console:

| logical configuration bits | proposed meaning |
| --- | --- |
| bit 0 | ROM-only policy: `1` boots from the network automatically and immediately; `0` waits at the concealed local-`N` recovery gate |
| bits 2:1 = `00` | 40x24, stock 320x241 timing |
| bits 2:1 = `01` | 53x24, stock 320x241 timing |
| bits 2:1 = `10` | 64x20, historical 384x201 timing |
| bits 2:1 = `11` | MODX-compatible 400x192, 80x24 compact console |
| bits 4:3 | English, Estonian, CP866 Russian, or English/user-remap character bank |
| bits 7:5 | reserved for later settings |

The physical keyboard drawing serializes S21 during scan positions 8..15 on
`CONTRDAT`; S21.1..S21.8 map to logical bits 7..0, with a closed active-low
contact becoming logical one. The shared keyboard driver implements that
mapping, the simulator models it electrically, and CS00015 raw `02h` selects
53x24. C5 samples S21 once at reset, stores the raw byte in its fixed
status/workspace, and exposes it through the ABI 1.1 resident query. Boot bit
0 is consumed only by ROM. The video and locale fields are shared policy:
ROM selects its initial console timing from it and CP/M reads the same latched
value through the ABI when initializing its console, rather than resampling or
inventing a separate setting. The host, `DIAG`, and `STATUS` report the raw
byte and decoded settings. Resolution selection is table-driven and covered
by geometry, exact-framebuffer, and ROM-to-CP/M handoff regressions for all
four combinations; 53x24 and 64x20 also have physical display evidence on
CS00015.

### CP/M Plus usability

- make the MODX-compatible console, font selection, keyboard translation, and
  cursor BIOS facilities rather than separately loaded transient utilities;
- support selectable English, Estonian, and Russian tables without duplicating
  the renderer, and permit a small per-machine remap for physically dead keys;
- expose ROM, CP/M system, protocol, disk-image, and host build identities in
  one concise version/status command and in host session logs;
- prove warm boot, server restart, disk reconnect, and a configurable initial
  CCP command before adding a museum/demo autorun mode;
- obtain date/time from the network host if CP/M Plus applications can consume
  it without making boot or disk service depend on a clock server;
- grow the shared `DIAG` program from the same `juku-common` diagnostic sources
  used by the ROM, retaining large and infrequently used tests on disk.
- add a resident memory-map/status command which reports the live loader, BDOS,
  BIOS, TPA limit, ROM ABI version, and last recovery reason without requiring
  a host-side log.

### NetDisk performance and media handling

- retain measured `DIR` and sequential-file-read baselines for every protocol
  change, separating wire time, target decode time, console output, and host
  scheduling;
- cache the directory and allocation records CP/M predictably rereads, and
  coalesce sequential 128-byte records into bounded larger replies;
- add ROM-ABI block transfer calls only after measuring their complete cost,
  including target copy/CRC time and memory-mode crossings, against the current
  NetDisk-v3 single-record baseline;
- retain independent per-drive read-ahead and invalidation state, including
  native Juku geometry for B: and later drives;
- add read-only, writable-copy, and snapshot-backed host modes so museum media
  cannot be modified accidentally;
- add write caching only with explicit flush, warm-boot, retry, disconnect, and
  power-loss contracts; correctness takes precedence over benchmark gains;
- first move the current single-record write transaction behind the resident
  ABI, preserving synchronous write-through semantics and invalidating every
  affected per-drive read-ahead entry before considering any write cache;
- let a boot manifest advertise available system and data images while keeping
  the server independent of Janet station identity.

### Simulator, packaging, and physical fleet

- reproduce each physical failure using real firmware branches, device limits,
  and timing; do not replace hardware behavior with injected CP/M errors;
- run long NetDisk read/write/reconnect soak tests in addition to the bounded
  boot and command regressions;
- extend the completed focused structural-HDL gate only when a new boundary
  benefits from it: the byte-identical C4 ROM already proves automatic reset/POST,
  framebuffer helper, keyboard, serial ABI, and one CRC-checked NetDisk-v3
  DMA record; full V15/CP/M, recovery, exact cursor pixels, and soak remain in
  the practical C-model oracle;
- provide one deterministic command that builds the combined ROM, named D15
  and D16 programmer images, CP/M system, disk images, hashes, and build map;
- generate a machine-readable ROM manifest and ABI-vector map from the same
  build that produces the programmer images, and reject stale CP/M bindings in
  CI rather than discovering an address mismatch on hardware;
- keep explicit machine profiles and service records for CS00000, CS00014,
  CS00015, and CS00024 rather than generalizing a fault seen on one board;
- keep CP/Mish and CP/M Plus as separate systems while moving only genuinely
  hardware-common, assembler-readable code through `juku-common`.

## Acceptance contract

The first network-first ROM is complete only when all of these are true:

- cold reset with no keypress reaches CP/M Plus over a 19,200-baud link;
- quick POST has a bounded measured duration and distinct, tested failures;
- a missing host causes automatic retry and later recovery, not a permanent
  tone, hang, or required reset;
- the ROM ABI, memory modes, PIC mask, USART framing, and stack boundaries are
  asserted by simulator checkpoints;
- compact console output, local keyboard input, and the blinking underline
  cursor work together;
- `DIR`, a sequential file read, `DIAG`, warm boot, and NetDisk reconnect pass;
- old failure fixtures still fail for the original reason and corrected
  fixtures pass without synthetic error injection;
- exact D15/D16 images, hashes, build identity, RAM/ROM map, TPA gain, simulator
  logs, and repeated CS00015 results are documented;
- the relinked system retains its measured 39,168-byte transient span, exceeding
  the original minimum target, through final physical qualification.
