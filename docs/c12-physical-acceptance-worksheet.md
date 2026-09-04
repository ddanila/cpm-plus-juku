# JukuNet C12 programming and physical acceptance worksheet

Status: **SIMULATOR/HOST QUALIFIED; PHYSICAL PROGRAMMING NOT YET AUTHORIZED;
MANIFEST-BOUND ACCEPTANCE INPUTS READY**

C12 keeps C11's deterministic checkerboard, complete-raster clear, passive
session recovery, memory map, and 39,680-byte TPA. It adds ABI 1.5 runtime
video-mode and character-bank control. This worksheet prepares the exact burn
and evidence path, but does not itself authorize programming. Record an
explicit programming decision before writing either device.

## Frozen candidate inputs

Program D15 first as the low 8 KiB half and D16 second as the high 8 KiB half.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| combined C12 ROM | 16,384 | `724f672657390882f10c19588778527bd0b46848616ccf4ec348502dbb36e18b` |
| D15 low half | 8,192 | `b95eb5b0842d501ee602d82a7907b1cf4baf3e1b2cd74f73ef553eac60faf9de` |
| D16 high half | 8,192 | `45193e069ee3dca7a0abf98a20a563959c2a760e9eca828659d69a76420fe9b4` |
| C12 CP/M system | 23,040 | `74abab89c14e8429eec943c8b7c77ad33675cbf411fde5190d4657a3d28bdb79` |
| C12 Fastboot V16 | 512 | `51788bc93dac1e03a541239eb7f2837e3e03ef2519c3703aa052fe15b248f202` |
| C12 full A: image | 409,600 | `56e0db2f203bd813e609298b5ef1ff01177c97dbb386d894b38251580a1c1fc9` |

- D15 source: `juku-network-rom-abi1.5-c12-d15.bin`.
- D16 source: `juku-network-rom-abi1.5-c12-d16.bin`.
- Combined reference: `juku-network-rom-abi1.5-c12.bin`.
- Boot binding: `out/cpm-plus-juku-c12-manifest.json`.
- [ ] Recheck every hash before programming.
- [ ] Confirm D15 followed by D16 reconstructs the combined image exactly.
- [ ] Keep the working C11 pair labelled for immediate rollback.

## Programmer and installation record

Use the proved 28C64 device selection and physical arrangement. One complete
writer blank scan before a write and the writer's complete built-in verify
afterward are sufficient; no independent reread is required.

| Field | D15 candidate | D16 candidate |
| --- | --- | --- |
| complete device marking | | |
| blank scan | pass / fail | pass / fail |
| write and built-in verify | pass / fail | pass / fail |
| writer checksum/CRC | | |

- [ ] An explicit burn decision is recorded below.
- [ ] CS00000 is powered off before either device is inserted or removed.
- [ ] D15/D16 order, pin 1, seating, and bent pins are checked.
- [ ] S21 is set to raw `0Eh`: 80x24 and Estonian default.

Stop after any interrupted, inconclusive, or failed writer operation. Erase,
blank-check, and repeat the complete write; do not install a partly verified
device.

## Manifest-bound physical runs

Build the exact manifest and dry-run all profiles before touching the machine:

```sh
make c12-check physical-acceptance-check
python3 tools/physical_acceptance.py run /dev/ttyUSB0 \
  --profile c12-cold --manifest out/cpm-plus-juku-c12-manifest.json \
  --board CS00000 --output out/physical-CS00000-c12-cold --dry-run
python3 tools/physical_acceptance.py run /dev/ttyUSB0 \
  --profile c12-runtime --manifest out/cpm-plus-juku-c12-manifest.json \
  --board CS00000 --output out/physical-CS00000-c12-runtime --dry-run
python3 tools/physical_acceptance.py run /dev/ttyUSB0 \
  --profile c12-full --manifest out/cpm-plus-juku-c12-manifest.json \
  --board CS00000 --output out/physical-CS00000-c12-full --dry-run
```

After installation, run those commands again without `--dry-run`, using the
actual stable serial path. Each profile snapshots the ROM metadata, system,
Fastboot, A:/B: media, host executable, runner, and workload before opening the
serial device. Audit every retained result:

```sh
python3 tools/physical_acceptance.py audit out/physical-CS00000-c12-cold
python3 tools/physical_acceptance.py audit out/physical-CS00000-c12-runtime
python3 tools/physical_acceptance.py audit out/physical-CS00000-c12-full
```

The profiles prove complementary boundaries:

- `c12-cold`: checked `JB/12` recovery, automatic boot, ABI 1.5 state,
  diagnostics, POF release, and the S21 `0Eh` default;
- `c12-runtime`: attended exact VIDTEST pages for 40x24/English,
  53x24/Estonian, 64x20/Russian, and 80x24/user-remap, covering every geometry
  and font bank, followed by warm-boot preservation and default restoration;
- `c12-full`: A:/B:, private write/read/erase, version/date, diagnostics,
  runtime override, warm boot, and default restoration.

For every VIDTEST page, inspect the whole raster, border continuity, sample
glyphs, cursor, and absence of a retained bottom line before pressing Return
on the Juku keyboard and confirming the checkpoint at the host.

## Recovery and power-cycle checks

- [ ] A host started after C12 is waiting discovers `JB/12` without RESET.
- [ ] Replacing the host during CP/M finds the next checked NetDisk request.
- [ ] RESET during NetDisk produces a fresh C12 beacon and complete V16 reboot.
- [ ] A cold power cycle restores S21 `0Eh`, regardless of the prior override.
- [ ] The deterministic checkerboard is stable before every cold boot.
- [ ] No UART error, disk retry, unexpected recovery reason, or raster residue
      appears in any accepted run.

## Decision

If any switch loses sync, produces the wrong geometry/glyphs, erases a
persistent remap unexpectedly, leaves raster residue, or regresses recovery or
disk service, power off and refit the labelled C11 pair. Retain the complete
failed-session evidence.

| Decision/result | Mark |
| --- | --- |
| explicit C12 programming authorized | |
| D15/D16 built-in verification passed | |
| all three physical profiles and audits passed | |
| cold power-cycle default passed | |
| failure observed; C11 rollback refitted | |
| physical promotion approved | |

Operator: ____________________  Date/time: ____________________

Reviewer: ____________________  Date/time: ____________________
