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

## Current baseline

The initial baseline is deliberately conservative:

```text
0100h..7CFFh  31 KiB transient program area
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
ROM-ABI consumer image now validates the resident manifest and delegates the
CP/M 19,200/8O1 serial initialization to `JCGINIT`/`JCGSERINIT`; it reaches
`A>`, completes `DIR`, and passes `DIAG CPU` with no USART overrun. This is
still a desk image rather than a D15/D16 programming release. The first binding
changes the adapter from 2,132 to 2,130 linked bytes, so it deliberately makes
no larger-TPA claim yet.

Physical CS00015 testing reproduced the timing/ownership failures. With the
corrected server manually retained at 19,200, the same running machine then
recovered to `A>`, completed `DIR`, and ran the full `DIAG` successfully. This
qualifies the corrected resident NetDisk-v3 path. The remaining physical issue
is earlier in the stock-`TN` wrapper: it misses the final V15 `JA` completion,
returns the host to 9,600, and leaves the already-started CP/M without its disk
server. The evidence, cycle budgets, fixes, and remaining acceptance item are in
[`docs/cs00015-netdisk-v3-timing.md`](docs/cs00015-netdisk-v3-timing.md).
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
```

`prebuilt/` contains byte-for-byte reference copies. `make check` first proves
that a fresh build matches them. Current SHA-256 values are:

- system: `170e3c2e91790ff08bcb846af65e0726cf8cfdbec53d813fde68f7762e6a96cd`;
- fastboot: `5ae6c667d0fc0a23f93d184924b771adaca08fecc3319bae1d2e280664d7faec`;
- network-ROM system: `234aa1726857e22a18b13330073db849987745c8f02b83aabb4e2c75dd3599a2`;
- network-ROM fastboot: `3d71aa9854728a04ab3146ada1caea80c4c6ddfda5cc2dc8468878a5ab462697`;
- A: volume: `bc14a67a441ad8c24b7574ee5e290866b058a6fe5d04c05b462b8d2b3abc3100`.

The checked-in `third_party/cpm3/cpm3.sys` makes a normal build independent of
the historical CP/M-hosted development tools. To regenerate it exactly, also
provide ZXCC plus `RMAC.COM`, `LINK.COM`, and `GENCPM.COM`:

```sh
make regenerate-cpm3 ZXCC=/path/to/zxcc CPM3_TOOLS=/path/to/tools
```

## Simulation

Place `cpm-plus-juku` and `8080-cosim` beside each other, or set
`JUKU_COSIM_ROOT`, then run:

```sh
make check
make network-rom-cosim-check  # focused keyless reset-ROM path
```

## Future physical test

After Ekta4402 is explicitly selected for bench testing, start the server and
press `N` alone in the monitor:

```sh
cd ~/fun/cpm-plus-juku && ../8080-cosim/tools/janet_disk_server.py \
  --fast-stage1 out/cpm-plus-juku-fastboot-v15.bin --direct-fastboot \
  --disk-baud 19200 --disk-protocol 3 --timeout 86400 \
  /dev/ttyUSB0 out/cpm-plus-juku-system.bin out/cpm-plus-juku.img
```

The corresponding automatic-ROM command and its explicit do-not-program gate
are recorded in
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
The first real CP/M consumer validates that ABI and uses its serial initializer.
The next milestone moves keyboard, console/font, and the complete NetDisk
service behind the same interface. CP/M Plus will retain only thin bindings and
mutable state in RAM, then be relinked upward to turn the saving into a measured
larger TPA. The exact memory constraints, staged migration,
recovery cases, and acceptance contract are in
[`docs/network-first-rom-plan.md`](docs/network-first-rom-plan.md).
The reproducible linked-byte inventory, fixed ROM envelopes, mode-crossing
call graph, and provisional 33 KiB TPA target are in
[`docs/rom-budget.md`](docs/rom-budget.md); `make rom-budget-check` enforces
the allocation and measures the first resident serial implementation.

ABI 1.0 is now fixed at `FF00h`, with a copied low-RAM gate and framebuffer
helper. The deterministic `8080-cosim` skeleton proves overlay, stack,
register, interrupt, and live-serial contracts; its generated D15/D16 halves
are explicitly simulator-only and are not physical programming candidates.
