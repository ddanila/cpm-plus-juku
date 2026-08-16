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
| 2. Native RAM console | Implemented; simulator-qualified | Authentic MODX geometry/timing extracted; CC0 5x7 font, packed 80x24 renderer, and blinking underline are shared through `juku-common`; the independent 9,600-byte oracle passes. See [`modx-console-reference.md`](modx-console-reference.md). An explicit full blink-cycle test and physical display check remain. |
| 3. Inventory and budget | Complete | `make rom-budget-check` measures linked shared modules, enforces exact 6 KiB/10 KiB envelopes, and records the mode-crossing call graph. The conservative target was exceeded by the measured 38.25 KiB transient span. See [`rom-budget.md`](rom-budget.md). |
| 4. ROM ABI | Complete | `juku-common` defines ABI 1.0 at `FF00h` and a fixed 196-byte gate at `D620h`; the retained ABI self-test image proves manifest rejection/acceptance, registers, stack guards, DI/PIC ownership, mode 0/1/3 crossings, overlay-write rejection, helper access, and concurrent 19,200 serial traffic. |
| 5. Automatic network boot | Complete in simulation | Reset establishes PPI/PIC and stock raster/refresh state; POST has distinct C1..C5 failures and reaches C4 target readiness in 725,602 cycles. Identity-free V15 rejects a corrupt extension, recovers, and boots the real CP/M Plus image without keys; `A>`, `DIR`, and `DIAG CPU` pass with zero retries/overruns. The host also recovers when its one-shot C4 observation was missed. See [`network-first-rom-auto-boot.md`](network-first-rom-auto-boot.md). |
| 6. Move services / relink | Complete in simulation | Resident serial, keyboard, console/font, and the 676-byte NetDisk-v3 read-ahead/write-through service pass. The regenerated system moves loader/BDOS/BIOS to `9A00h`/`9D00h`/`BC00h`; the packed 912-byte adapter at `C000h` yields a measured 39,168-byte transient span, exactly 8 KiB over baseline. The real system completes `DIR`, `DIAG CPU`, and `ERA README.TXT` with 38 reads, resident writes, zero retries/overruns, and byte-exact screen parity. |
| 7. Recovery matrix | Complete in simulation | Absent-host and missed-ready recovery, corrupt bootstrap rejection, target reset amid stale extension bytes, truncated/delayed/duplicate/bad-CRC disk replies, deliberate modeled 8251 overrun, idempotent request replay, and stateless disk-server restart pass. Every CP/M path reaches `A>`, `DIR`, `DIAG CPU`, and `ERA README.TXT`; the compound case recovers from three retries and three resident overruns. See [`network-first-rom-recovery.md`](network-first-rom-recovery.md). |
| 8. Physical qualification | Candidate packaged; bench pending | `network-first-abi1-cs00015-c1` fixes the exact D15/D16, CP/M, fastboot, and disk hashes and is produced by `make bench-candidate`; see [`network-first-rom-bench-candidate.md`](network-first-rom-bench-candidate.md). Burn C1 and run the complete CS00015 matrix including display, cursor, write, recovery, and repeated timing. |
| 9. Acceptance audit | Pending | Publish final maps, artifacts, logs, hashes, timings, and parity decision. |

## Later improvements, outside the first ROM baseline

- compress or delta-encode the initial payload only when end-to-end 8080
  decode time beats the extra wire bytes;
- negotiate protocol capabilities and ROM ABI features rather than infer them
  from a banner;
- prefetch CP/M directory/allocation records and coalesce sequential NetDisk
  operations, with cache invalidation proved for writes;
- give the host a small boot manifest so it can select a system without relying
  on station identity;
- add a remote diagnostic/status channel that remains bounded and cannot stall
  normal disk or console traffic;
- retain a small fixed RAM boot-status record containing the last POST stage,
  transfer/retry reason, ROM build, and warm/cold-boot marker so the host and
  `DIAG` can explain a failed or recovered boot without a display;
- add an optional checksummed boot manifest with image length, load address,
  entry, protocol requirements, and build identity; defer cryptographic
  authentication until its EPROM and 8080 cost is measured;
- consider two host-selectable system slots or a last-known-good image on the
  server; recovery selection must not require enlarging the ROM menu;
- investigate baud rates above 19,200 only as a separately named experiment;
  the proven mode-2/count-4 setting remains the production default;
- consider a concealed recovery/service entry or local fallback only after the
  automatic network-only machine is a stable baseline.

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
- carry the ROM ABI, framebuffer console, keyboard, automatic boot, and
  NetDisk checks into the structural HDL model after the C model is stable;
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
