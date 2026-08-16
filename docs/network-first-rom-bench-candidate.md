# Network-first ROM CS00015 bench candidate C1

Status: **READY TO BURN FOR CONTROLLED CS00015 QUALIFICATION; NOT YET PROMOTED**

Candidate: `network-first-abi1-cs00015-c1`

Date: **2026-08-16**

This is the first named physical candidate produced after the automatic boot,
resident-service, relink, and complete simulated recovery milestones. Its ROM
bytes are unchanged from the fully tested desk artifact; `8080-cosim` commit
`ac347cdb` changes the machine-readable gate from prohibited desk image to
CS00015 bench candidate.

## Reproducible package

From this repository, with sibling `8080-cosim` checked out:

```sh
make bench-candidate
```

That one command rebuilds and compares every checked-in CP/M artifact, checks
the ROM budget, runs the complete legacy/clean/recovery cosim matrix, verifies
the ROM builder, runs the focused structural-HDL gate, and writes this
self-describing directory:

```text
out/network-first-abi1-cs00015-c1/
  combined-rom.bin
  D15-low-8K.bin
  D16-high-8K.bin
  rom-metadata.json
  cpm-plus-system.bin
  fastboot-v15.bin
  network-disk.img
  manifest.json
```

The manifest records sizes, SHA-256 hashes, 19,200-baud protocol settings,
programmer order, memory map, and pending physical status. It rejects a ROM
whose metadata is not exactly C1 and verifies that D15 followed by D16 equals
the combined 16 KiB ROM.

The structural portion is fixed by `8080-cosim` commit `fefe01cb`. It boots
the exact production C1 bytes through `juku_top`/`vm80a` to the `C4h` marker,
then uses test-only dispatch around the unchanged resident bytes to prove the
framebuffer helper, shifted matrix input, serial ABI, and one CRC-checked
NetDisk-v3 reply copied as a complete 128-byte DMA record. Full CP/M commands,
recovery, exact cursor pixels, and soak remain covered by the C-model suite;
neither model replaces the physical matrix below.

## Fixed artifact hashes

| artifact | bytes | SHA-256 |
| --- | ---: | --- |
| combined ROM | 16,384 | `84488717b335039c12e87a9055c0a4950925fa17a556283e2dbfb86e8c07e900` |
| D15 low half | 8,192 | `1eaf3410849aa967b38f5b74c3db48c1f0ab5684f888998ee6575fd98c1a8534` |
| D16 high half | 8,192 | `f15b1b029edd845e0aa7622d61e9b84740957dce1f38a75867cedccef54494ac` |
| CP/M Plus ROM system | 18,432 | `74f2089bc85ef18fe90bb5868570e177037f55311f88484f27181425a7920ab1` |
| V15 fastboot payload | 7,699 | `0411ff682e7356d33073309b284bde33d627ea6c7769fdb1538d99c2c589bf4a` |
| network disk A | 409,600 | `b4402dc9be86fef9532e61fff491dc3b93dc0db40e68d575c89aab083160bec1` |

Program only `D15-low-8K.bin` into D15 and `D16-high-8K.bin` into D16. The
remaining files are matching host/runtime inputs, not EPROM images.

## Matching host invocation

After programming both halves and before switching CS00015 on:

```sh
cd ~/fun/cpm-plus-juku && ../8080-cosim/tools/janet_disk_server.py \
  /dev/ttyUSB0 out/network-first-abi1-cs00015-c1/cpm-plus-system.bin \
  out/network-first-abi1-cs00015-c1/network-disk.img \
  --fast-stage1 out/network-first-abi1-cs00015-c1/fastboot-v15.bin \
  --network-rom --disk-baud 19200 --disk-protocol 3 --writable \
  --timeout 86400
```

## Auditable physical session

Initialize a record before programming or powering the board:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py init \
  --output out/physical-CS00015-C1
```

This verifies every packaged hash and D15+D16 concatenation, captures both
repository commits, and writes a machine-readable session plus `CHECKLIST.md`.
Every `run` creates its own private writable copy of A:, so `ERA` and other
write tests cannot contaminate a later cold boot or the packaged reference
disk. Start each cold-boot attempt with:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py run \
  out/physical-CS00015-C1 /dev/ttyUSB0
```

The runner streams the normal server output to the console and a hash-locked
per-run `host.log`, while `boot.json` records the first valid disk-request
timing and exact system/fastboot identities. Stop it with Ctrl+C after the
local observation; power-cycle and repeat until at least three independent
cold boots have been captured. The runner owns the terminal signal and forwards
one SIGINT to an isolated server process; the server atomically replaces the
private A: copy, so an interrupted shutdown cannot truncate its last complete
state.

For the server-loss test, stop the live host without resetting Juku. After the
target has entered its bounded retry path, attach a fresh server directly to
the running NetDisk session:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py resume \
  out/physical-CS00015-C1 /dev/ttyUSB0
```

The underlying production CLI's `--resume-disk` mode reuses the most recent
cold boot's private A: but sends no bootstrap marker or system image. It waits
for the target's retried request at 19,200/8O1; prove
recovery by completing a later `DIR` without RESET. Record only observations
actually made on CS00015 with `record --test name=pass`, add the two programmer
readback hashes, then run:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py audit \
  out/physical-CS00015-C1
```

The audit refuses promotion unless both EPROM hashes match, at least three
identity-checked cold-boot timings exist, a resume run was captured, and every
required display, keyboard, command, write, warm-boot, and recovery observation
is explicitly marked as passed. It also locks the recorder and production host
source hashes at session initialization, so changing either implementation
mid-qualification invalidates the record. Live reattachment is implemented by
`8080-cosim` commit `8a3300e2`.

Promotion requires the physical matrix in
[`network-first-rom-plan.md`](network-first-rom-plan.md): repeated cold and
warm boots, prompt and timing, `DIR`, sequential read, `DIAG`, erase/write,
keyboard, compact display and blinking cursor, host-loss recovery, and a later
server reconnection without manual reset. Record board identity and programmer
verification hashes. A failure keeps C1 unpromoted and must be reproduced in
simulation before C2 is made.
