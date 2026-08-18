# CP/M 3 development-tool audit

Status: **COMPLETE; ED AND SID ADMITTED TO `development-a`**

This generated report closes the feature plan's individual DRI
`ASM`/`LOAD`/`ED`/`SID`/`RMAC` audit. It distinguishes programs that
may run on the Juku from opaque historical executables used only inside
the pinned host-side reproduction path.

| Program | Exact pinned evidence | Decision |
| --- | --- | --- |
| `ASM.COM` | Absent from both CP/M 3 archives | Do not ship |
| `LOAD.COM` | Absent from both CP/M 3 archives | Do not ship; use `HEXCOM` for Intel HEX |
| `ED.COM` | 9,254 B; PL/M/8080 sources; strict edit/save pass | Admit to `development-a` |
| `SID.COM` | 7,936 B; byte-identical source rebuild; strict load/quit pass | Admit to `development-a` |
| `RMAC.COM` | Exact build-input binary; matching source absent | Host-side ZXCC input only |
| `MAC.COM` | Exact build-input binary; matching source absent | Host-side ZXCC input only |
| `DRLINK.COM` | Exact build-input binary; matching source absent | Host-side ZXCC input only |

## Selected workflow

1. Edit source and text with ED.COM.
2. Build Intel HEX on the modern host with the pinned strict-8080 zmac path.
3. Convert HELLO.HEX on target with reproducibly rebuilt HEXCOM.COM.
4. Debug the resulting HELLO.COM with reproducibly rebuilt SID.COM.
5. Inspect binary patches with reproducibly rebuilt PATCH.COM.

This is intentionally a hybrid period/modern workflow. It is useful and
reproducible without pretending that source-less DRI assembler/linker
binaries satisfy the target-distribution admission rule.

## ED executable evidence

The development simulator boots the generated image, waits for ED's
actual `: *` prompt, sends the documented `Istring^Z` insertion, waits
for the next prompt, saves with `E`, returns to CCP, and reads the new
file back with `TYPE`. The command took 72 NetDisk reads and 4 synchronous writes in the observed run. ED's default uppercase translation is
retained and asserted rather than hidden by the harness.

## Build boundary

`SID`, `HEXCOM`, and `PATCH` rebuild byte-for-byte from archived 8080
assembly with pinned ZXCC/MAC/RMAC/DRLINK. ED has complete PL/M-80 and
assembly source plus the upstream GNU Make recipe, but recreating its
binary requires the original PL/M80/ASM80/Thames environment. The exact
maintained upstream binary is therefore checksum-pinned and executable-
tested, while those historical compilers do not become ordinary project
dependencies.

`make development-tool-audit-check` verifies both complete archive
hashes, every present/absent member, source mappings, profile isolation,
TPA arithmetic, simulator evidence, catalogue state, and this report.
`make development-cosim-check` executes the complete selected workflow.
