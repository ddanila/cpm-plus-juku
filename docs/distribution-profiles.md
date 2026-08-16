# Reproducible CP/M Plus distribution profiles

The distribution build keeps hardware qualification separate from user-facing
software. `make distribution` creates five named artifacts and a JSON report
beside each one:

| Artifact | Purpose | Geometry | Contents | Free space | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| `cpm-plus-juku-recovery.img` | immutable C4 recovery/qualification A: | 386 KiB logical A: | CCP, DIAG, WBOOT, README | 376 KiB | `b4402dc9be86fef9532e61fff491dc3b93dc0db40e68d575c89aab083160bec1` |
| `cpm-plus-juku-native-recovery.img` | post-C4 native recovery A: | 386 KiB logical A: | C4 recovery files plus STATUS | 374 KiB | `d3bddfc903fabd4f998fdc7e8c57af6071bed3914a91b752cea29b560c8b67e2` |
| `cpm-plus-juku-full.img` | normal licensed A: | 386 KiB logical A: | native recovery files plus PIP, SHOW, SET, DEVICE, DATE, SUBMIT, HELP | 252 KiB | `a7e5401daaff5f4e4d477b2577241baf58a96f0266eeb0ab8eff46b8aa354b74` |
| `cpm-plus-juku-museum-demo.img` | opt-in initial-command demo A: | 386 KiB logical A: | full A: plus `PROFILE.SUB` | 250 KiB | `0df47df9bbff5005625737f73433aa3bbc92bda954bd1ab4c74d46013d4f2fac` |
| `cpm-plus-juku-apps.juk` | approved native B: | physical 800 KiB cylinder/head image | README and DIAG | 776 KiB | `8e84cb1ab3f2d0be86d516d515389ef4588a0a15665132949de2e5e4c6e7273c` |

`out/cpm-plus-juku.img` remains a compatibility name for the recovery A: and
must match `prebuilt/cpm-plus-juku.img` byte for byte. Full and demo profiles
cannot silently alter that C4 baseline. The native recovery profile is the
explicit post-baseline successor; it adds `STATUS.COM` without changing C4.

## Build contract

Profiles under `volume/profiles/` name every CP/M file, source, version, and
license. Pinned third-party binaries additionally carry their expected SHA-256.
The builder rejects duplicate CP/M names, paths outside the repository,
checksum differences, invalid geometry/layout values, and inheritance cycles.
It normalizes host text to CP/M CRLF plus `1Ah`, creates a fresh filesystem,
and atomically replaces the result.

Each report records the image hash, geometry, physical layout, CP/M directory,
per-file source and volume hashes, provenance, allocation, and free space.
`tests/distribution_test.py` rebuilds all profiles, requires byte-identical
images and reports, exercises negative profiles, and proves the named recovery
image still equals C4.

The B: profile is built in CP/M logical side-then-track order and then converted
to the physical Juku cylinder/head order expected by `--drive-b`. The
distribution cosimulation passes this physical image through the production
host's inverse conversion, selects B:, lists it, loads B:`DIAG.COM`, returns to
A:, and retains the framebuffer oracle with zero NetDisk retries.

Run the complete distribution gates with:

```sh
make distribution-check
make distribution-cosim-check
```

## Initial command policy

The normal full A: has no startup command. The museum profile adds a plain
`PROFILE.SUB` containing `DIR`; CP/M Plus's CCP prints its first prompt,
submits the profile, and then prints the stable interactive prompt. Automation
must wait for that second prompt. The cosimulation asserts this sequence before
typing any test command. Changing `volume/PROFILE.sub` creates a new, explicitly
named demo image and never changes recovery A:.
