# External CP/M software and compiler audit

Status: **COMPLETE; NO EXTERNAL CANDIDATE ADMITTED BY THIS AUDIT**

This generated report closes the external-candidate and host-toolchain
items in the CP/M Plus feature plan. Passing a build or simulator test
is necessary but not sufficient for admission: provenance, overlap,
runtime cost, and completeness also apply. Exact records live in
`experiments/external-software/results.json`; checked patches preserve
the two source experiments without importing unexplained binaries.

| Candidate | Exact source | 8080 execution | Decision |
| --- | --- | --- | --- |
| `cpm-ls` 0.1b | Kevin Boone, GPLv3, `27bfbb29b0a4` | Pass | Defer from profiles |
| `HIST` RSX | z80pack image `91fd28eb04e6`; matching source/license absent | Not run | Reject |
| FIG-Forth 1.1 A0, 1979-09-17 | Cassady/Harris listing, gist `780a214ce9d9` | Pass, including `BYE` | Defer incomplete package |
| `uplm80` | GPLv3, `5546c476c291` | Fails CPU contract at generated assembly | Reject as production tool |

## cpm-ls

The intended project is [https://github.com/kevinboone/cpm-ls](https://github.com/kevinboone/cpm-ls) at `27bfbb29b0a4e4e0f4037b0d7745fce6a98b99f6`. It explicitly supports 8080 and Z80 and is GPLv3, so the earlier name/provenance uncertainty is resolved.

Upstream builds a checked-in 9,984-byte binary with Manx Aztec C 1.06d. The archived patch ports the same source to pinned z88dk, fixes byte-valued BDOS return handling and an FCB-name bounds bug, and reproducibly emits a 14,913-byte strict-8080 executable. It leaves 24,255 bytes below the measured TPA ceiling before runtime data and stack.

Measured on the same representative full A: image:

| Command | NetDisk reads | Records | Observed elapsed |
| --- | ---: | ---: | ---: |
| `DIR` | 3 | 9 | 6.222 s |
| `LS` | 55 | 165 | 23.550 s |
| `LS -L` | 188 | 564 | 69.955 s |

Decision: keep it planned and audited, but do not put it in `full` or
`dev` yet. `DIR`/`DIRSYS` cover ordinary listing, while the richer
sorting/size display currently has a disproportionate network and TPA
cost. A future indexed-directory service or a demonstrated workflow can
reopen admission without repeating the provenance and compiler work.

## HIST command-history RSX

The z80pack CP/M 3 image at `91fd28eb04e675c2127df88ed3f40675e15282e2` contains the behavior-reference `HIST.COM` and `HISTCL.COM` binaries. No matching source, independent license, CPU declaration, or build recipe exists in that tree. `HIST.UTL` is an unrelated Digital Research SID histogram utility, not the RSX source.

Decision: reject. The project does not execute or redistribute an
unlicensed, unexplained resident binary merely because another
distribution demonstrates useful behavior.

## FIG-Forth 1.1

The exact preserved listing (`8c69c5c6f0c5791d86170445b243753c8d75999be3bbc804d6c0a08c2fd6e2fb`) needs only three mechanical zmac compatibility edits. It builds to a 6,536-byte image with SHA-256 `aa7558d95d24ca9d3cf26f7d3637889cbcdbd880adcc5e0656aa62d62caecd55`. Strict simulation prints `fig-FORTH 1.1`, accepts `BYE`, returns to `A>`, and fetches neither Z80 prefixes nor undocumented 8080 aliases.

Decision: defer optional development-media packaging. The plan asks for
the language together with its editor, assembler, source, documentation,
and complete notice. The gist supplies only the core listing, and its
public-domain publication statement coexists with narrower copyright and
all-rights-reserved text that does not cover the missing components.

## Host compiler experiments

Pinned Millfork v0.3.30 and z88dk v2.4 each reproducibly build standalone `hello`, `cat`, and `wc` fixtures; all six pass strict-8080 execution. Millfork emits much smaller images and readable Intel assembly, while z88dk remains the preferable C portability probe.

| Toolchain | Program | COM bytes | Observed stack bytes | TPA left | Static instructions |
| --- | --- | ---: | ---: | ---: | ---: |
| Millfork | `hello` | 69 | 2 | 39,097 | 21 |
| Millfork | `cat` | 143 | 2 | 39,023 | 56 |
| Millfork | `wc` | 362 | 6 | 38,800 | 139 |
| z88dk | `hello` | 363 | 78 | 38,727 | 90 |
| z88dk | `cat` | 565 | 83 | 38,520 | 221 |
| z88dk | `wc` | 970 | 98 | 38,100 | 449 |

The flow-aware static disassembler accounts for every output byte,
follows only reachable code, and rejects undocumented/Z80-only
opcodes, direct hardware I/O, arbitrary `PCHL`, and control transfers
outside the image except CP/M warm boot and BDOS. The strict simulator
arms and freezes an SP low-water measurement around each representative
command; its broader fetched-opcode gate independently remains clean.
Exact listings are represented by stable SHA-256 digests in
`experiments/compiler-comparison/results.json`.

Hand-written 8080 assembly remains the production baseline. Neither
compiler becomes a required distribution build dependency. Millfork is
the preferred next high-level experiment; z88dk is retained for C ports.

`uplm80` revision `5546c476c291acdbd2d8a3c80501218f13f1608c` cannot replace the archived DRI PL/M-80 toolchain: its documented target is Z80, and exact `SETDEF.PLM` output contains 200 `JR` instructions at `-O2`; at `-O0` it still contains `SRL`/`RR`. Reconsider it only after a genuine Intel 8080 backend exists.

## Reproduction boundaries

`make external-software-audit-check` verifies the exact revisions,
decisions, hashes, TPA arithmetic, patches, strict-execution records, and
this generated report. `make external-software-rebuild-check` additionally
rebuilds cpm-ls and FIG-Forth when the pinned source trees/toolchains are
supplied explicitly; ordinary offline builds never download third-party
material.
