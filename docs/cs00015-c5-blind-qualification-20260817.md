# CS00015 C5 blind qualification — 2026-08-17

## Scope

CS00015 ran the packaged JukuNet C5 ROM while the external display was
unavailable. This run therefore qualifies reset/autoboot, serial bootstrap,
NetDisk, diagnostics, local keyboard input through N4 observation, warm boot,
snapshot writes, and live host replacement. It does not qualify framebuffer
appearance or the blinking cursor.

The installed EPROMs were labelled `JukuNet C5 LOW` (D15) and
`JukuNet C5 HIGH` (D16). Their SHA-256 values were respectively
`2100718d75a2bcf2fc9d6497622f1db94ebf82b48f05445afc130a08b081a9bf`
and `a47d9be5e9a087efffb68c95f249084ec4bce8038446bb07897f354d8197d193`;
their concatenated C5 ROM hash was
`9ed6273f44c1b09dcb5fcd3ca94e5a1aad813b285607558a7d8cb98b1a5e6e7a`.
Both AT28C64 writes completed with their one built-in full verification and no
retry or late-write event.

S21 was `00000011` (`03h`). Bit 0 produced immediate automatic boot. Raw `03h`
has bits 2:1=`01`, so the intended video selection is mode 1, 53x24. Status 1.2
printed mode `03`, but the same run exposed its adjacent-field formatter bug;
that decoded text is not usable evidence. The independent binary N4 report
confirmed `s21=03`, `video=1`, `features=1F`, and `clock=00`. No monitor was
available to confirm the selected geometry physically.

## Exact boot result

The host manifest selected `c5-native`; the C4 fallback was not used. The
system hash was
`86b36bd70156d10bafba332bd02e8756473c76bde3e9cc4a50fbc530bfb8a3f2`
and the V15 stage hash was
`4aaff8f9a78c289e96bb1699453d3136f7c2f6c82f3bfb2323d46145028178b0`.
The 19,200-baud bulk transfer took 4.349916 s with zero retries; the first disk
request arrived 6.267955 s after the first accepted bootstrap request. The
target then emitted the CP/M Plus 3.1 banner and `A>` over N4.

## Command and media matrix

- `DIAG IO` passed D57 PIT clock, D11 USART status, ROM ABI, video/console, and
  keyboard/S21.
- `DIAG ALL` passed CPU, RAM data, RAM address, RAM retention, checksum, D57,
  D11, ROM ABI, video/console, and keyboard/S21.
- A: `DIR` succeeded. Paginated `TYPE README.TXT` completed after a remote
  Return at its continuation prompt.
- Snapshot-backed `ERA README.TXT` returned to `A>`; the following `DIR`
  confirmed the deletion while leaving the base image unchanged.
- `WBOOT` returned to `A>`.
- Native-geometry B: logged in, listed `README.TXT` and `DIAG.COM`, and loaded
  its own `DIAG CPU`, which passed.

## Local keyboard coverage

`KEYTEST.COM` observed local input and mirrored its reports over N4. Space,
Backspace, Tab, Return, Delete, and Escape all produced the correct control
codes; Escape terminated the utility and returned to `A>`. Across three
passes, every letter `a` through `z` and every digit `0` through `9` produced
the correct code at least once. Observed punctuation included Space, comma,
slash, backslash, both brackets, equals, less-than, and question mark.

The standard keyboard occasionally misses a press. The per-key utility also
made this worse by printing through N4 between polls: continuous `juku 2026`
lost one `u`, and `abcdefghij` lost `d` and `j`, although those letters worked
in later passes. `KEYTEST B` now buffers a complete line before reporting and
has an exact simulator regression, removing this observer effect. Standalone
Shift/Ctrl, function, navigation, Caps Lock, Erase, LAT/RUS, and national keys
remain outside this character-level test; a future raw-matrix utility would be
needed to qualify contacts which intentionally translate to zero.

## Live host replacement

After the command matrix, the original host was stopped deliberately. It saved
the sparse A: snapshot, and a fresh `--resume-disk` host reopened the same
overlay while CS00015 remained on. The replacement immediately received N4
poll sequence `7F`; no RESET or keyboard input was used. A subsequent `DIR`
returned to `A>` and still showed `README.TXT` absent, proving both service
recovery and overlay continuity.

## STATUS formatter finding

The physical run exposed that Status 1.2 printed the first byte after each
freshly loaded pointer correctly but could print unrelated bytes for adjacent
fields after a BDOS string call. This made values such as CRC retries,
read-ahead depth, and capability flags appear as repeated `03`. The cause was
assuming BDOS function 9 preserved HL. Status 1.3 now preserves HL explicitly;
the simulator requires exact ABI, S21/video, boot, and capability lines. The
transport and the underlying binary N4 status reports were not implicated:
the host received bootstrap stage `50h`, zero CRC retries, protocol 15, ABI
minor 1, and capabilities NetDisk v3/read-ahead 8/features `3Fh`/two drives.

## Result and remaining gate

The C5 blind hardware matrix passes on CS00015. Promotion still waits for a
working display to confirm the selected geometry, exact glyphs, and blinking
underline cursor, plus a short physical check of the corrected Status 1.3 and
buffered Keytest 1.1 media utilities. No ROM reburn is needed for those utility
checks.
