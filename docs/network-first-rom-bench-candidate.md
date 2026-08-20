# Network-first ROM CS00015 bench candidate C4

Status: **BLIND QUALIFICATION PASSED; LOCAL CONSOLE CHECK PENDING; NOT YET PROMOTED**

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
`DIR`, sequential read, `DIAG CPU`, explicit `WBOOT`, erase/write, and
post-warm-boot operation on CS00015. Three independent cold boots reached the
first disk request in 6.068--6.070 seconds. A replacement host then restored
NetDisk and N4, ran `DIR`, and returned to `A>` without RESET. The only
remaining candidate observation is the exact resident display, cursor, and
local keyboard with a monitor attached.
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

## Historical qualification boundary

C4 and its Fastboot V15 transport are preserved historical artifacts, not a
current deployment path. The physical commands which produced the retained
2026-08-17 evidence used the then-current Python host and are preserved in Git
history and in the result directories under `out/`; they are intentionally not
offered as runnable commands here.

The production host migration admits the current C8/Fastboot V16 path. It does
not carry the obsolete V1--V15 serving implementation into portable C merely
to repeat an already completed candidate experiment. The old
`physical_qualification.py` recorder and its live `run`/`resume` entry points
were therefore retired with the Python production host.

Use [`cpm3-physical-acceptance.md`](cpm3-physical-acceptance.md) for every new
physical run. That manifest-bound runner launches the native C `jukuhost`,
retains its text log and CRC-protected capture, derives JSON acceptance evidence
after shutdown, and covers the current ROM/system/media identities. The C4
package and this document remain useful for provenance and comparison only.
