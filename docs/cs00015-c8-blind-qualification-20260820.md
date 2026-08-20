# CS00015 C8 blind qualification — 2026-08-20

Status: **AUTOMATED AND ATTENDED BLIND MATRICES PASSED; DISPLAY AND
FORCED-POST-FAILURE OBSERVATIONS POSTPONED**

## Scope

CS00015 is fitted with the packaged JukuNet C8 / ROM ABI 1.3 pair. No usable
display was available, so this session makes only evidence-backed blind claims:
direct automatic Fastboot V16, CP/M and NetDisk, the resident N4 services,
A:/B:, diagnostics, warm boot, write/erase, disk soak, and repeated live host
replacement. A later attended extension also covers a representative local-key
sample and normal sound. It does not claim physical glyphs, geometry, cursor,
or the audible C1--C5 failure patterns.

## Installed artifacts

| artifact | SHA-256 | physical result |
| --- | --- | --- |
| combined C8 ROM | `a54cb877edfe25e939e05ada0e98783acb53cfc8969071c63928b119c8e09e46` | D15/D16 pair fitted in CS00015 |
| D15 `JukuNet C8 Low` | `aa14d114a0176d3123b5d58366c45d05462c8a2127893fa996a533a9107d1773` | 8,192-byte built-in verify passed |
| D16 `JukuNet C8 High` | `1afbed0b22ec5ab8d32fffb9784c0e87a287f54ec65cb2b0565afa91552dc5ee` | 8,192-byte built-in verify passed |
| C8 CP/M system | `ec9b7fd00db2d8e70258aae74500fa261f987b6b04bddfdb5ab44e56ca2ba3f1` | booted to `A>` |
| Fastboot V16 stream | `44735bf468a2014bbcf327d5d0770d9fcf21a3c33704499282180ad6c95898ea` | direct 19,200/8N1 ROM path passed |
| boot manifest | `c6b733ec1574594427e1f8485c19aa2aeb0a3c377586e3490cfce9c46e0273b8` | identity `c8-ec9b7fd00db2d8e7` accepted |

The Willem/AT28C64 writes used only the programmer's built-in post-write
verification. D15 changed 1,844 bytes, left 6,348 unchanged, and verified all
8,192 bytes with zero retries. D16 changed 3,567 bytes, left 4,625 unchanged,
and likewise verified all 8,192 bytes with zero retries. The first D16 attempt
ended before `EXEC` when the laptop lost power, so it did not touch the chip;
the successful retry is retained separately.

## Automatic cold boot

The passing `c8-blind` run used the manifest-bound system, ROM metadata,
Fastboot stage, private writable A: snapshot, read-only native B:, host source,
runner, workload, console bytes, events, and per-request trace. The direct C8
transfer carried 7,670 compressed bytes at 19,200 baud, completed in 11.187 s,
and produced the first valid disk request at 13.060 s after target response.
The complete 15-command run reached its prompt and finished in 252.141 s from
the runner's pre-reset wait. It recorded 62 disk-read requests covering 496
records and no disk retries.

The matrix passed:

- cold and warm `STATUS`, with ABI 1.3, POST/ABI/disk status zero, two drives,
  NetDisk v3, read-ahead 8, and the expected cold-to-warm marker transition;
- two `DIAG ALL` executions, including the ROM-resident CPU, RAM,
  retention/checksum, D57, D11, ABI, video/console, and keyboard/S21 selectors;
- A: and B: directory paths, B:-loaded diagnostics, `N4BULK` before and after
  warm boot, a disk `SOAK`, and writable-A: `ERA` followed by directory proof;
- the remote-input path through `KEYTEST B`, including Space, Return, and
  Escape. This proves N4 input delivery, not the physical keyboard contacts.

The first capture was rejected only because its runner expected the diagnostic
status byte labelled `ROM ABI` to contain ABI minor `03`; the target correctly
reported status `00` and separately identified `ROM: Juku ABI 01.03`. The fixed
runner then passed 15/15 and its independent audit passed.

## Repeated attended cold boots

Two additional independent power-on boots used focused, manifest-bound
workloads after stopping unrelated simulator load:

| sample | accepted bulk | first disk request | accepted header retries | result |
| --- | ---: | ---: | ---: | --- |
| attended 1 | 5.750 s | 7.623 s | 0 | 7/7 and audit pass |
| focused 2 | 9.568 s | 11.438 s | 2 | 4/4 and audit pass |

Both reached `A>` automatically, reported cold marker `00` and zero POST, ABI,
disk, and N4 failures, then passed full diagnostics, N4 bulk output and disk
soak with no NetDisk retries. The first also passed warm boot and the retained
warm marker. The second accepted transfer needed two bounded header retries;
this variability is retained as a boot-margin observation, not hidden. It did
not propagate into disk errors or prevent automatic recovery.

One earlier attended capture is retained as a harness failure rather than a
target failure: CP/M booted, but the runner tried to read a host-side Enter
confirmation from noninteractive stdin and received EOF at `KEYTEST READY`.
The corrected `--external-operator` path announces the action and trusts only
the subsequent captured target bytes.

