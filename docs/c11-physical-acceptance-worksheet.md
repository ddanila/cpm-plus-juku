# JukuNet C11 programming and physical acceptance worksheet

Status: **RASTER/SESSION-RECOVERY DESK-QUALIFIED; ROM PAIR READY TO PROGRAM; FOCUSED PHYSICAL ACCEPTANCE PENDING**

C11 keeps C10's proved PC7/POF video-enable fix and the exact C10 CP/M Plus
system, Fastboot V16 stage, and resident adapter. It changes two visible raster
details: the power-on picture is initialized as a deterministic 8x8
checkerboard before POF is released, and console initialization clears a safe
9,648-byte envelope covering every supported physical raster. This addresses
the random pixels in the power-on checkerboard and the retained bottom line in
mode 0 without changing the 9,600-byte text surface. The revised, still
unprogrammed C11 D15 also adds the checked 8O1 boot-discovery beacon used by
the production host's passive `--recover-session` state machine. The earlier
pre-recovery C11 D15 is superseded and must not be programmed.

## Frozen programming inputs

Program D15 first as the low 8 KiB half and D16 second as the high 8 KiB half.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| combined C11 ROM | 16,384 | `b93428bb33cd7e31c2d9b2b84aa07ea17edda76c9d53ab73b3cb8687e8d53dfd` |
| D15 low half | 8,192 | `a94e8fa2911fd3f7e715c6086d237b45fe630e71e8e14786bdcce435d99a8134` |
| D16 high half | 8,192 | `ac80ca047adeff842a911266ff1c054e30ac4628e925ea9fbb1be54e872b9581` |

- D15 source: `juku-network-rom-abi1.4-c11-d15.bin`
- D16 source: `juku-network-rom-abi1.4-c11-d16.bin`
- Combined reference: `juku-network-rom-abi1.4-c11.bin`
- [ ] Recheck all three SHA-256 values before programming.
- [ ] Confirm D15 followed by D16 reconstructs the combined image exactly.
- [ ] Keep the working C10 or EKTA3.7 pair labelled for rollback.

Superseded pre-recovery hashes (identification only; do not program): combined
`49af4137be8cab2a487ccec0ac264e964b75f6699ebea8baf0f1a29d1ce292dc`,
D15 `4040833d71fe9029d9cf5bc261b76b57edb87528d1d624e6b003fb2208bf2187`.
D16 is unchanged.

## Programmer record

Use the already proved 28C64 device selection, DIP/jumper arrangement, and
voltage arrangement for this exact setup. One writer blank scan before a write
and the writer's complete built-in verify afterward are sufficient.

| Field | D15 candidate | D16 candidate |
| --- | --- | --- |
| complete device marking | | |
| blank scan | pass / fail | pass / fail |
| write and built-in verify | pass / fail | pass / fail |
| writer checksum/CRC | | |

Do not install a device after an interrupted or inconclusive write. Erase it,
blank-check it, and repeat the complete write and verify.

## Installation

- [ ] CS00000 is powered off before inserting the ROMs.
- [ ] C11 D15 is fitted in D15 and C11 D16 in D16.
- [ ] Pin 1 orientation is correct; no pins are bent.
- [ ] The same known-working S21 setting is retained.

## Focused C11 visual gate

- [ ] On cold power-up, the picture appears without a live Port C patch.
- [ ] The pre-boot picture is a stable, regular 8x8 checkerboard across the
      complete visible raster, including the bottom scanline.
- [ ] No isolated or randomly changing pixels appear in that checkerboard.
- [ ] When CP/M reaches `A>`, no checkerboard line remains at the bottom.
- [ ] The bottom line remains clear after `VIDTEST`, its return to `A>`, a
      screen clear, `WBOOT`, and one further power cycle.

The startup checkerboard is intentional: it gives immediate evidence that
video timing, framebuffer RAM, and POF release are operating. Its deterministic
content, rather than a blank screen, is the expected result.

## Carry-forward workload gate

Retain the host log, raw serial capture, decoded trace, manifest snapshot, and
visual observations. The prepared profiles are:

- `c11-cold`: automatic boot, `STATUS 1.5`, `DIAG 0.7 ALL`, Port C/POF.
- `c11-display`: attended `VIDTEST` and bottom-line inspection.
- `c11-full`: A:/B:, write/read/erase, date, diagnostics, and warm boot.

Run them with `tools/physical_acceptance.py` and
`out/cpm-plus-juku-c11-manifest.json`. The harness checks the exact ROM, system,
Fastboot, and volume bindings before opening the serial device.

- [ ] Cold boot reaches the CP/M Plus banner and `A>` automatically.
- [ ] A host started after C11 is already waiting discovers the periodic
      beacon and boots without RESET.
- [ ] A replacement host started while CP/M is already running detects the
      next checked NetDisk request without `--resume-disk`.
- [ ] One attended RESET during NetDisk is detected from the fresh C11 beacon,
      followed by a complete automatic V16 reboot.
- [ ] `STATUS` reports ABI `01.04`, TPA `0100-9BFF`, Port C `01`, POF released,
      and POST `00`.
- [ ] `DIAG ALL` identifies C11 and all checks pass.
- [ ] A: and B: access, private A: write/read/erase, `DATE`, and `WBOOT` pass.
- [ ] After warm boot, Port C remains `01`, POF remains released, and no raster
      residue is visible.

## Decision

If the checkerboard is irregular, a bottom line remains, local video is lost,
or any carry-forward behavior regresses, power off and refit the labelled
working ROM pair. Preserve the complete failed-session evidence.

| Result | Mark |
| --- | --- |
| C11 focused physical gate passed | |
| failure observed; working ROM pair refitted | |
| physical promotion separately approved | |

Operator: ____________________  Date/time: ____________________

Reviewer: ____________________  Date/time: ____________________
