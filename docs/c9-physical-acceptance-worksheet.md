# JukuNet C9 physical acceptance worksheet

Status: **PREPARED; NO EPROM PROGRAMMING OR PHYSICAL PROMOTION AUTHORIZED**

Use this sheet only after an explicit decision to begin the C9 physical gate.
Completing the desk/preflight fields does not itself authorize a write. C8 is
the fitted and qualified rollback until every applicable result below passes.

## Frozen candidate evidence

The authoritative clean-room command was `make c9-simulator-candidate` on
2026-08-26. Both isolated source trees were clean before and after the build.
The complete passing log is
`out/c9-simulator-candidate-cleanroom-20260826.log`, 61,487 bytes, SHA-256
`5c81086f7d5bd22365faf42b78b5035259abf7e73366e173f037f1b938619ddb`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| combined C9 ROM | 16,384 | `352417fafcf1ceaef40b8d39916acdaee6de03d914eafe2b54185ccbabe35530` |
| D15 low half | 8,192 | `b18e96e8f4cc88c7436e457b63b564ad42e1bf55f3e997f272301096c463593e` |
| D16 high half | 8,192 | `6f9bdf53bcf7ee919224305bcaf135c2d0076779218f49a2aed5395dc6baf932` |
| C9 CP/M system | 18,432 | `ec06111e197a75a628d6a8c917542d0afa68c66ac26d14d39b9ef13aa0b38225` |
| Fastboot V16 | 7,811 | `cae64165a04837d309f7b02c88a25754186ec333166ab5dd725d6e178088761b` |
| C9 full A: volume | 409,600 | `26f640ea6f0f7237910731f56ae006944d9102d51bfe5d217c4025a78d9fed10` |
| C9 boot manifest | 4,465 | `892eca0928a52705ede1399e8cee2567c48c022478ab0ae285bd09fcf2b7384f` |
| non-physical package tar | 2,652,160 | `43b03802e156dba0492c860fe27a9fc1aec1672cf5dc0afab82176fbd243eb75` |

Before a physical session:

- [ ] `(cd out && sha256sum -c cpm-plus-3.1-juku-c9-bounded-host-simulator.tar.sha256)`
- [ ] Recheck each loose D15/D16 file against the table above.
- [ ] Confirm that D15 followed by D16 exactly reconstructs the combined ROM.
- [ ] Record the passing clean-room log hash: ______________________________
- [ ] Record explicit programming authorization, person and time:
      ______________________________________________________________________

## Hardware and rollback identity

| Field | Record |
| --- | --- |
| board identity and revision | |
| board serial/owner label | |
| raw S21 byte | |
| host machine and OS | |
| serial adapter and device path | |
| power supply | |
| fitted C8 D15 label/storage location | |
| fitted C8 D16 label/storage location | |
| board/socket orientation photographs | |

- [ ] Board is powered off and disconnected before removing or inserting ROMs.
- [ ] The known-good C8 pair is individually labelled D15-low/D16-high and
      stored as a pair; it will not be erased or reused for C9.
- [ ] A rollback can be performed by power-off and refitting that exact pair.

## Programmer preflight

The devices currently in scope are marked `M2764AFI`. Select an algorithm that
explicitly supports the exact device/compatible programming specification.
Do not derive programming voltage or pulse settings from this worksheet. Use
the exact device datasheet and the programmer's supported-device table. Apply
programming voltage only in the programmer, never through the Juku socket.

| Field | D15 candidate | D16 candidate |
| --- | --- | --- |
| physical chip ID/marking | | |
| programmer/software version | | |
| selected device algorithm | | |
| DIP/jumper setting and photo | | |
| ZIF pin-1 orientation checked | | |
| empty-ZIF read VCC | | |
| empty-ZIF program VCC | | |
| empty-ZIF VPP | | |
| values checked against exact specification | pass / fail | pass / fail |
| UV erase duration/cycle | | |
| one complete blank scan | pass / fail | pass / fail |

One complete blank scan is sufficient before each write attempt. If power is
lost or the writer does not reach its programming command, record the attempt
as interrupted; do not infer whether bytes changed. Blank-check or erase again
before retrying.

## Programming record

### D15 — low 8 KiB

- Source: `juku-network-rom-abi1.4-c9-d15.bin`
- Expected SHA-256:
  `b18e96e8f4cc88c7436e457b63b564ad42e1bf55f3e997f272301096c463593e`
