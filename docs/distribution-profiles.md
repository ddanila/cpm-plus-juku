# Reproducible CP/M Plus distribution profiles

The distribution build keeps hardware qualification separate from user-facing
software. `make distribution` creates five named artifacts and a JSON report
beside each one:

| Artifact | Purpose | Geometry | Contents | Free space | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| `cpm-plus-juku-recovery.img` | immutable C4 recovery/qualification A: | 386 KiB logical A: | CCP, DIAG, WBOOT, README | 376 KiB | `b4402dc9be86fef9532e61fff491dc3b93dc0db40e68d575c89aab083160bec1` |
| `cpm-plus-juku-native-recovery.img` | post-C4 native recovery A: | 386 KiB logical A: | C4 recovery files plus STATUS, KEYTEST, and Diag 0.5 | 372 KiB | `165441407e549ec351709cab4915112e4424c896d050f04e62a2bd0a069a4df7` |
| `cpm-plus-juku-full.img` | normal licensed A: | 386 KiB logical A: | native recovery files plus PIP, SHOW, SET, DEVICE, DATE, SUBMIT, HELP | 250 KiB | `42c19929f6f4d3d2f168a2757b7bd2492d3cdd18ab2a76b70f31ce0de89fa4c0` |
| `cpm-plus-juku-museum-demo.img` | opt-in initial-command demo A: | 386 KiB logical A: | full A: plus `PROFILE.SUB` | 248 KiB | `2c99a34b02a49c17a745aca6928e5f65306558fb6c7166e9d85acbb6ee97d257` |
| `cpm-plus-juku-apps.juk` | approved native B: | physical 800 KiB cylinder/head image | README and Diag 0.5 | 776 KiB | `1003053769cac8c8b8dc3fef21039f3ce55071d4274701fe929effff6dcdb8b6` |

`out/cpm-plus-juku.img` remains a compatibility name for the recovery A: and
must match `prebuilt/cpm-plus-juku.img` byte for byte. Full and demo profiles
cannot silently alter that C4 baseline. The native recovery profile is the
explicit post-baseline successor; it adds `STATUS.COM` without changing C4.
It also adds `KEYTEST.COM`, whose unbuffered direct-console input and normal
BIOS output provide a blind local-keyboard test over the N4 console.

## Build contract

Profiles under `volume/profiles/` name every CP/M file, source, version, and
license. Pinned third-party binaries additionally carry their expected SHA-256.
The builder rejects duplicate CP/M names, paths outside the repository,
checksum differences, invalid geometry/layout values, and inheritance cycles.
It normalizes host text to CP/M CRLF plus `1Ah`, creates a fresh filesystem,
and atomically replaces the result.

An inherited file may be replaced only by an explicit boolean
`"override": true` entry naming exactly one inherited destination. This is
used by the native recovery profile to replace frozen C4 Diag 0.4 with Diag
0.5. Missing, ambiguous, or non-boolean overrides fail the build; the override
marker is not retained in the resolved manifest.

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

## Host-visible set

`make manifest-check` also generates a single native boot/media manifest that
binds the system and v15 bootstrap hashes to these volume reports. See
[`boot-manifest.md`](boot-manifest.md). The host can validate a selected A:
and B: before opening the serial link and recommends read-only B: plus
snapshot-backed A: for museum sessions.
