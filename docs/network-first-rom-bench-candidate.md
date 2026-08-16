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
the ROM builder, and writes this self-describing directory:

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

## Fixed artifact hashes

| artifact | bytes | SHA-256 |
| --- | ---: | --- |
| combined ROM | 16,384 | `84488717b335039c12e87a9055c0a4950925fa17a556283e2dbfb86e8c07e900` |
| D15 low half | 8,192 | `1eaf3410849aa967b38f5b74c3db48c1f0ab5684f888998ee6575fd98c1a8534` |
| D16 high half | 8,192 | `f15b1b029edd845e0aa7622d61e9b84740957dce1f38a75867cedccef54494ac` |
| CP/M Plus ROM system | 18,432 | `74f2089bc85ef18fe90bb5868570e177037f55311f88484f27181425a7920ab1` |
| V15 fastboot payload | 7,699 | `0411ff682e7356d33073309b284bde33d627ea6c7769fdb1538d99c2c589bf4a` |
| network disk A | 409,600 | `bc14a67a441ad8c24b7574ee5e290866b058a6fe5d04c05b462b8d2b3abc3100` |

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

Promotion requires the physical matrix in
[`network-first-rom-plan.md`](network-first-rom-plan.md): repeated cold and
warm boots, prompt and timing, `DIR`, sequential read, `DIAG`, erase/write,
keyboard, compact display and blinking cursor, host-loss recovery, and a later
server reconnection without manual reset. Record board identity and programmer
verification hashes. A failure keeps C1 unpromoted and must be reproduced in
simulation before C2 is made.
