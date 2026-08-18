# CP/M 3.1 utility provenance

Status: **PINNED AND STRICT-8080 VERIFIED IN FULL/DEMO/DEV; C4 UNCHANGED**

Priority 1 requires a useful distribution without importing unexplained
binaries. The selected source is John Elliott's 2026-06-07 Unix build of the
Digital Research CP/M 3.1 release:

- release page: <https://www.seasip.info/Cpm/software/dri.html>;
- source archive: `cpm3src_unix.zip`, locally pinned as
  `cpm3src_unix-20260607.zip`;
- matching binary archive: `cpm3bin_unix.zip`, locally pinned as
  `cpm3bin_unix-20260607.zip`;
- Digital Research redistribution record:
  [`third_party/cpm3/LICENSE.md`](../third_party/cpm3/LICENSE.md).

The upstream release records CP/M 3 Y2K corrections, the 2025-01-22 CCP and
loader corrections, and the 2026-06-07 HELP update. The HELP binary identifies
itself as `HELP UTILITY v1.1 pl5`. The complete source archive is retained
because the PL/M utilities share runtime and parser modules; copying only one
top-level `.plm` file would not constitute the corresponding source.

## Locked inputs

| archive | bytes | SHA-256 |
| --- | ---: | --- |
| source | 566,619 | `d90cda1f25112ace3b436c4054304ace423331caa1f034c44f26698728a9fdb7` |
| binaries | 133,368 | `ec24f6e1fa173d33bcd2555dfae8296471fc8ea144c72e8cbe2166971451da82` |

`third_party/cpm3/releases/provenance.json` additionally records, for every
selected file, its archive member, source members, version description, size,
and SHA-256. The approved set is `PIP.COM`, `SHOW.COM`, `SET.COM`,
`DEVICE.COM`, `DATE.COM`, `SUBMIT.COM`, `SETDEF.COM`, `DUMP.COM`, `HELP.COM`,
and `HELP.HLP`. The optional development selection additionally admits
`ED.COM`, `HEXCOM.COM`, `PATCH.COM`, and `SID.COM`. The HELP source mapping
includes their topics as well as `setdef.help` and `dump.help`; the pinned
database exposes all six.

The broader 23-program source/binary corpus, including deferred duplicates and
development candidates, is independently rendered and negative-tested in
[`cpm3-utility-catalogue.md`](cpm3-utility-catalogue.md). A catalogue row is
not permission to ship it; only entries admitted by this file and a generated
volume profile are distributed.

## Reproducible extraction gate

Run:

```sh
cd ~/fun/cpm-plus-juku && make distribution-input-check
```

The gate verifies both complete archives before opening them, requires every
recorded source member, verifies every selected binary's size and digest,
extracts only the approved names into `build/cpm3-utilities`, and compares a
deterministic extraction manifest. Its negative regression mutates the pinned
binary archive and requires rejection.

`make dev-utility-rebuild-check` independently builds archived host helpers,
runs the archived MAC/RMAC/DRLINK tools through the pinned ZXCC environment,
and reconstructs HEXCOM, PATCH, and SID from their mapped assembly sources.
All three results must equal both the pinned release bytes and catalogue
digests. ED has complete PL/M-80/assembly source and the pinned upstream build
recipe, but its clean rebuild needs the original PL/M80/ASM80/Thames tools;
the maintained upstream binary is instead checksum-pinned and must pass a real
edit/save/readback path. See
[`cpm3-development-tools.md`](cpm3-development-tools.md).

This gate deliberately does not alter `out/cpm-plus-juku.img`. C4 remains the
immutable Priority 0 qualification volume. The separately named full, demo,
and development profiles consume the staged files with generated contents,
provenance, free-space, and hash reports. The distribution cosimulation executes a useful
path through every admitted program: `SETDEF`; exact `DUMP`; interactive
`HELP`; a `PIP` file creation proved by a second exact dump; `SHOW` space;
`SET` read-only/read-write transitions; rejected `DATE` input; and a
missing-file `SUBMIT`. A separate native-BIOS run executes `DEVICE NAMES` and
requires the real `JUKU` input/output entry. The matrix then retains the normal
warm-boot, write/erase, and B:-drive regression. The simulator records actual
TPA instruction fetches in both runs, and the admission gate requires zero Z80
prefixes and zero undocumented 8080 aliases across the complete sequence.

The extended sequence also proved that the simulator disk server must not use
a fixed whole-session deadline: the former 180-second limit could expire in a
healthy interactive run and mimic directory/CCP corruption. Active simulator
sessions are now unbounded and stop on transport EOF; the exact served image
is retained on failure for filesystem inspection.

The development cosimulation starts from `HELLO.ASM` assembled to Intel HEX
by the pinned host toolchain, converts it to `HELLO.COM` using target
`HEXCOM`, and executes the result. It then enters and exits `SID HELLO.COM`,
makes PATCH report SID's patch state, and drives ED through its real `: *`
prompt to insert, save, and read back `EDTEST.TXT`. Actual fetched TPA opcodes
across the sequence remain subject to the strict Intel 8080 execution gate.
