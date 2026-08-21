# CP/M Plus 3.1 for Juku

This repository contains a strict-Intel-8080, non-banked CP/M Plus 3.1 port for
the Juku E5101/E5104. It uses Digital Research's CP/M 3 CCP, BDOS, SCB, and
BIOS conventions; it is not CP/Mish 3.

Status: **The immutable ABI 1.2 C6 ROM, Priority-7 strict-8080 distribution,
and post-C6 M1--M5 desk implementation are complete. The corrected PIP path,
command history, status panel, and measured NetDisk cache pass the complete
simulator/recovery/package gates. CS00015 full/development evidence, the
controlled cache comparison, and four display observations remain physical
acceptance work.**

Danila Sukharev owns the project-written code. OpenAI GPT-5.6 Sol was used as a
development assistant. Third-party authors and licenses are retained in
`NOTICE.md` and the corresponding `third_party/` directories.

## Repository boundary

- `cpm-plus-juku`: CP/M Plus policy, BIOS bindings, system/media generation,
  manifests, packaging, and full-system tests.
- [`juku-common`](https://github.com/ddanila/juku-common): assembler-readable
  console, keyboard, NetDisk, bootstrap, music, diagnostics, and ROM ABI.
- [`8080-cosim`](https://github.com/ddanila/8080-cosim): Juku machine/timing
  model, network ROM, Janet/NetDisk host, and protocol tests.
- [`cpmish`](https://github.com/ddanila/cpmish): separate CP/M 2.2-compatible
  distribution. Shared hardware code moves through `juku-common`; the systems
  do not evolve into one another.

## Working configurations

The frozen stock-ROM/RAM-BIOS reference has a 30,976-byte transient area:

```text
0100h..79FFh  transient program area
7A00h..7CFFh  loader
7D00h..9BFFh  BDOS
9C00h..9FFFh  BIOS
A000h..AFFFh  compatibility adapter
```

It can boot through stock Ekta4401 `TN` or Ekta4402 `N`, using V15 at 19,200
baud after the stock discovery stage. It remains the recovery and timing
comparison path. Both exact prebuilt system/stream pairs—the stock-ROM/RAM-
BIOS path and its network-ROM counterpart—remain the build inputs;
their source boundary is repository commit `6ce52d8` with `juku-common`
`aeee23d`. Current common font and keyboard growth is not allowed to relink
and silently rename that physical baseline.

The physically qualified C5 system/V15 pair is frozen the same way. Its exact
source boundary is repository commit `e970088` with `juku-common` `04c2541`;
the build consumes hash-checked prebuilt bytes for C5 manifests and packages.
Later loaded-system maintenance is published under a new identity.

The network-first ROM resets directly into bounded POST and identity-free
19,200/8N1 Fastboot V16. The complete 361-byte receive/decompress loader is
already in the boot-only ROM; the host sends only a checked compressed system
stream, not executable loader code. Its CP/M image switches to 19,200/8O1
NetDisk v3 and uses resident platform services:

```text
0100h..99FFh  39,168-byte transient program area
9A00h..9CFFh  loader
9D00h..BB9Bh  BDOS
BB9Ch..BBFFh  SCB
BC00h..BFFFh  BIOS
C000h..D3B7h  C6 binding/services and independent A:/B: read-ahead
C5A0h..C63Fh  post-C6 hot state and first retained record
D3C0h..D570h  post-C6 retained records and cache code
D600h..D7FFh  ROM gate, helper, status, and mutable resident state
D800h..FFFFh  resident ROM window / underlying framebuffer RAM
```

The live page-zero chain and generated map prove an exact 8,192-byte TPA gain.
No banked memory is claimed.

The additive ROM line is:

- C4 / ABI 1.0: immutable automatic-boot reference;
- C5 / ABI 1.1: S21 boot/video/locale policy and key remapping; physically
  exercised on CS00015 through the blind boot, keyboard, disk, diagnostic,
  warm-boot, and live-reconnect matrix;
- C6 / ABI 1.2: bounded console-span, ordered NetDisk multi-request,
  instantaneous raw keyboard, sound, and bounded N4 block output. C6 is the
  completed simulator release, is now fitted and blind-qualified on CS00015,
  and does not modify C5 bytes;
- C7 / ABI 1.2: a separately named, simulator-qualified successor correcting
  modified raw-key scan order and carrying VC-compatible CP437 box glyphs.
  Exact Shift+F8 and Ctrl+Up/Home fixtures pass; focused CS00015 physical
  acceptance is pending and C6 remains immutable;
- C8 / ABI 1.3: resident N4/host services, 512 additional TPA bytes, bounded
  ROM diagnostics, and short/long POST codes. The exact pair is fitted in
  CS00015 and its automated cold-boot plus two repeated live-reconnect matrices
  pass. Two further cold boots, a physical-keyboard sample, and normal sound
  also pass; display and forced POST-failure observations are postponed. See
  [`docs/cs00015-c8-blind-qualification-20260820.md`](docs/cs00015-c8-blind-qualification-20260820.md).

## Build and verification

On Debian/Ubuntu:

```sh
sudo apt install build-essential bison cpmtools python3 python3-pexpect
git clone --recurse-submodules https://github.com/ddanila/cpm-plus-juku.git
cd cpm-plus-juku
make check
```

The repository builds pinned zmac, ld80, ZX0, and CP/M artifacts locally.
GitHub Actions runs the distribution check in a digest-pinned build container;
the container is rebuilt only when its definition or publishing workflow changes.
That image incorporates the digest-pinned `8080-cosim` smoke kit, allowing CI
to boot the generated system through the network ROM without cloning or
compiling the simulator on every run.
`make check` verifies immutable prebuilt images, ROM budgets, licensed volume
inputs, deterministic distribution reports, boot manifests, C5/C6/C7 package
reproducibility, the CP/M 3 toolchain output, native BIOS services,
observability/recovery, the 23-program candidate catalogue, every admitted DRI
and project utility on the current C6 path, live disk/stack/TPA accounting, and
the complete legacy/production cosimulation matrix. It also executes the
same-source M4 cache-off/cache-on desk comparison; physical result bundles
remain separate evidence and are never synthesized by `make check`.

The final C6 command is:

```sh
make c6-release-candidate
```

It regenerates the ROM, runs C4/C5/C6 ABI and focused HDL boundaries, boots
C6 through both local and N4 consoles, executes A:/B:, sequential read,
diagnostics, raw-key and N4-block utilities, warm boot and write/erase, runs a
64-cycle read/write/reconnect soak, then produces and independently reproduces
the complete package.

Prepare the distinct C7 programmer/bench bundle with:

```sh
make c7-bench-candidate
```

This does not promote C7 physically. It regenerates and checks the exact ROM,
pins its manifest and D15/D16 order, packages the matching CP/M/V16/media set,
and leaves one operator-guided `c7-raw` run on CS00015.

Important focused commands are:

```sh
make network-rom-extended-local-cosim-check
make network-rom-extended-cosim-check
make network-rom-long-soak-check
make distribution-check distribution-cosim-check
make native-services-check
make utility-catalogue-check development-tool-audit-check
make external-software-audit-check
make compiler-comparison-check
make physical-acceptance-check
make physical-performance-check
make physical-closure-check
make vidtest-cosim-check
make display-acceptance-check
make physical-promotion-check
make history-cosim-check panel-cosim-check
```

## Generated outputs

The normal build creates the frozen RAM-BIOS and C4 systems, native and C5/C6
systems/fastboot stages, seven declarative media profiles and their reports, and
ABI-specific boot manifests. The C6/C7-specific files include:

```text
out/cpm-plus-juku-network-rom-extended-native-system.bin
out/cpm-plus-juku-network-rom-extended-native-fastboot-v16.bin
out/cpm-plus-juku-c6-recovery.img
out/cpm-plus-juku-c6-manifest.json
out/cpm-plus-3.1-juku-c6-simulator/
out/cpm-plus-3.1-juku-c6-simulator.tar
out/cpm-plus-3.1-juku-c6-simulator.tar.sha256
out/cpm-plus-juku-c7-manifest.json
out/cpm-plus-3.1-juku-c7-modified-raw-bench/
out/cpm-plus-3.1-juku-c7-modified-raw-bench.tar
out/cpm-plus-3.1-juku-c7-modified-raw-bench.tar.sha256
```

The release directory contains the combined 16 KiB ROM, exact low D15 and high
D16 8 KiB halves, matching CP/M system/bootstrap, immutable C4 fallback slot,
A:/B: media, license/notice, build manifest, complete fixed ABI-vector map,
RAM/ROM placement, and all file hashes. Two independently built tar archives
must be byte-identical.

## System behavior

- Reset-latched S21 bit 0 selects immediate network boot or a concealed local
  `N` recovery wait.
- Bits 2:1 select 40x24, 53x24, 64x20, or MODX-compatible 80x24.
- Bits 4:3 select English, Estonian, CP866 Russian, or English/user-remap.
- The Creep-derived 5x7 policy leaves a separator column for text while its
  CP437 UI subset joins with five edge pixels for continuous pseudographics.
- Local display and keyboard are authoritative. N4 is optional, negotiated,
  duplicate-safe, and recoverable after host replacement.
- NetDisk uses independent per-drive eight-record read-ahead. Writes are
  synchronous write-through and invalidate cache before their first attempt.
- A: defaults read-only with explicit copy/snapshot/write-through modes; B:
  remains read-only and uses native Juku cylinder/head geometry.
- `VER`, `STATUS`, `DIAG`, `HIST`, `PANEL`, `KEYTEST`, `VIDTEST`, `KEYRAW`, `SOAK`,
  and `N4BULK` provide bounded target and machine-readable observability.
- Full, development, and demo media retain one command across CCP reloads;
  `!!` repeats it and `HIST [CLEAR]` inspects or clears it. Recovery media keep
  the exact unmodified DRI CCP.
- `PANEL` is a compact 80x24 status front end for the shared JNS1 record. It
  uses the exact-C6 connected CP437 border where the locale permits, falls
  back to an ASCII frame for Estonian, and returns on any key; other video
  modes receive a safe explanatory message.

The immutable C5/C6 loaded-system baseline measures 10/0/1 requests for
boot/first `DIR`/`TYPE`. The current post-C6 system retains three measured hot
directory records and improves that to 8/0/1; B: login/first `DIR` is 4/0.
The visible `TYPE` delay is dominated by framebuffer output and paging, not
disk serialization. Write-back caching, cryptographic authentication, and
production baud rates above 19,200 are intentionally outside C6 until a
measured design justifies their cost and failure semantics.

## Physical use

The package's exact C6 D15-low and D16-high halves are fitted in CS00015. On
2026-08-18 they passed built-in programmer verification, repeated automatic
19,200-baud V16 cold boots, local keyboard and ROM sound, A:/B:, diagnostics,
warm boot, writes, soak, and live host replacement. A working display is still
needed to observe the selected geometry, glyphs, pseudographics, and blinking
cursor physically. See
[`docs/cs00015-c6-blind-qualification-20260818.md`](docs/cs00015-c6-blind-qualification-20260818.md).
C5 and the stock-ROM/RAM-BIOS path remain recoverable baselines.

The newer network-loaded system does not require another EPROM burn. Its full,
development, and controlled M4 runs passed on CS00015 on 2026-08-19, and the
independent blind closure accepts the retained evidence. Physical promotion
now requires only the four-mode analog display observation. The results and
retained-evidence contract are in
[`docs/cs00015-post-c6-acceptance-20260819.md`](docs/cs00015-post-c6-acceptance-20260819.md)
and
[`docs/cpm3-physical-acceptance.md`](docs/cpm3-physical-acceptance.md).

The authoritative current documents are:

- [`docs/cpm-plus-feature-plan.md`](docs/cpm-plus-feature-plan.md)
- [`docs/network-first-rom-plan.md`](docs/network-first-rom-plan.md)
- [`docs/plan-completion-audit.md`](docs/plan-completion-audit.md)
- [`docs/c9-future-rom-policy.md`](docs/c9-future-rom-policy.md)
- [`docs/cpm-plus-31-c6-simulator.md`](docs/cpm-plus-31-c6-simulator.md)
- [`docs/distribution-profiles.md`](docs/distribution-profiles.md)
- [`docs/project-utilities.md`](docs/project-utilities.md)
- [`docs/cpm3-development-tools.md`](docs/cpm3-development-tools.md)
- [`docs/external-software-audit.md`](docs/external-software-audit.md)
- [`docs/cpm3-native-services.md`](docs/cpm3-native-services.md)
- [`docs/cpm3-pip-warm-boot-fix.md`](docs/cpm3-pip-warm-boot-fix.md)
- [`docs/cpm3-physical-acceptance.md`](docs/cpm3-physical-acceptance.md)
- [`docs/cs00015-post-c6-acceptance-20260819.md`](docs/cs00015-post-c6-acceptance-20260819.md)
- [`docs/cpm3-video-acceptance.md`](docs/cpm3-video-acceptance.md)
- [`docs/netdisk-performance.md`](docs/netdisk-performance.md)
