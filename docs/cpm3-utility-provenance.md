# CP/M 3.1 utility provenance

Status: **PINNED AND VERIFIED; NOT YET ADDED TO THE C4 BASELINE VOLUME**

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
and `HELP.HLP`. The HELP source mapping includes `setdef.help` and `dump.help`;
the pinned database exposes both topics.

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

This gate deliberately does not alter `out/cpm-plus-juku.img`. C4 remains the
immutable Priority 0 qualification volume. The separately named full and demo
profiles consume the staged files with generated contents, provenance,
free-space, and hash reports. The distribution cosimulation executes `SETDEF`,
`DUMP PROFILE.SUB`, and `HELP DUMP` through the production CP/M/NetDisk path,
then retains the normal warm-boot, write/erase, and B:-drive regression.