The corrected attended run captured the physical keyboard spelling
`juku 2026`, including Space and digits, followed by Return and Escape. It then
returned from `KEYTEST B` and completed the remaining matrix. This is the
intended representative sample for the original, mechanically variable Juku
keyboard; it is not an exhaustive contact survey.

## Unattended host-loss and reconnect

The acceptance runner now has an explicit `--resume` mode. It starts the host
with `--resume-disk`, queues a Return until the resident N4 reprobe accepts it,
requires a returned `A>` prompt, and retains the same hashes, lifecycle,
console, event, request, command, and private-media evidence as a cold run.
It deliberately requires no RESET or local keypress.

Two preliminary captures refined the oracle without changing the target. The
first reattached and ran `DIR`, then showed that an intentional host loss is
remembered as N4 failure reason `01`. The second passed 13 commands, including
two disk soaks and warm boot, then showed that warm boot correctly preserves
that reason. The final workload therefore requires `01`, while the reconnect
counter is allowed to increase.

| retained run | reconnect to `A>` | complete matrix | disk reads / records | retries | retained counter |
| --- | ---: | ---: | ---: | ---: | ---: |
| `c8-reconnect-03` | 0.766 s | 172.428 s | 74 / 592 | 0 | `03` |
| `c8-reconnect-04` | 0.588 s | 172.240 s | 74 / 592 | 0 | `04` |

Both final runs passed 15/15 and independently re-audited. Each covered `DIR`,
`STATUS`, `N4BULK`, remote `KEYTEST`, two A:-loaded `DIAG ALL`/soak sequences,
B: selection and B:-loaded diagnostics, A: return, warm boot, status, another
bulk transfer, and a third soak. The host stopped cleanly after each run and
CS00015 remained at `A>`; four sequential server losses were recovered without
RESET.

## Normal sound

The reproducible 136-byte `physical/helpers/sound.asm` caller invokes the fixed
low-RAM `JCGSOUND` gate at `D641h` with cue 1. Its binary SHA-256 is
`888399fbe423da8e077935e557af57ec6fda4d7412090877a04dc0aa40646b9d`.
A derived private A: image added only this transient; the retained manifest and
runner snapshots bind that image without changing the standard distribution
or fitted ROM.

The running C8 session reattached in 1.041 s. `SOUND` loaded with nine disk
reads/72 records and zero retries, printed both the start and service-PASS
markers, played the diagnostic tune audibly, and returned to `A>`. The
operator confirmed the tune by ear. This closes normal speaker, D57 channel 1,
ROM sound service, copied gate, and return-path behavior. It does not claim the
separate C1--C5 POST failure phrases.

## Portable C host M2.1 qualification

The exact accepted Linux `jukuhost 0.1.0-m2` executable, SHA-256
`09b20fc58d9383282528b90cc4af21405bb738d2c0149780f442a5dd056317ec`,
was subsequently exercised against this same fitted C8 pair. The manifest,
ROM, Fastboot V16 stage, CP/M system, A: and B: identities remained identical
to the table above.

Three new retained runs passed:

| run | purpose | result | reads / records / writes | disk retries |
| --- | --- | ---: | ---: | ---: |
| `physical-CS00015-m2.1-linux-02` | cold boot and complete blind workload | 15/15 | 70 / 560 / 5 | 0 |
| `physical-CS00015-m2.1-linux-reconnect-01` | replace host in a live CP/M session | 15/15 | 77 / 616 / 12 | 0 |
| `physical-CS00015-m2.1-linux-reset-01` | RESET into a fresh network boot | 4/4 | 33 / 264 / 4 | 0 |

The matrix covered A:, B:, remote input and bulk output, status, repeated full
diagnostics, disk soak, controlled writable-A: changes, warm boot, clean host
stop, live host replacement and target reset. The replacement continued at
request sequence `4C`; both cold paths restarted at `01`. All three raw
captures regenerate the retained request traces byte for byte, all independent
audits pass, and the corresponding C8/Linux PTY simulator paths pass.

The cold host summaries count 382 and 186 pre-target probe groups while the
operator had not yet powered or reset the board; the native source increments
that aggregate field once per 32 unanswered readiness probes. These are not
disk retransmissions: every structured NetDisk trace reports zero retries.
Both cold sessions reached `A>` 3.040 seconds after the first disk request.

The first preparation attempt exposed a host-runner issue, not a board issue:
Linux PTY masters return `EIO` until the native host opens its N4 slave after
Fastboot. The runner now waits through this transient condition and has a
delayed-open regression. Its resume auditor now also accepts the native
`phase=netdisk` marker rather than requiring wording from the retired Python
host.

## Result and remaining boundary

C8's new resident-host migration and the portable C host's M2.1 gate have
passed their automated blind physical boundary on CS00015. The exact fitted
ROM pair boots the exact manifest-bound CP/M image, resident ABI 1.3 services
work under sustained traffic, warm boot is stable, and repeated replacement
hosts recover with zero disk retries.

Promotion is still intentionally narrower than “all physical gates complete”.
The local-keyboard, normal-sound, repeated cold-boot, and automated blind gates
now pass. The operator chose to postpone only the separate display/glyph/cursor
observations and safe physical exercise of the C1--C5 POST failure tones. C6
remains the immutable rollback image while those explicitly physical items are
pending; exact simulator oracles continue to cover both without being presented
as physical observations.
