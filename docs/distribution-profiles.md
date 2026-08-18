# Reproducible CP/M Plus distribution profiles

The distribution build keeps hardware qualification separate from user-facing
software. `make distribution` creates seven named artifacts and a JSON report
beside each one:

| Artifact | Purpose | Geometry | Contents | Free space | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| `cpm-plus-juku-recovery.img` | immutable C4 recovery/qualification A: | 386 KiB logical A: | CCP, DIAG, WBOOT, README | 376 KiB | `b4402dc9be86fef9532e61fff491dc3b93dc0db40e68d575c89aab083160bec1` |
| `cpm-plus-juku-native-recovery.img` | post-C4 native recovery A: | 386 KiB logical A: | C4 recovery files plus Status 1.3, Keytest 1.1, and Diag 0.5 | 372 KiB | `17751ba06fa5a59836a99b0dd83ea2185186f025cf3dbb650610d16a6e6b5074` |
| `cpm-plus-juku-c6-recovery.img` | ABI 1.2 C6 recovery/test A: | 386 KiB logical A: | native recovery plus Keyraw, Soak, and N4Bulk | 366 KiB | `5b114df3b053af325e8254afd2134997cff180c13c6cfee17645059390367905` |
| `cpm-plus-juku-full.img` | normal licensed A: | 386 KiB logical A: | native recovery and DRI files plus CRC, CMP, MEM, WC, FIND, STRINGS, and `TOOLS.TXT` | 228 KiB | `7b2f38686409de4f7bf7f050e84357e5f74258c81b0616f6f6ab18aad9063b09` |
| `cpm-plus-juku-dev.img` | optional strict-8080 development A: | 386 KiB logical A: | full A: plus HEXCOM, PATCH, SID, and the source/HEX form of a reproducible example | 210 KiB | `04c76245f619adc80f9f0dfcc71526fd641c08e3c29d92077c89d2528ce77892` |
| `cpm-plus-juku-museum-demo.img` | opt-in initial-command demo A: | 386 KiB logical A: | full A: plus `PROFILE.SUB` | 226 KiB | `ed580c033d2491a8f30b21c9d24cc7f6753bf9423d929930395a4f06e6e518e1` |
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

The development profile is deliberately separate from the ordinary full
profile. `HEXCOM.COM`, `PATCH.COM`, and `SID.COM` are rebuilt byte-for-byte
from their pinned Digital Research assembly sources before admission. The
image includes `HELLO.ASM` and its Intel HEX output: the strict-8080 simulator
runs `HEXCOM HELLO`, executes the resulting `HELLO.COM`, enters and quits SID,
and asks PATCH to enumerate SID's installed patches. This proves the complete
host-assisted edit/assemble-to-HEX/convert/debug workflow without claiming
that an original on-target assembler is available from complete source.

The full profile's project utilities are documented and independently
simulator-admitted in [`project-utilities.md`](project-utilities.md).

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
A:, and retains the framebuffer oracle with zero NetDisk retries. On A: it
also executes the shipped DRI file/system utilities: `SETDEF`, exact `DUMP`,
the `HELP DUMP` topic, `PIP` create/copy, `SHOW`, `SET`, `DATE`, and `SUBMIT`.
Interactive HELP exit is driven explicitly; copied bytes and attributes are
verified by subsequent commands; and every extra-command byte is included in
the independent framebuffer oracle. `DEVICE NAMES` is executed separately on
the native-BIOS/full-volume path, where the real fixed `JUKU` character table
must be reported. This split preserves the immutable RomBios and C4/C5/C6 SYS
artifacts byte for byte.

Run the complete distribution gates with:

```sh
make distribution-check
make distribution-cosim-check
make development-cosim-check
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
