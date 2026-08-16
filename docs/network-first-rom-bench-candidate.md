# Network-first ROM CS00015 bench candidate C4

Status: **READY FOR CONTROLLED CS00015 QUALIFICATION; NOT YET PROMOTED**

Candidate: `network-first-abi1-cs00015-c4`

Date: **2026-08-17**

This is the fourth named physical candidate. C1 was never burned: a
stock-ROM/manual-resume run exposed its malformed font first. C2 corrected the
source extraction. C3 adopted the MIT-licensed Creep adaptation and 512-poll
cursor, and its ROM pair was burned into CS00015. That first blind run proved
automatic reset, V15 loading, resident output, and NetDisk, but its matching
CP/M binding could enter the resident ROM's blocking local `CONIN` before a
later N4 byte arrived. C4 freezes the corrected binding: it checks resident
`CONSTAT` and continues polling N4 while the local keyboard is idle.

C4 changes no EPROM bytes. Its D15 and D16 hashes are identical to C3, so the
already-installed chips require no rewrite. Only the downloaded CP/M system
and V15 bundle change. The corrected runtime physically completed remote
`DIR`, `DIAG CPU`, explicit `WBOOT`, and a second `DIR` on CS00015 with zero
bootstrap/disk retry; the remaining display, local-keyboard, write, repeated
cold-boot, and live reconnect matrix is still pending.
The exact failure evidence, timing, commands, and simulator reproduction are
preserved in
[`cs00015-c4-blind-qualification-20260817.md`](cs00015-c4-blind-qualification-20260817.md).

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
out/network-first-abi1-cs00015-c4/
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
whose metadata is not exactly C4 and verifies that D15 followed by D16 equals
the combined 16 KiB ROM.

The structural portion was introduced by `8080-cosim` commit `fefe01cb` and
rerun for C3 in `b04aa388`. C4 keeps those exact production bytes and boots them through
`juku_top`/`vm80a` to the `C4h` marker,
then uses test-only dispatch around the unchanged resident bytes to prove the
framebuffer helper, shifted matrix input, serial ABI, and one CRC-checked
NetDisk-v3 reply copied as a complete 128-byte DMA record. Full CP/M commands,
recovery, exact cursor pixels, and soak remain covered by the C-model suite;
neither model replaces the physical matrix below.

## Fixed artifact hashes

| artifact | bytes | SHA-256 |
| --- | ---: | --- |
| combined ROM | 16,384 | `931218a654412e2f9b0776a81bd5369f0c22c1da45cada220a2b96bbe70854c0` |
| D15 low half | 8,192 | `3e8b9eb2f3752002821e6ec18dd59805108389c9d93aba40316bd2e18eb7684f` |
| D16 high half | 8,192 | `f15b1b029edd845e0aa7622d61e9b84740957dce1f38a75867cedccef54494ac` |
| CP/M Plus ROM system | 18,432 | `a0a98915ba570b6816eadb096f9d885514dca9987c2070c123552397b1adc80e` |
| V15 fastboot payload | 7,704 | `991eabf57360528c1a28fedab2013e94542348870aebd0de7ea8b60452765d3f` |
| network disk A | 409,600 | `b4402dc9be86fef9532e61fff491dc3b93dc0db40e68d575c89aab083160bec1` |

Program only `D15-low-8K.bin` into D15 and `D16-high-8K.bin` into D16. The
remaining files are matching host/runtime inputs, not EPROM images.

## Matching host invocation

After programming both halves and before switching CS00015 on:

```sh
cd ~/fun/cpm-plus-juku && ../8080-cosim/tools/janet_disk_server.py \
  /dev/ttyUSB0 out/network-first-abi1-cs00015-c4/cpm-plus-system.bin \
  out/network-first-abi1-cs00015-c4/network-disk.img \
  --fast-stage1 out/network-first-abi1-cs00015-c4/fastboot-v15.bin \
  --network-rom --disk-baud 19200 --disk-protocol 3 --writable \
  --timeout 86400
```

## Auditable physical session

Initialize a record before programming or powering the board:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py init \
  --output out/physical-CS00015-C4
```

This verifies every packaged hash and D15+D16 concatenation, captures both
repository commits, and writes a machine-readable session plus `CHECKLIST.md`.
Every `run` creates its own private writable copy of A:, so `ERA` and other
write tests cannot contaminate a later cold boot or the packaged reference
disk. Start each cold-boot attempt with:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py run \
  out/physical-CS00015-C4 /dev/ttyUSB0
```

The runner streams the normal server output to the console and a hash-locked
per-run `host.log`, while `boot.json` records the first valid disk-request
timing and exact system/fastboot identities. Stop it with Ctrl+C after the
local observation; power-cycle and repeat until at least three independent
cold boots have been captured. The runner owns the terminal signal and forwards
one SIGINT to an isolated server process; the server atomically replaces the
private A: copy, so an interrupted shutdown cannot truncate its last complete
state.

For a monitor-independent, auditable command suite, add `--console-smoke`:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py run \
  out/physical-CS00015-C4 /dev/ttyUSB0 --console-smoke
```

After printing the host-ready line, the runner waits for a physical reset or
power-on. It verifies the C4 banner and `A>`, deliberately delays the first
input so the target has entered its idle `CONIN` path, and runs `DIR`, paginated
`TYPE README.TXT`, `DIAG CPU`, `WBOOT`, `ERA README.TXT`, and a directory that
must no longer contain README. The server then stops cleanly. Raw N4 bytes,
their hash, decoded checks, host log, boot timing, artifact identities, and the
private writable volume are retained in that boot directory. Successful checks
update only the observations they directly prove; display, local keyboard, and
cursor remain pending.

For the server-loss test, stop the live host without resetting Juku. After the
target has entered its bounded retry path, attach a fresh server directly to
the running NetDisk session:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py resume \
  out/physical-CS00015-C4 /dev/ttyUSB0 --console-smoke
```

The underlying production CLI's `--resume-disk` mode reuses the most recent
cold boot's private A: but sends no bootstrap marker or system image. It waits
for the target's retried request at 19,200/8O1; prove
recovery by completing a later `DIR` without RESET. In console-smoke mode the
command is queued before the target reprobes, captured byte for byte, and the
replacement host stops cleanly after the returned prompt. Record only
observations actually made on CS00015 with `record --test name=pass`, add the two programmer
readback hashes, then run:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_qualification.py audit \
  out/physical-CS00015-C4
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
verification hashes. A failure keeps C4 unpromoted and must be reproduced in
simulation before another named candidate is made.
