# Reproducible CP/M Plus distribution profiles

The distribution build keeps hardware qualification separate from user-facing
software. `make distribution` creates seven named artifacts and a JSON report
beside each one:

| Artifact | Purpose | Geometry | Contents | Free space | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| `cpm-plus-juku-recovery.img` | immutable C4 recovery/qualification A: | 386 KiB logical A: | CCP, DIAG, WBOOT, README | 376 KiB | `b4402dc9be86fef9532e61fff491dc3b93dc0db40e68d575c89aab083160bec1` |
| `cpm-plus-juku-native-recovery.img` | post-C4 native recovery A: | 386 KiB logical A: | C4 recovery files plus Status 1.3, Keytest 1.1, and Diag 0.5 | 372 KiB | `899fface833e53d06634bb7d2291d7e675d43a101911fbc225fc0ccd2831570a` |
| `cpm-plus-juku-c6-recovery.img` | ABI 1.2 C6 recovery/test A: | 386 KiB logical A: | native recovery plus Keyraw, Soak, and N4Bulk | 366 KiB | `67d0a99b2979642d6f7d5d9c20ef705be685c99f1ab7846b8cf4f3ea383a54b0` |
| `cpm-plus-juku-full.img` | normal licensed A: | 386 KiB logical A: | licensed history CCP, HIST, DRI files, gap tools, VIDTEST, PANEL, and `TOOLS.TXT` | 222 KiB | `64ef456e9e5f8fb9fcc237d56ee92deb9e11c30a4b887dbdcbaa734fc1b51750` |
| `cpm-plus-juku-dev.img` | optional strict-8080 development A: | 386 KiB logical A: | full A: plus ED, HEXCOM, PATCH, SID, and the source/HEX form of a reproducible example | 194 KiB | `c23de8944b2cc49f7413d27178549a9c60d19783b04dfbcf1b8048ba8bcb1e18` |
| `cpm-plus-juku-museum-demo.img` | opt-in initial-command demo A: | 386 KiB logical A: | full A: plus `PROFILE.SUB` | 220 KiB | `bcb87b820d5797691819294167fc107bba424441b7210e243a8bdb0f0d787590` |
| `cpm-plus-juku-apps.juk` | approved native B: | physical 800 KiB cylinder/head image | README and Diag 0.5 | 776 KiB | `1003053769cac8c8b8dc3fef21039f3ce55071d4274701fe929effff6dcdb8b6` |

`out/cpm-plus-juku.img` remains a compatibility name for the recovery A: and
must match `prebuilt/cpm-plus-juku.img` byte for byte. Full and demo profiles
cannot silently alter that C4 baseline. The native recovery profile is the
explicit post-baseline successor; it adds `STATUS.COM` without changing C4.
It also adds `KEYTEST.COM`, whose direct-console single-key and buffered-line
input modes and normal BIOS output provide a blind local-keyboard test over
the N4 console.
The C6 recovery profile is separately named because `KEYRAW.COM` and
`N4BULK.COM` require ABI 1.2. `SOAK.COM` provides one deterministic
read/diagnostic/write cycle for the long reconnect harness. None of these
files is inserted into the immutable C4 or physically established C5 images.

Full, development, and demo replace only their user-facing CCP with the
reproducible Juku history derivative and add `HIST.COM`. The build first proves
the unmodified DRI CCP byte-for-byte; all recovery profiles continue to carry
that exact original. See
[`cpm3-command-history.md`](cpm3-command-history.md).

The development profile is deliberately separate from the ordinary full
profile. `HEXCOM.COM`, `PATCH.COM`, and `SID.COM` are rebuilt byte-for-byte
from their pinned Digital Research assembly sources before admission. ED's
PL/M-80/assembly source, upstream recipe, binary, and HELP topic are pinned;
the strict simulator inserts text through its actual command prompt, saves,
returns to CCP, and reads the new file back. The image includes `HELLO.ASM`
and its Intel HEX output: the same run converts and executes `HELLO.COM`,
enters and quits SID, and asks PATCH to enumerate SID's installed patches.
This proves the selected host-assisted edit/assemble-to-HEX/convert/debug
workflow without claiming that a source-complete on-target assembler exists.

The full profile's project utilities are documented and independently
simulator-admitted in [`project-utilities.md`](project-utilities.md).
Its deterministic display utility and physical procedure are documented in
[`cpm3-video-acceptance.md`](cpm3-video-acceptance.md).
The first real CP437 text-interface consumer and its exact local/N4
framebuffer admission are documented in [`cpm3-panel.md`](cpm3-panel.md).

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

The B: profile is built in CP/M logical side-then-track order and then
converted to the physical Juku cylinder/head order expected by `--drive-b`.
The distribution cosimulation boots the C6 network-first ROM and native BIOS,
passes this physical image through the production host's inverse conversion,
selects B:, lists it, loads B:`DIAG.COM`, returns to A:, and retains the
framebuffer oracle with zero NetDisk retries. On A: it also executes the
shipped DRI file/system utilities: `SETDEF`, exact `DUMP`, the `HELP DUMP`
topic, two four-record `PIP` copies with exact CRCs, `SHOW`, `SET`, `DATE`, `SUBMIT`, and native `DEVICE
NAMES` with the fixed `JUKU` character table. Interactive HELP exit is driven
explicitly; copied bytes and attributes are verified by subsequent commands;
and every extra-command byte is included in the independent framebuffer
oracle. The separate general cosimulation retains the RomBios compatibility
path and immutable C4/C5/C6 artifacts byte for byte.

Both full and development command matrices capture live stack low-water marks
inside the 39,168-byte C6 TPA and cross-check per-file disk allocation. The
exact evidence and conservative interpretation are in
[`cpm3-runtime-memory.md`](cpm3-runtime-memory.md).

Run the complete distribution gates with:

```sh
make distribution-check
make distribution-cosim-check
make development-cosim-check
make vidtest-cosim-check
make history-cosim-check
make panel-cosim-check
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
