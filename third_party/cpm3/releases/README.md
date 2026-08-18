# Pinned CP/M 3.1 utility release

These two unmodified archives are the 2026-06-07 CP/M 3.1 Unix source and
binary builds published by John Elliott at
<https://www.seasip.info/Cpm/software/dri.html>. The source release contains
the Digital Research sources and Unix build rules; the binary release was
produced from that tree. Upstream records the 2025 CCP/loader fixes, CP/M 3 Y2K
fixes, and HELP 1.1 patch level 5 in its archive README.

`provenance.json` pins both archive bytes and every utility selected by the
post-baseline full and development profiles.
`tools/extract_cpm3_utilities.py` refuses an archive, member, size, or digest
mismatch before exposing a `.COM` file to the volume builder. The archives
are inputs, not permission to add every contained binary to the Juku
distribution.

The optional development set is limited to HEXCOM, PATCH, and SID. Unlike the
PL/M programs, these three are reproducibly rebuilt from the mapped assembly
sources by `tools/rebuild_cpm3_dev_utilities.py`; their outputs must be
byte-identical to the pinned binary release before the dev image can pass.

Digital Research provenance and redistribution terms are recorded in
[`../LICENSE.md`](../LICENSE.md). No local claim of authorship is made for the
upstream sources or binaries.
