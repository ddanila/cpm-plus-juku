# JukuNet C10 programming and physical acceptance worksheet

Status: **DESK-QUALIFIED; ROM PAIR READY TO PROGRAM; PHYSICAL ACCEPTANCE PENDING**

C10 is the C9 carry-forward with the CS00000 video-enable defect corrected.
C9 wrote PPI0 control `82h, 0Fh` and left Port C at `81h`, which asserted
PC7/POF and suppressed the picture. C10 performs the stock-compatible ordered
writes `82h, 0Fh, 0Eh`, verifies PC7 low, and enters runtime with Port C `01h`.
The exact C9 CP/M system and Fastboot V16 payloads are retained.

## Frozen programming inputs

Program the halves in this order; D15 is the low 8 KiB and D16 is the high
8 KiB.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| combined C10 ROM | 16,384 | `fbf9baaad9027a5335e3549da3a396eb999bbaae1a1f3f5f6e2f36798848a6bc` |
| D15 low half | 8,192 | `a8e54e8ffac5b2654ba23f3dbff8acee17dd857d05f3654fa0fa9d23fdd58c7c` |
| D16 high half | 8,192 | `e4c423a0d3bf2dea6ff69170787f67d6c481a07b246727625906293e5aea618e` |

- D15 source: `juku-network-rom-abi1.4-c10-d15.bin`
- D16 source: `juku-network-rom-abi1.4-c10-d16.bin`
- Combined reference: `juku-network-rom-abi1.4-c10.bin`
- [ ] Recheck all three SHA-256 values before programming.
- [ ] Confirm D15 followed by D16 reconstructs the combined image exactly.
- [ ] Keep the known-good EKTA3.7 pair labelled and available for rollback.

## Programmer preflight

The intended devices are the same supported 28C64 parts used on this setup
for C9. Record the complete chip marking and select that exact supported-device
algorithm in the writer. Do not infer programming voltage, pulse parameters,
or DIP/jumper settings from this worksheet.

| Field | D15 candidate | D16 candidate |
| --- | --- | --- |
| complete physical marking | | |
| programmer/software version | | |
| selected device algorithm | | |
| DIP/jumper setting and photo | | |
| ZIF pin-1 orientation checked | | |
| one complete writer blank scan | pass / fail | pass / fail |

One complete writer blank scan is sufficient before each write attempt. If a
write is interrupted before a conclusive built-in verify, erase/blank-check the
device again before retrying.

## Programming record

### D15 — low 8 KiB

- Expected SHA-256:
  `a8e54e8ffac5b2654ba23f3dbff8acee17dd857d05f3654fa0fa9d23fdd58c7c`
- Attempt/time: __________________________
- Writer result: _________________________
- Built-in verify, all 8,192 bytes: pass / fail
- Writer checksum/CRC, if available: __________________________

### D16 — high 8 KiB

- Expected SHA-256:
  `e4c423a0d3bf2dea6ff69170787f67d6c481a07b246727625906293e5aea618e`
- Attempt/time: __________________________
- Writer result: _________________________
- Built-in verify, all 8,192 bytes: pass / fail
- Writer checksum/CRC, if available: __________________________

Stop on any blank-check, programming, or verify error. Do not install a partly
verified pair.

## Installation

- [ ] CS00000 is powered off and discharged before inserting the ROMs.
- [ ] D15 contains the low half and is fitted in socket D15.
- [ ] D16 contains the high half and is fitted in socket D16.
- [ ] Both pin-1/notch orientations match the board/socket orientation.
- [ ] No bent pins; both devices are fully seated.
- [ ] The exact S21 setting that worked with EKTA3.7 is retained and recorded.

## Required first physical gate

Retain the host log, raw capture, decoded request trace, N4 transcript, and
manifest snapshot for each run. The prepared profiles are:

- `c10-cold`: automatic boot, `STATUS 1.5`, `DIAG 0.7 ALL`, Port C/POF.
- `c10-display`: attended `VIDTEST` local-picture check.
- `c10-full`: A:/B:, read/write/erase, date, diagnostics, and warm boot.

Run them through `tools/physical_acceptance.py` with
`out/cpm-plus-juku-c10-manifest.json`; the harness rejects a mismatched ROM,
system, Fastboot, or volume before opening the serial device.

- [ ] Cold boot reaches the CP/M Plus banner and `A>` automatically.
- [ ] Local video is present without a helper program or manual Port C write.
- [ ] `STATUS` reports `Juku Status 1.5`, ABI `01.04`, TPA `0100-9BFF`,
      `PPI0 Port C: 01`, and `POF: released (picture enabled)`.
- [ ] `DIAG ALL` reports `Juku Diagnostics 0.7` and
      `Video enable/console state: PASS` with every other item passing.
- [ ] `VIDTEST` is visibly correct in the retained S21 video/locale mode.
- [ ] `DIR` works on A: and B:; `PIP C10COPY.TXT=README.TXT`, readback, and
      erase all pass on the private writable A: copy.
- [ ] `VER`, `DATE`, and `WBOOT` return normally; post-warm-boot Port C remains
      `01h` and POF remains released.
- [ ] Power-cycle repeat produces the same result.

## Rollback and decision

If local video is absent, diagnostics fail, or any disk/console behavior
regresses, power off and refit the labelled EKTA3.7 pair. Preserve the complete
failed-session evidence; do not patch Port C live and count that as C10
acceptance.

| Result | Mark |
| --- | --- |
| C10 physical gate passed; retain for observation | |
| failure observed; EKTA3.7 rollback refitted | |
| physical promotion separately approved | |

Operator: ____________________  Date/time: ____________________

Reviewer: ____________________  Date/time: ____________________
