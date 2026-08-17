# CP/M Plus 3.1 C5 desk release candidate

Status: **BLIND C5 MATRIX PASSED; DISPLAY ACCEPTANCE PENDING**

Date: **2026-08-17**

`make release-candidate` produces one deterministic, self-contained candidate
named `cpm-plus-3.1-juku-c5-desk`. It closes the artifact-binding gap between
the ABI 1.1 C5 ROM and the matching locale/native CP/M Plus 3.1 system. It is
not a promoted hardware release.

## Bound artifact set

The generated directory and uncompressed deterministic tar contain:

- the 16 KiB ABI 1.1 C5 ROM, exact D15-low and D16-high 8 KiB halves, and ROM
  metadata;
- the matching locale-native CP/M Plus 3.1 `JUKURM1` system and V15 fastboot
  stage—not the ABI 1.0 native system;
- the native recovery, full, museum/demo, and approved native-geometry B:
  media plus their reproducibility/provenance reports;
- the C5 boot/media manifest, project license and third-party notice;
- a package manifest covering every payload file by size and SHA-256.

The C5 boot manifest requires ROM ABI 1.1 and uses `c5-native` as its primary
system slot. The immutable C4 system/fastboot pair remains the explicit bounded
fallback. The production host can therefore reject a stale or mixed artifact
set before opening the serial device.

Build and verify it with:

```sh
cd ~/fun/cpm-plus-juku && make release-candidate
```

Generated outputs are:

```text
out/cpm-plus-3.1-juku-c5-desk/
out/cpm-plus-3.1-juku-c5-desk.tar
out/cpm-plus-3.1-juku-c5-desk.tar.sha256
```

The current deterministic tar SHA-256 is
`b9ffd34ef6c87eebf019a29f543bfd75ecabbe04f1061c4c7911dce78d883b34`.

`tests/release_candidate_test.py` builds the package twice in independent
temporary paths and requires byte-identical tar files. It also rechecks every
packaged hash, every primary/fallback slot artifact, and the D15+D16
concatenation. `tests/c5_boot_manifest_test.py` rejects an ABI 1.0 CP/M/C5
pairing and pins the ROM metadata, system slots, and media set.

## Blind keyboard qualification

The native recovery/full profiles include `KEYTEST.COM`. The host may inject
`KEYTEST` through N4 after `A>`; the utility then reads every following key via
CP/M direct console input and reports it through the ordinary BIOS console
path as `KEY hh`, adding the printable character when applicable. For example,
Space is `KEY 20 ' '`, Enter is `KEY 0D`, and `A` is `KEY 41 'A'`. Escape or
Ctrl-C is reported and then exits; a 128-key bound is the final escape hatch.

`KEYTEST B` is the preferred continuous-typing test. It polls and stores up to
64 local keys without emitting anything, then reports the complete batch after
Enter. This avoids pausing the polled keyboard while N4 prints a report for the
previous key. Each report starts with `BATCH hh`; Escape or Ctrl-C also flushes
the pending batch and exits.

`READY` is deliberately the final banner line. This prevents an automated
host from injecting the first key while CP/M is still printing instructions;
the simulator regression originally reproduced and then closed exactly that
race. The regression runs buffered mode, sends `A`, Space, `1`, Enter, and
Escape, and requires both batch lengths, all five exact reports, `DONE`, and
the returned `A>` prompt.

On a monitorless physical run, start the N4 PTY, wait until the host observes
`Juku Keytest 1.1 READY`, and then press the local keys. For a typing sequence,
run `KEYTEST B`, type the sequence, and press Enter; its buffered codes then
appear in the host-side PTY/log even though the display is unavailable. Remote
Escape can terminate the utility if a local Escape key is unavailable.

## Promotion boundary

The C5 ROM now passes a blind CS00015 run: direct 19,200-baud autoboot, both
drives, the full non-destructive diagnostic suite, sequential read,
snapshot-backed erase, warm boot, local keyboard including Space, and live
host replacement without RESET. See
[`cs00015-c5-blind-qualification-20260817.md`](cs00015-c5-blind-qualification-20260817.md).

Promotion now waits for a working display to confirm all selected S21 modes,
readable glyphs, and the blinking cursor, plus a short physical check of Status
1.3 and buffered Keytest 1.1. Until that passes, C5 remains a candidate and C4
remains the immutable fallback.