- Attempt/time: __________________________
- Writer result: _________________________
- Built-in verify, all 8,192 bytes: pass / fail
- Writer checksum/CRC, if available: __________________________
- Notes: _________________________________________________________________

### D16 — high 8 KiB

- Source: `juku-network-rom-abi1.4-c9-d16.bin`
- Expected SHA-256:
  `6f9bdf53bcf7ee919224305bcaf135c2d0076779218f49a2aed5395dc6baf932`
- Attempt/time: __________________________
- Writer result: _________________________
- Built-in verify, all 8,192 bytes: pass / fail
- Writer checksum/CRC, if available: __________________________
- Notes: _________________________________________________________________

Stop on any blank-check, programming or verify error. Preserve the log and do
not install a partly verified pair.

## Installation

- [ ] Board power is off and discharged.
- [ ] D15 contains the low half and is installed in socket D15.
- [ ] D16 contains the high half and is installed in socket D16.
- [ ] Both pin-1/notch orientations match the socket/board photograph.
- [ ] No bent pins; both devices are fully seated; UV windows are covered.
- [ ] S21 raw value is recorded. C9 reserves bit 0 and must boot identically
      for either value; bits 4:1 retain the selected locale/video mode.

## Cold-boot and command transcript

Retain the exact host command, host log, raw capture, N4 transcript and a copy
of the manifest. Console acceptance is through `jukuhost --console-pty`; a
simulator CONOUT hook is not evidence.

| Evidence | Path / result |
| --- | --- |
| session directory | |
| exact `jukuhost` command | |
| host executable SHA-256 | |
| private writable A: SHA-256 before run | |
| private writable A: SHA-256 after run | |
| read-only B: SHA-256 | |
| raw capture | |
| decoded requests JSONL | |
| complete N4 transcript | |

- [ ] Cold boot reaches the complete CP/M banner and `A>` automatically.
- [ ] `STATUS` reports `Juku Status 1.4`, ROM ABI `01.04`, TPA
      `0100-9BFF`, cold marker `00`, POST/ROM/disk status zero, state flags
      `0F`, and failure reason `none`.
- [ ] `VER` and `DATE` return normally.
- [ ] `DIAG ALL` passes CPU, RAM, checksum, D57, D11, ROM ABI,
      video/console and keyboard/S21 checks.
- [ ] `DIR` on A: and B: succeeds.
- [ ] A private writable A: copy passes `PIP C9COPY.TXT=README.TXT`, the copy
      is readable, and `ERA C9COPY.TXT` removes it.
- [ ] `WBOOT` returns to `A>` and `STATUS` reports warm marker `01`.
- [ ] A long N4 output and the manifest-bound recovery-volume `SOAK` complete
      with zero clean-path transport errors.
- [ ] Normal sound is heard.

## Host loss and replacement without RESET

- [ ] Stop the first host while CP/M remains at `A>`; do not press RESET.
- [ ] Leave enough time for at least one bounded N4 input poll to observe loss.
- [ ] Start a replacement host in resume-disk mode and recover a prompt.
- [ ] `VER` succeeds through the replacement host.
- [ ] On a fresh cold session, `STATUS` reports last failure `02`, reconnects
      `01`, flags `1F`, last operation `20`, and `receive timeout`. If a count
      differs because of additional deliberate replacements, explain it below.
- [ ] A:/B:, write/readback/erase, warm boot and long output still pass.

Replacement notes: ________________________________________________________

## Local console and adverse-host boundary

Complete these only on a machine with a usable display path.

- [ ] Compare local and N4 boot/command transcripts character for character.
- [ ] With the host absent, slow or sending malformed replies, local output
      remains responsive and no local-console freeze occurs.
- [ ] Reconnecting a valid host restores N4 operation without RESET.
- [ ] Selected video mode, character bank, keyboard and cursor match the
      retained C8 behavior for the recorded S21 byte.

## Decision

| Result | Mark |
| --- | --- |
| all applicable gates pass; retain C9 for further observation | |
| failure observed; power off and refit the labelled C8 pair | |
| physical promotion separately approved | |

Operator: ____________________  Date/time: ____________________

Reviewer: ____________________  Date/time: ____________________

Promotion notes and evidence hashes: ______________________________________

Until the final promotion line is explicitly approved, the result is physical
test evidence only and C8 remains the rollback baseline.
