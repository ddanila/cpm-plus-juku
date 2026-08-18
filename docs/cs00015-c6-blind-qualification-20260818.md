# CS00015 C6 blind qualification — 2026-08-18

Status: **BLIND PHYSICAL MATRIX PASSED; DISPLAY/CURSOR OBSERVATION PENDING**

## Scope

CS00015 ran the packaged JukuNet C6 / ROM ABI 1.2 pair with S21 set to
`00000011` (`03h`). The external display was unavailable, so this session
qualifies programming identity, automatic Fastboot V16, CP/M and NetDisk,
local keyboard input observed through N4, diagnostics, sound, writes, warm
boot, soak, and live host replacement. It does not claim physical framebuffer,
font, geometry, or blinking-cursor observation.

## Installed and verified artifacts

| artifact | SHA-256 | physical result |
| --- | --- | --- |
| combined C6 ROM | `0487d5150f9b662a193b3f031aadd90002ee232477d355d3877a757a247c2f09` | D15/D16 pair fitted in CS00015 |
| D15 `JukuNet C6 Low` | `8cf403663ed860f7e5ab56f382e42bddf6e8951e478e89313074c03ab31f2750` | 8,192-byte built-in verify passed |
| D16 `JukuNet C6 High` | `3a60561d0e5f8a8d8e9a1f1c355e503db5daeadec174b45380de732690c9bdf1` | 8,192-byte built-in verify passed |
| C6 CP/M system | `6dbe02421fb88cc964b9536f0f5c51f0e31a652a6017cb4a8d3178394849b70b` | booted to `A>` |
| Fastboot V16 stream | `40c1560348b2615064cf8d2f216c5c85a020f9b1384707ec83e93d94a94a3706` | 19,200/8N1 direct ROM path passed |
| recovery A: | `5b114df3b053af325e8254afd2134997cff180c13c6cfee17645059390367905` | immutable base remained unchanged |
| boot manifest | `d98c1ead2a971384f6b4ebe168aaf330876c6dec2cba87c4d852d037b5862930` | identity `c6-6dbe02421fb88cc9` accepted |

The Willem/AT28C64 writes used only the programmer's normal built-in full
post-write verification; no redundant read was requested. D15 changed 3,151
bytes, left 5,041 unchanged, and reported image CRC32 `A1DC319C`. D16 changed
4,529 bytes, left 3,663 unchanged, and reported image CRC32 `2D9CE4D5`.
Both had zero retry bytes, retries, and late completions. The retained DOSRAVI
session names are `at28c64-jukunet-c6-d15-write-20260818` and
`at28c64-jukunet-c6-d16-write-20260818`.

## Cold boot and delayed-host results

C6 reset booted without a keypress and used the direct automatic-ROM path at
19,200/8N1. The `boot_baud: 9600` compatibility field in the host result is
not the effective wire rate: every record identifies `network_rom: true`,
`direct_fastboot: true`, `effective_boot_baud: 19200`, protocol 16, zero stock
frames, zero extension bytes, and the ROM-resident V16 loader.

| run | compressed bulk | first A: request | stream retries | result |
| --- | ---: | ---: | ---: | --- |
| initial full matrix | 4.666156 s | 6.653207 s | 0 | `A>` and complete matrix |
| requested cold boot 1 | 7.671429 s | 9.657446 s | 0 | `A>`; clean status |
| requested cold boot 2 | 6.916085 s | 8.902176 s | 0 | `A>`; clean status |
| requested cold boot 3 | 7.797071 s | 9.787175 s | 0 | `A>`; clean status |

The host was intentionally started before operator power-on. Header probes and
`boot_restarts` recorded while the target was absent are therefore chronology,
not target failures. Once each powered target answered, the bounded JZ exchange
accepted the header and each 7,895-byte compressed stream completed without a
retry. The missing optional final bootstrap reply was conservatively confirmed
by the first valid NetDisk request rather than retransmitting into live CP/M.

One additional recovery observation began with the host accidentally in the
stock-compatible 9,600-baud listener. C6 correctly sent no Janet request. The
host was replaced with the proper `--network-rom` V16 listener at 19,200 while
the machine remained on. C6's overlap-safe scanner then accepted JZ without
another RESET, transferred in 7.168937 s with zero retries, reached its first
disk request 9.156078 s after the corrected host started, and presented `A>`.
This is useful missed-ready/late-host evidence; the discarded 9,600 listener
is a host invocation error and not a failed C6 boot.

## Runtime, media, and recovery matrix

- Status 1.3 reported ROM ABI 1.2, NetDisk v3 at 19,200, N4, S21 `03`, video
  selection 1 (53x24), English locale, two drives, read-ahead 8, cold marker
  `00`, and zero POST, ABI, disk, CRC, and N4 errors.
- A: `DIR` and paginated `TYPE README.TXT` passed.
- B: login, `DIR`, full `TYPE README.TXT`, and B:-loaded `DIAG ALL` passed.
- `DIAG ALL` passed CPU, RAM data/address/retention, checksum, D57, D11, ROM
  ABI, video/console, and keyboard/S21. No-argument private-RAM DIAG passed.
- `N4BULK` passed before and after host replacement.
- Six SOAK runs passed. One host was deliberately stopped during active disk
  I/O; the same SOAK process resumed and completed after replacement.
- Snapshot-backed `ERA README.TXT` persisted across two server replacements.
  The following `DIR` proved deletion and the recovery A: hash above remained
  unchanged.
- Two `WBOOT` operations returned to `A>` and changed the retained marker from
  cold `00` to warm `01`.
- Two live host replacements recovered without RESET. Final status recorded
  reconnect count `02`, read-ahead 8, and zero POST/ABI/disk/CRC errors.

## Local keyboard and sound

With `KEYTEST B` running, the physical keyboard produced exact `juku 2026`,
including Space and digits, followed by Return and Escape. The utility emitted
the corresponding codes, printed `DONE`, and returned to `A>`. This is a
bounded local-input sample rather than another exhaustive contact survey; the
earlier C5 session already covered the full alphanumeric set.

The normal C6 startup diagnostic phrase was audible, proving the physical
speaker and D57 channel-1 path. A 136-byte transient then called the public
low-RAM `JCGSOUND` gate at `D641h` with A=1. The same phrase played, the call
returned A=0, the utility printed `SOUND: service returned PASS`, and CP/M
returned to `A>`.

An earlier temporary caller incorrectly used `FF21h`. It printed its pre-call
line, produced no sound, and did not return; power cycling recovered normally.
`FF21h` is not the sound entry. The resident vector is `FF41h`, while ordinary
CP/M consumers must call the copied mode-safe gate at `D641h`. Correcting only
the temporary utility made the test pass; no ROM or CP/M image change is
required.

## Result and remaining boundary

The C6 blind physical matrix passes on CS00015, and the exact C6 ROM pair is
now the fitted firmware. Automatic V16 boot, resident services, sound, local
keyboard, A:/B:, diagnostics, write safety, warm boot, soak, and host-loss
recovery agree with the simulator claims.

Physical promotion remains deliberately incomplete only for what could not be
observed without a working display: exact selected geometry, rendered glyphs
and pseudographics, and the blinking underline cursor. The simulator's exact
framebuffer oracles remain the software acceptance evidence for those items;
they are not presented as a physical observation.
