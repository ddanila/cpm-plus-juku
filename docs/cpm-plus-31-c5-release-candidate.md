# CP/M Plus 3.1 C5 desk release candidate

Status: **DESK-QUALIFIED; COMPLETE C5 PHYSICAL ACCEPTANCE PENDING**

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
`1797d9eb6168441bb0f7479325bbdba28e3a72368a5f769b1dcbedc752214334`.

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

`READY` is deliberately the final banner line. This prevents an automated
host from injecting the first key while CP/M is still printing instructions;
the simulator regression originally reproduced and then closed exactly that
race. The regression sends `A`, Space, `1`, Enter, and Escape and requires all
five exact reports plus `DONE` and the returned `A>` prompt.

On a monitorless physical run, start the N4 PTY, wait until the host observes
`Juku Keytest 1.0 READY`, and then press the local keys. Their codes appear in
the host-side PTY/log even though the display is unavailable. Remote Escape
can terminate the utility if a local Escape key is unavailable.

## Promotion boundary

The existing C4 physical evidence remains the safe automatic-ROM baseline:
three cold boots, the complete blind command/disk matrix, and live host
reconnect passed on CS00015. C5 adds real resident configuration, locale,
remapping, bootstrap records, and independent A:/B: caches, so simulation
alone cannot promote it.

When hardware work resumes, use the exact packaged D15/D16 halves and repeat
the complete CS00015 matrix: cold and warm boot, sequential read, write/erase,
host loss/live reconnect, all selected S21 modes, readable local display,
blinking cursor, and local keyboard including Space. Record exact package and
run hashes. Until that passes, C5 is a desk release candidate and C4 remains
the physical fallback.
