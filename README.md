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
fastboot at 19,200/8N1. The system then owns RAM and establishes a fresh
19,200/8O1 NetDisk-v3 session. Its A: volume contains `CCP.COM`, `DIAG.COM`,
and `README.TXT`.

The baseline is simulator-qualified through all of the following in one test:

- direct Ekta4402/V15 boot with zero stock Janet frames;
- the CP/M Plus banner and `A>` prompt;
- NetDisk-v3 `DIR`;
- loading `DIAG.COM` and passing `DIAG CPU`;
- all-RAM memory mode, fully masked PIC, and 8O1 USART state.

It is not yet qualified on physical Juku hardware. The adapter intentionally
retains the proven CP/M-compatible hardware-call shape until a native CP/M 3
implementation matches this baseline.

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
out/cpm-plus-juku.img              host-backed A: volume
```

`prebuilt/` contains byte-for-byte reference copies. `make check` first proves
that a fresh build matches them. Current SHA-256 values are:

- system: `f983ca17c7382048afb61b7e02afe29bfa1f86bedc3fde22ac1d2cba5f20f43d`;
- fastboot: `be2393e02732c9d24a8dd2b95b5ba1a313d45b17d64bd7dcdf83901b181c93ce`;
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

## Roadmap

1. Preserve the simulator-proven compatibility adapter as the reference.
2. Verify A: and native-geometry B: traffic, writes, warm boot, and reconnect
   recovery under CP/M Plus.
3. Implement a native CP/M 3 Juku hardware module and compare it against the
   reference before reclaiming the adapter/workspace gap for a larger TPA.
4. Add build identity utilities and shared ROM diagnostics where useful.
5. Qualify the direct boot and sustained NetDisk-v3 session on CS00015 before
   changing the CP/Mish physical baseline.
