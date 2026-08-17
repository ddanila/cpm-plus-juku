# CP/M Plus for Juku

This repository contains the strict-Intel-8080, non-banked CP/M Plus 3.1 port
for the Juku E5101/E5104. It is a genuine CP/M Plus port using Digital
Research's CP/M 3 CCP, BDOS, SCB, and BIOS conventions; it is not CP/Mish 3.

Danila Sukharev owns the project-written code. OpenAI GPT-5.6 Sol was used as a
development assistant. Third-party authors and licenses are preserved in
`NOTICE.md` and below their respective `third_party/` directories.

## Repository boundary

The three cooperating projects have deliberately separate responsibilities:

- `cpm-plus-juku`: CP/M Plus system generation, CP/M 3 BIOS policy, images,
  and CP/M Plus tests;
- [`juku-common`](https://github.com/ddanila/juku-common): shared Juku RAM
  console, keyboard, NetDisk, direct-fastboot, music, and diagnostic sources;
- [`8080-cosim`](https://github.com/ddanila/8080-cosim): machine model and
  Janet host tools.

[`cpmish`](https://github.com/ddanila/cpmish) remains the separate CP/M
2.2-compatible Juku distribution and the current physical baseline. Published
CP/Mish history is not rewritten to hide the prototype from which this port
was separated. [`HISTORY.md`](HISTORY.md) records the exact prototype,
separation, and shared-code commits.

## Current memory maps

The frozen stock-ROM/RAM-BIOS baseline remains deliberately conservative:

```text
0100h..79FFh  30,976-byte (30.25 KiB) transient program area
7A00h..7CFFh  CP/M Plus loader
7D00h..9BFFh  CP/M Plus BDOS
9C00h..9FFFh  Juku CP/M 3 BIOS
A000h..AFFFh  CP/M-compatible Juku hardware adapter
B000h..B409h  adapter state, buffers, and NetDisk-v3 cache
```

Ekta4402 command `N` loads a 16 KiB container at `7000h` using direct V15
fastboot at 19,200/8N1. The same container also boots through the stock Janet
`TN` path and a dynamically loaded V15 core, so Ekta4401 needs no ROM change.
The system then owns RAM and establishes a fresh 19,200/8O1 NetDisk-v3
session. Its A: volume contains `CCP.COM`, `DIAG.COM`, and `README.TXT`.

The baseline is simulator-qualified through all of the following in one test:

- physical-time pacing at CS00015's measured 1.70 MHz CPU rate;
- reproduction of the old target-turnaround, host-guard, and stock-PIC
  failures through their actual legacy code paths;
- direct Ekta4402/V15 boot with zero stock Janet frames;
- stock Ekta4401 `TN` bootstrap into the same V15 system;
- the CP/M Plus banner and `A>` prompt;
- NetDisk-v3 `DIR`;
- loading `DIAG.COM` and passing `DIAG CPU`;
- all-RAM memory mode, fully masked PIC, and 8O1 USART state.

The network-first ROM now adds a third simulator-qualified entry path. Reset
runs bounded POST, announces C4 at 19,200/8N1, and loads this same CP/M Plus
system with no monitor command, keypress, or Janet station identity. A separate
ROM-ABI consumer image now validates the resident manifest, delegates the CP/M
19,200/8O1 serial initialization, consumes local input through the shared
resident keyboard, and renders through the resident 80x24 console/font plus a
119-byte low-RAM pixel helper. It reaches `A>`, accepts `DIR` and `DIAG CPU`,
and completes both with no USART overrun. Its final 9,600-byte framebuffer is
byte-identical to the RAM baseline. The Creep font and faster cursor entered
CS00015 as candidate C3. Its first blind automatic-ROM run proved reset, V15,
resident output, and NetDisk, then exposed a blocking local-`CONIN` race in the
matching CP/M N4 input path. Candidate C4 keeps both C3 EPROM halves unchanged
and freezes the corrected runtime. Three physical cold boots now pass the full
remote `DIR`, sequential-read, `DIAG CPU`, `WBOOT`, and erase/write matrix in
6.068--6.070 seconds. A replacement host also restores NetDisk/N4 and returns
`DIR` to `A>` without RESET. The earlier apparent reconnect failure was a
host-only PTY input flush, now fixed and regression-tested. Only the exact
resident display, cursor, and local-keyboard observation remains before C4
promotion.
C1 was superseded before burning after a stock-ROM/manual-resume run exposed
its deterministic glyph corruption, and C2/C3 remain immutable.
Resident
NetDisk-v3 owns bounded read-ahead and
synchronous write-through, including three-attempt recovery and cache
invalidation. The dedicated CP/M system is regenerated and relinked as follows:

```text
0100h..99FFh  39,168-byte (38.25 KiB) transient program area
9A00h..9CFFh  CP/M Plus loader
9D00h..BBFFh  CP/M Plus BDOS
BC00h..BFFFh  Juku CP/M 3 BIOS
C000h..C39Fh  928-byte ROM-ABI binding and remote console
C5ECh..C909h  sparse mutable adapter state, directory buffer, and cache
D600h..D7FFh  fixed ROM call gate/state and framebuffer helper
D800h..FFFFh  resident runtime ROM
```

The separately named C5/ABI 1.1 binding uses eight-record A:/B: buffers at
`CB80h..CF97h` and `CFA0h..D3B7h`; neither changes the TPA.
Alternating B: and A: in cosimulation leaves both resident validity records
live. An ABI 1.0 consumer may still share one buffer and triggers C5's safe
alias-invalidating fallback.

The exact transient span is 8,192 bytes larger than the frozen baseline. The
cosimulator validates the live page-zero loader/BDOS chain as well as `A>`,
`DIR`, paginated `TYPE README.TXT`, `DIAG CPU`, explicit `WBOOT`,
`ERA README.TXT`, console parity, and zero resident USART overruns.

Physical CS00015 testing first reproduced the timing/ownership failures and
proved manual 19,200-baud reattachment. The host now treats a fully sent V15
stream with a missing final reply as explicitly unconfirmed and proceeds to
NetDisk instead of retransmitting into a possibly running CP/M. A subsequent
stock-`TN` run received the final confirmation normally, attached A:
immediately, and reached `A>` without I/O errors. That run also physically
qualified S21=`02h` as 53x24, the narrower Creep-derived font, and the doubled
cursor blink rate. See [`docs/cs00015-netdisk-v3-timing.md`](docs/cs00015-netdisk-v3-timing.md)
and [`docs/s21-video-modes.md`](docs/s21-video-modes.md).
The adapter intentionally retains the proven CP/M-compatible hardware-call
shape until a native CP/M 3 implementation matches this baseline.

## Build

On Debian/Ubuntu:

```sh
sudo apt install build-essential bison cpmtools python3 python3-pexpect
git clone --recurse-submodules https://github.com/ddanila/cpm-plus-juku.git
cd cpm-plus-juku
make
```

The build compiles the pinned zmac, ld80, and ZX0 sources locally. It produces:

```text
out/cpm-plus-juku-system.bin       V15 RAM container
out/cpm-plus-juku-fastboot-v15.bin direct-fastboot bundle
out/cpm-plus-juku-network-rom-system.bin       ROM-ABI consumer container
out/cpm-plus-juku-network-rom-fastboot-v15.bin ROM-ABI consumer fastboot bundle
out/cpm-plus-juku.img              host-backed A: volume
out/cpm-plus-juku-recovery.img     named immutable C4 recovery A:
out/cpm-plus-juku-native-recovery.img post-C4 recovery A: with STATUS/KEYTEST
out/cpm-plus-juku-full.img         licensed utility A:
out/cpm-plus-juku-museum-demo.img  opt-in PROFILE.SUB demo A:
out/cpm-plus-juku-apps.juk         approved native 800 KiB B:
```

Every named distribution image has a `.report.json` recording contents,
provenance, free space, and hashes. The profiles and validation commands are
documented in
[`docs/distribution-profiles.md`](docs/distribution-profiles.md). Published
Juku 3000 game disks remain supported external read-only B: inputs; their
licensing boundary is recorded in
[`docs/juku3000-media-provenance.md`](docs/juku3000-media-provenance.md).

`prebuilt/` contains byte-for-byte reference copies. `make check` first proves
that a fresh build matches them. Current SHA-256 values are:

- system: `3b61b1fe5de4e7e4cf4fa20dd88582210d5c8c09ef690bc1246021aa97983b6d`;
- fastboot: `37155d7966cfc655f2755364a0cc9c2f84227c20dd58afd77d0946f013404042`;
- network-ROM system: `74f2089bc85ef18fe90bb5868570e177037f55311f88484f27181425a7920ab1`;
- network-ROM fastboot: `0411ff682e7356d33073309b284bde33d627ea6c7769fdb1538d99c2c589bf4a`;
- A: volume: `b4402dc9be86fef9532e61fff491dc3b93dc0db40e68d575c89aab083160bec1`.

The checked-in baseline `third_party/cpm3/cpm3.sys` and relinked
`cpm3-network-rom.sys` make a normal build independent of the CP/M-hosted
development tools. To regenerate either, provide ZXCC plus `RMAC.COM`,
`LINK.COM`, and `GENCPM.COM` from the matching CP/M 3 tool set:

```sh
make regenerate-cpm3 ZXCC=/path/to/zxcc CPM3_TOOLS=/path/to/tools
make regenerate-cpm3-rom ZXCC=/path/to/zxcc CPM3_TOOLS=/path/to/tools
```

## Simulation

Place `cpm-plus-juku` and `8080-cosim` beside each other, or set
`JUKU_COSIM_ROOT`, then run:

```sh
make check
make network-rom-cosim-check  # focused keyless reset-ROM path
make bench-candidate          # full C-model matrix, structural HDL, package
make release-candidate        # deterministic ABI 1.1 C5 CP/M 3.1 artifact set
```

For the controlled CS00015 burn, `tools/physical_qualification.py` verifies
the exact C4 package, records repeated boot timing and host logs, keeps writes
in a fresh per-boot image, and audits the manual display/keyboard/recovery
matrix. The complete commands are in the bench-candidate document below.

## Physical direct-ROM test

With Ekta4402 fitted for bench testing, start the server and press `N` alone in
the monitor. This path is physically qualified on CS00015:

```sh
cd ~/fun/cpm-plus-juku && ../8080-cosim/tools/janet_disk_server.py \
  --fast-stage1 out/cpm-plus-juku-fastboot-v15.bin --direct-fastboot \
  --disk-baud 19200 --disk-protocol 3 --timeout 86400 \
  /dev/ttyUSB0 out/cpm-plus-juku-system.bin out/cpm-plus-juku.img
```

The corresponding automatic-ROM command and named CS00015 C4 bench gate are
recorded in
[`docs/network-first-rom-auto-boot.md`](docs/network-first-rom-auto-boot.md).

## Roadmap

The immediate work preserves the simulator-proven compatibility adapter as the
reference, completes CS00015 qualification, and builds the MODX-compatible
compact console plus blinking cursor in RAM first.

The RAM console milestone now passes its packed 80x24 framebuffer oracle. The
binary extraction, period-document discrepancy, exact video timing, font
provenance, and remaining physical checks are recorded in
[`docs/modx-console-reference.md`](docs/modx-console-reference.md).

The network-first 16 KiB ROM now has bounded quick POST, automatic
19,200-baud boot with no menu or keypress, and a proven versioned resident ABI.
The CP/M consumer validates that ABI and uses its serial, keyboard, and compact
console/font and NetDisk-v3 read/write services. CP/M Plus has been regenerated
and relinked upward, yielding an exact 8 KiB TPA gain while retaining thin
bindings and mutable state in RAM. The complete simulated recovery matrix now
covers stale bootstrap bytes, truncated/delayed/duplicated/corrupt disk
traffic, modeled 8251 overrun, bootstrap-time and live post-prompt stateless
server replacement, explicit warm boot, and a 16-cycle/271-read soak. The exact results
are in
[`docs/network-first-rom-recovery.md`](docs/network-first-rom-recovery.md).
The focused structural gate, rerun for C3 in `8080-cosim` commit `b04aa388`,
boots the byte-identical C4 image through `juku_top`/`vm80a` and proves its resident
framebuffer, keyboard, serial, and one NetDisk-v3 DMA transaction. Full-system
behavior remains guarded by the C-model matrix and the pending physical test.
The deterministic `network-first-abi1-cs00015-c4` programming/runtime package,
hashes, socket order, and the remaining local-console observation are in
[`docs/network-first-rom-bench-candidate.md`](docs/network-first-rom-bench-candidate.md).
The memory constraints, staged migration, and acceptance contract are in
[`docs/network-first-rom-plan.md`](docs/network-first-rom-plan.md).
The reproducible linked-byte inventory, fixed ROM envelopes, mode-crossing
call graph, and achieved 38.25 KiB transient span are in
[`docs/rom-budget.md`](docs/rom-budget.md); `make rom-budget-check` enforces
the allocation and measures the first resident serial implementation.

ABI 1.0 is now fixed at `FF00h`, with a copied low-RAM gate and framebuffer
helper. The deterministic `8080-cosim` implementation proves overlay, stack,
register, interrupt, live-serial, and recovery contracts; its generated D15/D16
halves are the controlled C4 bench candidate, not a promoted release. They are
byte-identical to the C3 chips already installed in CS00015.

A separately named ABI 1.1 C5 desk candidate keeps every 1.0 address intact
and adds reset-latched S21/locale, a four-pair key-remap vector, and S21 bit-0
automatic-versus-local-`N` boot policy. Its matching CP/M system consumes the
latched byte and `STATUS.COM` 1.3 reports the selected locale and exact retained
status fields. C5 has passed the monitorless CS00015 boot/disk/diagnostic/
keyboard/reconnect matrix; C4 remains the immutable fallback until a working
display confirms C5 geometry, glyphs, and cursor behavior. Simulation proves
the matching ROM/CP/M selection for all four S21 video geometries.
The finalized desk artifact set now has a distinct ABI 1.1 boot manifest,
exact ROM halves, matching locale-native system/bootstrap, all published media
and reports, license/notice files, and a byte-reproducible tar. Its contents,
blind hardware evidence, and remaining display promotion boundary are recorded in
[`docs/cpm-plus-31-c5-release-candidate.md`](docs/cpm-plus-31-c5-release-candidate.md).
