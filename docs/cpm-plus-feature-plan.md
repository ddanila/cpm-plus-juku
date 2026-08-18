# CP/M Plus post-baseline feature plan

Status: **COMPLETE THROUGH PRIORITY 7; PIP FIX SIMULATOR-ADMITTED, PHYSICAL CONFIRMATION PENDING**

This document complements the hardware- and ROM-focused
[`network-first-rom-plan.md`](network-first-rom-plan.md). That plan remains the
acceptance authority for the first automatic network-ROM release. This one
records the operating-system, distribution, native-BIOS, and service work that
becomes safe after that baseline is repeatable on physical Juku hardware.

The port is CP/M Plus 3.1 for the strict Intel 8080 and is deliberately
non-banked. A future feature must not weaken the stock-ROM/RAM-BIOS reference,
the 19,200-baud NetDisk-v3 baseline, or the measured 39,168-byte transient
program area.

## Priority 0: freeze the physical baseline

Before adding user-facing or protocol features:

- complete repeated cold boots, local display and keyboard, sequential read,
  write/erase, warm boot, host-loss, and live reconnect checks on CS00015;
- preserve exact ROM, CP/M payload, disk, host, and programmer hashes;
- either obtain the final V15 completion reply or explicitly accept a first
  valid NetDisk request as the independently recorded execution confirmation;
- reproduce every physical failure through real firmware branches and device
  timing in simulation;
- publish one immutable candidate package and its acceptance record.

Current state (2026-08-18): C4 and C5 are immutable hash-pinned references.
C5 physically passed the monitorless CS00015 matrix. C6 changes neither the C5
ROM nor its matching CP/M system bytes. On 2026-08-18 the exact C6 pair then
passed repeated automatic boot, A:/B:, sequential read, write/erase, warm boot,
diagnostics, local keyboard, sound, soak, host-loss, and live reconnect on the
same board. The production-path simulator supplies exact display/cursor
evidence, so hardware availability does not block the software release. A
later monitor-assisted C6 observation will close the physical visual boundary;
it is not completion evidence borrowed by the simulator artifact.

The compatibility adapter remains the reference until a replacement matches
this matrix. Higher baud rates, write-back caching, and additional recovery
menus are not release blockers.

## Priority 1: usable system distribution

The current A: image is a deliberately small qualification volume. Turn it
into a useful CP/M Plus distribution without mixing hardware bring-up with
unreviewed binaries:

- add legally redistributable CP/M Plus utilities such as `PIP`, `SHOW`,
  `SET`, `DEVICE`, `DATE`, `SUBMIT`, and `HELP` where their provenance permits;
- retain a minimal recovery A: profile containing CCP, diagnostics, status,
  disk tools, and documentation;
- provide a separate applications/games B: image using native Juku geometry;
- support `PROFILE.SUB` or an equivalent configurable initial command;
- add an opt-in museum/demo profile only after normal warm boot and reconnect
  remain deterministic;
- generate volume contents, provenance, free-space reports, and hashes from
  the reproducible build.

No third-party tool enters a distributed image without a recorded source,
license, version, and checksum.

Preparation completed on 2026-08-17: the maintained 2026-06-07 CP/M 3.1
source/binary release is pinned locally, and the eight initially selected files
are checked against source-member mappings, sizes, and SHA-256 before
extraction. They remain absent from the immutable C4 volume and are now present
only in the separately named full/demo profiles. See
[`cpm3-utility-provenance.md`](cpm3-utility-provenance.md).

Distribution implementation completed on 2026-08-17: declarative profiles now
produce a byte-identical named C4 recovery A:, a licensed full A:, an opt-in
`PROFILE.SUB` museum A:, and a physical cylinder/head native B: containing
only approved project material. Deterministic reports include contents,
provenance, allocation, free space, and hashes. Cosimulation runs the CCP
profile, the normal disk/read/write/warm-boot matrix, and B: selection, listing,
and transient loading through the production host conversion. The mixed-license
Juku 3000 game disks remain checksum-recorded external read-only inputs rather
than being silently redistributed. See
[`distribution-profiles.md`](distribution-profiles.md) and
[`juku3000-media-provenance.md`](juku3000-media-provenance.md).

## Priority 2: native CP/M 3 BIOS services

The existing 32-entry CP/M 3 BIOS is genuine, but deliberately delegates the
first seventeen hardware calls to the qualified CP/M-compatible adapter and
keeps several optional CP/M 3 entries conservative. Replace these only in
measured, independently testable increments:

- provide a real character-device table and CP/M 3 console/list/auxiliary
  assignment rather than placeholder device entries;
- implement host-supplied date/time through the CP/M 3 `TIME` call without
  making boot or disk availability depend on a clock server;
- evaluate `MULTIO` against bounded NetDisk multi-record replies;
- give `FLUSH` explicit semantics before introducing any write cache;
- make device initialization and live status report useful configuration and
  failure information;
- keep `MOVE` verified for overlap and boundary behavior;
- retain bank selection and cross-bank movement as documented stubs unless
  real banked memory hardware is added.

Each native service must retain a compatibility fixture and prove the same
command, framebuffer, disk, reconnect, and memory-map behavior before it
replaces the adapter path.

First native slice completed on 2026-08-17: separately named network-ROM
artifacts now provide the real `JUKU` character-device table, device/status
semantics, A-register `MULTIO` recording, explicit synchronous `FLUSH`, an
overlap-safe strict-8080 `MOVE`, raw/decoded S21 through versioned USERF, and a
target-side executable regression. The normal command/framebuffer matrix and
compound NetDisk recovery pass without changing C4 or its 39,168-byte TPA.
The follow-up TIME slice now provides optional host GET and session-offset SET
with atomic SCB commit, exact HL/DE preservation, target-side SET/GET checks,
and no dependency from boot or disk. See
[`cpm3-native-services.md`](cpm3-native-services.md).

## Priority 3: configuration, console, and localization

- consume the ROM-latched S21 configuration through a versioned ABI query;
- use S21 bit 0 for the final automatic-network-boot policy;
- share S21 bits 2:1 between ROM and CP/M for 40x24, 53x24, 64x20, and 80x24;
- expose raw and decoded S21 values in both host logs and a target status tool;
- add selectable English, Estonian, and Russian translation/font banks without
  duplicating the renderer;
- retain the edge-connected CP437 pseudographic subset for text interfaces;
- add a small per-machine key remap for dead or nonstandard keys;
- consider ROM-assisted clear, scroll, or bulk console output only when its
  measured call-gate cost beats the current helper;
- add a bounded bulk N4 output operation if character-at-a-time remote output
  becomes a practical debugging bottleneck.

Local screen and keyboard remain authoritative when remote console service is
absent, interrupted, or rejected.

Status slice completed on 2026-08-17: native USERF selector 1 now samples S21
and publishes raw S21, decoded video mode, native feature flags, and last clock
status through idempotent NetDisk-v3 operation 24h. `STATUS.COM` prints the
same configuration plus resident map and build/protocol identities. The C4
recovery image remains immutable; a separately named native recovery profile
adds the utility. Shared code now provides optional English, Estonian, and
CP866 Russian font extensions selected by S21 bits 4:3 without duplicating the
renderer, retains the connected CP437 UI range, and offers a bounded four-pair
resident key remap. Their pinned MIT/public-domain sources and generated rows
have independent oracles. Exact measurement rejects enabling them in the
already 3,989-byte compatibility adapter. The separate ABI 1.1 C5 desk image
now uses 1,128 bytes of the network ROM's reserved console/locale bank, exposes
reset-latched configuration and four-pair remapping through appended vectors,
and implements S21 bit 0 as immediate autoboot versus a concealed local-`N`
recovery wait. Its matching CP/M image consumes the latched byte and reports
the locale. The resident ROM and CP/M binding now share all four S21 video
geometries; independent 9,600-byte framebuffer oracles pass for every mode.

ABI 1.2 C6 completes the conditional console work: one gate call renders a
1..256-byte span, while USERF selector 5 sends a duplicate-safe 1..32-byte N4
span when the host advertises it. Separate local-only and N4-complete CP/M
runs prove that remote service cannot replace or starve the authoritative
local display and keyboard. The raw-key vector and `KEYRAW.COM` expose
untranslated matrix state without weakening the translated console path.

## Priority 4: diagnostics and observability

Grow the shared `DIAG` and status facilities from the same `juku-common`
sources used by ROM diagnostics:

- CPU, memory/address, RAM, PIT, USART, video, keyboard, refresh, and ROM-ABI
  tests, with destructive tests clearly separated;
- a resident memory-map report covering loader, BDOS, BIOS, adapter, TPA top,
  ROM ABI, and mutable work areas;
- concise ROM, CP/M system, protocol, disk-image, host, and build identities;
- raw/decoded S21 configuration and active video/locale settings;
- the last POST stage, bootstrap retry/failure reason, cold/warm marker, disk
  recovery reason, and server reconnect count;
- an unattended machine-readable result channel over N4 that cannot starve
  disk or local console service.

The ROM should retain a small fixed RAM boot-status record so failures can be
explained after recovery or on a machine without a monitor.

Observability implementation completed on 2026-08-17: `STATUS.COM` reports the
resident map, system/ROM/protocol identities, S21/video configuration, MULTIO,
clock counters, reset POST status, cold/warm state, last disk status/attempt
state, and N4 failure/reconnect state, and mirrors its compact configuration
tuple to host logs. The simulator proves the cold-to-warm transition and keeps
the C4 ROM artifacts byte-identical. C5 now retains POST, V15 core, extension,
system-header, CRC-retry, authenticated/decompression, CP/M-entry, and first
successful-disk stages at D610h..D613h. `STATUS.COM` 1.2 displays that record
and publishes it through bounded, duplicate-safe operation 27h; ABI 1.0
publishes a deterministic zero tuple. The regression corrupts one compressed
stream, observes the retained retry, and then proves recovery through stage
`50h` with matching host and target counts.
The safe shared diagnostic matrix is now implemented in Diag 0.5:
CPU/memory, D57, D11, ROM/integrity, video, keyboard/S21, and combined suites
use `juku-common` probes and publish a bounded machine-readable result over N4.
Destructive tests are explicitly refused under live CP/M and remain a ROM-only
responsibility. The immutable C4 image retains Diag 0.4; post-C4 profiles opt
into Diag 0.5. See [`cpm3-diagnostics.md`](cpm3-diagnostics.md).

## Priority 5: NetDisk performance and media safety

Retain measured `DIR`, sequential-read, and write baselines for every change,
separating wire, target copy/CRC, console, and host scheduling time.

- cache predictable directory and allocation records;
- keep independent per-drive read-ahead and invalidation state;
- coalesce bounded sequential records and compare them with CP/M 3 `MULTIO`;
- add a protocol capability exchange rather than inferring features from a
  banner or host identity;
- support multiple host-advertised volumes and native Juku B: geometry;
- provide explicit read-only, writable-copy, and snapshot-backed modes;
- preserve synchronous write-through as the correctness baseline;
- introduce write caching only with specified flush, warm-boot, retry,
  disconnect, and power-loss behavior;
- keep NetDisk v3 as the compatibility path when experimenting with a later
  block-transfer protocol.

Directory prefetch and bounded sequential coalescing are the first performance
experiments. They have high expected value and do not require risking a write
cache.

Safety/capability slice completed on 2026-08-17: the host defaults to
read-only A: and provides explicit synchronous write-through, full writable
copy, and sparse snapshot modes with atomic persistence and base-image hash
validation. B: remains read-only. NetDisk-v3 operation 26h now provides an
explicit, bounded, duplicate-safe capability reply containing protocol,
maximum read-ahead, feature flags, and drive count; `STATUS.COM` displays it.
The C5 slice now retains independent A:/B: read-ahead buffers and validity
metadata, with an alias-safe fallback for ABI 1.0 consumers. Its alternating
B: -> A: regression leaves both entries live after loading a transient from
each drive. Its explicit eight-record setting reduces initial A: login from 22
turns to 10, B: login from 11 to 4, and `TYPE` from 2 to 1 while preserving the
zero-turn `DIR` and flat measured wire volume. CP/M's existing directory state
already supplies the useful directory cache; a second protocol cache is
rejected. MULTIO-aware bulk DMA is deferred because the translated predictor
already fills eight records and the visible workloads show no remaining
benefit that would justify another ABI/protocol.

C6 nevertheless provides the bounded ordered multi-request ABI required by
the architecture. Its executable fixture mixes invalidations through the same
single-request implementation and rejects zero/oversized lists. Production
CP/M continues using the measured eight-record predictor because no current
workload justifies replacing it merely to exercise the new vector.

The immutable three-record baseline is pinned by
[`netdisk-performance.md`](netdisk-performance.md): login costs 22 turns, the
first interactive `DIR` costs zero further wire turns, and `TYPE README.TXT`
costs two. C5/C6 supersede that performance result with independently bounded
eight-record A:/B: caches and measured 10/0/1 turns. Explicit operation-26h negotiation also
eliminates 186 rejected N4 discovery polls from a representative disk-only
session. The next disk experiment must therefore target initial login or
first/alternating drive selection; steady-state `DIR` is already local.

## Priority 6: manifests and recovery policy

- add a host-visible boot manifest containing length, load and entry address,
  protocol/ABI requirements, and build identity;
- let the host advertise available system and data images without Janet
  station identity;
- consider two system slots or a last-known-good server image;
- expose capability negotiation for ROM ABI, NetDisk, console, time, and
  diagnostic services;
- keep recovery selection automatic or concealed until the network-only
  baseline is stable—do not regrow a mandatory ROM menu;
- treat baud rates above 19,200 as separately named experiments, retaining the
  proven mode-2/count-4 clock as production default.

Cryptographic authentication is deferred until its EPROM, wire, and 8080
decode costs are measured. Checksums and reproducible build identities remain
mandatory.

Initial manifest slice completed on 2026-08-17: the reproducible build now
generates a host-visible manifest containing system load/entry/length/CRC,
system and versioned fastboot hashes, ROM-ABI/NetDisk/baud requirements, build identity, and
all named A:/B: profiles with geometry and media policy. The production host
can reject stale artifacts before opening the serial device and records the
manifest identity in timing evidence. This is station-identity independent.
The on-wire target capability query is now implemented as operation 26h and is
kept distinct from the build/media manifest. The manifest now binds native and
immutable C4-compatible system/bootstrap slots; the host exhausts one bounded
restart budget before automatically trying the other and atomically promotes
a slot only after the first valid disk request proves execution. A matching
last-known-good slot is preferred on the next run. See
[`boot-manifest.md`](boot-manifest.md).

## Priority 7: curated 8080 software and development environment

Status: **COMPLETE**

The completed C6 platform is now stable enough to grow into a curated CP/M
Plus distribution. This is distribution work, not a reason to reopen the
network-ROM or native-BIOS baseline. Every target binary must run on a real
Intel 8080; "runs under CP/M" is not sufficient evidence because much later
CP/M software silently requires a Z80.

### Admission gate

Before adding any third-party executable to a generated image:

1. pin its upstream revision, source, license or public-domain notice, build
   recipe, output size, and SHA-256;
2. build it reproducibly where source permits rather than importing an
   unexplained `.COM` file;
3. reject Z80-only opcodes with a static instruction audit, then execute the
   useful paths under the strict-8080 simulator;
4. test it under this non-banked CP/M Plus 3.1 port with the 39,168-byte TPA,
   including normal return to CCP and warm boot;
5. measure disk allocation and runtime memory before choosing a profile;
6. preserve license/credit text in a generated software manifest and, where
   practical, CP/M `HELP` topics.

An emulator or distribution repository may be a source of ideas and test
cases without making every binary inside it redistributable or 8080-safe.
"Open-source-ish" is not acceptable provenance.

### First distribution slice

- Add the pinned DRI `SETDEF.COM`, source mapping, help topic, and checksum to
  the full profile. Validate drive search paths and `COM`/`SUB` search order
  instead of inventing a Unix-like `PATH` mechanism. The current pinned CP/M
  3.1 archives contain `SETDEF.COM`, `setdef.plm`, and `setdef.help`; their
  later admission is recorded in the completed slice below.
- Audit DRI `DUMP.COM` next. Prefer it over a new hexdump until a measured gap
  is found; its binary, assembly source, and help topic are also present in the
  pinned archives.
- Audit Kevin Boone's exact GPLv3 `cpm-ls` source and compare its value against
  CP/M `DIR`, `DIRSYS`, and any legally available `SDIR` before shipping an
  overlapping command. A successful 8080 build alone does not establish that
  its TPA and NetDisk costs belong in a default profile.
- Evaluate `HIST` as an optional CP/M 3 RSX. Acceptance requires strict-8080
  code, a traceable license, measured resident-memory/TPA cost, clean removal,
  and correct interaction with both local and N4 console input across warm
  boots. The z80pack CP/M 3 image is a useful behavior reference, not a binary
  source to import wholesale.
- Keep the recovery profile small. Put convenience tools in `full`; introduce
  a separately named `dev` profile for assemblers, editors, debuggers, source,
  and language systems.

First slice completed on 2026-08-18: the pinned `SETDEF.COM` and `DUMP.COM`
bytes, `setdef.plm`/`dump.asm` source mappings, HELP topics, sizes, and SHA-256
records are admission-gated and present only in the full/demo profiles. The
production-path simulator executes `SETDEF`, dumps the known `PROFILE.SUB`
bytes, enters `HELP DUMP`, exits HELP deliberately, and then completes the
ordinary framebuffer, warm-boot, write/erase, and native-B regression. The
test harness now includes extra-command output in its independent framebuffer
oracle; previously those commands could run without contributing to the final
visual comparison.

Development slice completed on 2026-08-18: a separately named `development-a`
profile extends `full-a` with ED, HEXCOM, PATCH, SID, `HELLO.ASM`, and its
reproducible Intel HEX output while leaving recovery/full/demo bytes
unchanged. HEXCOM, PATCH, and SID rebuild byte-for-byte from their pinned
assembly sources with archived MAC/RMAC/DRLINK under pinned ZXCC. ED has a
complete PL/M-80/assembly mapping and pinned maintained binary. The strict-
8080 simulator converts and executes HELLO, enters/exits SID, exercises PATCH,
then inserts, saves, and reads back a new file with ED. The image has 200 KiB
free and is advertised in every generated boot manifest and included in the
reproducible C5/C6 packages.

Do not duplicate established CP/M commands merely to give them Unix names:
`TYPE` already covers the ordinary `cat` case, `PIP` copies files, `REN`
renames them, and `ERA` removes them. After the first slice, prioritize actual
gaps such as `CMP`, CRC/checksum, text search, `WC`, `STRINGS`, and a compact
hex/ascii view. `HEAD` and `TAIL` remain lower priority until a real workflow
needs them.

### Machine and diagnostic tools

`STATUS.COM` is already the Juku equivalent of the proposed `SYSINFO`: it
reports CP/M/profile and build identities, protocol and ROM ABI, TPA and
resident map, S21/video/locale state, clock status, retained boot state,
diagnostics, capabilities, drives, and reconnect information. Extend it only
for measured omissions rather than adding a second overlapping command.

Candidate project utilities are:

- a bounded `MEM`/`DUMP` view and file `CMP`/CRC tools;
- safe timing and clock diagnostics that build on the existing TIME service;
- an optional developer-only, allow-listed I/O probe.

Do not ship an unrestricted `PORT` utility in recovery or museum profiles.
Reads as well as writes can acknowledge, reset, or otherwise disturb real
peripherals, so direct-I/O diagnostics must use an explicit safe-port list and
separate destructive operations.

Gap-filling utility slice completed on 2026-08-18: the separately generated
full/demo/dev profiles now include project-owned `CRC`, `CMP`, `MEM`, `WC`,
`FIND`, and `STRINGS` commands plus target-side `TOOLS.TXT`. Their exact
positive and negative behavior runs under the fetched-opcode strict-8080
simulator gate. MEM is read-only and capped at 40h bytes. Existing STATUS,
DATE, DIAG PIT, and native TIME tests satisfy the safe timing/clock item; the
maintained diagnostic suites remain the hardware-port allow-list, so no
unrestricted or duplicate `PORT` command was added. See
[`project-utilities.md`](project-utilities.md).

External-software slice completed on 2026-08-18: Kevin Boone's exact GPLv3
`cpm-ls` 0.1b source is identified, patched reproducibly for pinned z88dk, and
passes strict-8080 CP/M 3 execution. It remains out of generated profiles by a
measured decision: ordinary `LS` takes 55 NetDisk reads and 23.550 seconds on
the representative full disk versus three reads and 6.222 seconds for `DIR`;
`LS -L` takes 188 reads and 69.955 seconds, while the ported executable itself
uses 14,913 bytes. The z80pack `HIST` behavior-reference binaries are rejected
because matching source, license, CPU contract, and build recipe are absent.
The FIG-Forth core listing builds, starts, accepts `BYE`, and returns to CCP
under strict simulation, but its optional package remains deferred because the
editor, assembler, documentation, and a clear complete-package notice are
missing. See [`external-software-audit.md`](external-software-audit.md).

### Optional development media

- Audit the CP/M 8080 FIG-Forth 1.1 source and its complete notice. If it
  builds and passes the strict-8080/CP/M 3 matrix, package it with its editor,
  assembler, source, and documentation on optional development media, not the
  recovery disk.
- Audit the DRI `ASM`, `LOAD`, `ED`, `SID`, `RMAC`, and related sources and
  binaries individually. Include only the subset with clear provenance that
  fits a useful, reproducible development workflow.
- Use z80pack as a CP/M 2.2/3 behavior and software-catalog reference. Its
  emulator is MIT licensed, but bundled historical software still needs its
  own source, CPU, and license audit.
- Use RomWBW as a modern CP/M usability catalogue only. Its supported systems
  are Z80/Z180/Z280 and its aggregate contains independently licensed pieces;
  neither its binaries nor its hardware layer are candidates for direct Juku
  import.
- LokiOS is Z80-only and remains an ideas reference, not a port dependency.

DRI development-tool audit completed on 2026-08-18: ED and SID are admitted
to `development-a` with exact source mappings and strict-8080 workflows. The
pinned `ASM.COM` and `LOAD.COM` candidates do not exist in either exact CP/M 3
archive, so they are not imported from an unrelated distribution; HEXCOM
already converts host-produced Intel HEX. RMAC, MAC, and DRLINK exist only as
source-less executable inputs needed by the upstream/local reproduction path.
Their exact bytes remain host-side under ZXCC and are forbidden from generated
target profiles. [`cpm3-development-tools.md`](cpm3-development-tools.md)
records and checks all seven individual dispositions.

### Host-side compiler experiments

Keep hand-written assembly and the existing tools as the trusted baseline,
then run a small, pinned compiler comparison for new utilities:

- compile the same `hello`, file-copy/`cat`, and `wc` programs with z88dk and
  Millfork for Intel 8080 and CP/M;
- compare `.COM` size, stack and TPA usage, BDOS ABI correctness, runtime on
  representative files, diagnostics, reproducibility, and ease of debugging;
- disassemble every result and fail the build on Z80-only opcodes or an
  unapproved runtime dependency;
- select a compiler only on evidence; generated programs remain standalone
  and require no compiler runtime installed on the Juku.

Also evaluate `uplm80` as a host-side route for rebuilding and modifying the
existing DRI PL/M-80 utilities from their pinned sources. Its current backend
describes Z80 output, so it must pass the same strict-8080 opcode gate before
it can become a production tool; its ability to consume the original CP/M 3
PL/M sources makes it worth a focused experiment.

Compiler experiment completed on 2026-08-18: pinned Millfork v0.3.30 and
z88dk v2.4 reproducibly build matching standalone `hello`, `cat`, and `wc`
fixtures, and all six binaries pass strict-8080 CP/M 3 execution. A flow-aware
static disassembler now accounts for every byte as reachable code or data and
rejects undocumented/Z80-only opcodes, direct hardware I/O, unresolved
indirect transfers, and external control dependencies other than CP/M warm
boot and BDOS. Its canonical complete listings are pinned by digest. A
command-scoped simulator low-water measurement observes 2/2/6 bytes of stack
for Millfork `hello`/`cat`/`wc` and 78/83/98 bytes for z88dk, leaving
39,097/39,023/38,800 and 38,727/38,520/38,100 TPA bytes respectively after
image plus observed stack. The strict rebuild gate reproduces the binaries,
static audits, representative behavior, and exact stack results.

Millfork produces the smallest images and clearest generated Intel assembly,
so it is the preferred future high-level experiment; z88dk remains the C
portability probe. Hand-written 8080 assembly remains the production baseline,
and neither compiler is a mandatory distribution dependency. Exact DRI
`SETDEF.PLM` compilation rejects `uplm80` as a production path: `-O2` emits
200 `JR` instructions, while `-O0` still emits Z80-only `SRL` and `RR`. The
pinned fixtures, sizes, hashes, TPA accounting, rebuild command, strict
simulator results, and fail-closed gates are recorded under
`experiments/compiler-comparison/`.

### Explicit exclusions

- Do not add XMODEM. NetDisk/N4 already supplies faster, checksummed,
  reconnectable file and disk access integrated with the host, while XMODEM
  would compete for the same physical USART and require a second ownership
  mode without filling a project need.
- Keep the port non-banked. The current hardware and 39,168-byte TPA are the
  acceptance baseline; banked CP/M Plus becomes a separate future project
  only if real Juku memory hardware is designed, built, and characterized.

### Deliverable

Produce a candidate catalogue of roughly 20--30 source-available programs
with upstream URL/revision, author, license, CPU requirement, source language,
build method, `.COM` size, TPA use, CP/M 3 test result, and proposed profile.
The catalogue drives selection; it does not authorize all candidates for
redistribution. Add automated opcode, manifest, build-reproducibility, and
strict-8080 smoke gates before expanding the generated full/dev images.

Catalogue slice completed on 2026-08-18: 23 exact DRI CP/M 3.1 `.COM`
candidates now have pinned source-member lists, source language, upstream
build method, binary size/hash, static C6 TPA span, test state, and proposed
profile in a generated catalogue. Its validator checks both complete archive
hashes, every source member and binary, the 20--30 entry bound, profile/status
consistency, and the admitted full-profile set; mutations to each boundary are
required to fail. `make utility-catalogue-check` is part of `make check`.

Static-instruction slice completed on 2026-08-18: every one of the 13 admitted
DRI executables has a complete, canonical flow-aware 8080 listing and a pinned
listing hash. The gate rejects reachable undocumented/Z80 aliases, direct
hardware I/O, arbitrary external transfers, and unannotated indirect control
flow. Exact source-backed policies cover PL/M `DO CASE` tables, PATCH's
non-returning `STOP`, and the executable components hidden by CP/M 3 container
formats. In particular, it separately audits the normal transient and RSX in
GENCOM-built `SET`/`SUBMIT`, plus SID's relocator and linked debugger module;
unused annotations fail so a stale exception cannot quietly weaken coverage.
The binary archive hash still accounts for every header, relocation bitmap,
padding byte, and data byte outside those executable paths.

Runtime-memory slice completed on 2026-08-18: all 13 shipped DRI programs now
run on the C6 network-first ROM and native BIOS with the exact 39,168-byte TPA,
return to CCP, and freeze a command-scoped stack checkpoint before warm boot.
The two profile matrices select ABI 1.2/V16 explicitly, and their metrics must
match the exact C6 ROM, extended system, and Fastboot SHA-256 identities; the
shared ABI 1.0 default is no longer accepted as indirect C6 evidence.
The admission gate binds each useful command to its C6 entry SP, private-stack
anchor and low-water mark, segment/SP-write counts, loaded transient size,
GENCOM RSX size where applicable, 2,048-byte disk allocation, and remaining
TPA. Full and development volume reports are cross-checked, and eight negative
mutations prove the gate fails closed. The observed workload peaks range from
6 to 20 bytes, while the smallest runtime headroom is 29,914 bytes. These are
named-workload regression measurements rather than unsupported worst-case
claims. See [`cpm3-runtime-memory.md`](cpm3-runtime-memory.md).

The shared C simulator now records actual instruction fetches, not byte-pattern
guesses, over `0100h..99FFh`. The distribution regression requires nonzero TPA
execution with zero fetched Z80 prefixes and zero undocumented 8080 aliases
while running every shipped DRI executable. The completed path covers
`SETDEF`, exact `DUMP`, `HELP`, `PIP` create/copy, `SHOW`, `SET` attribute
changes, `DEVICE NAMES`, `DATE` validation, and `SUBMIT` error handling,
then proves warm boot and both drives. All nine shipped `.COM` rows now require
`strict-8080-cosim`; downgrading even one row fails the catalogue audit.

The longer sequence exposed and fixed a simulator-only 180-second whole-session
deadline which had looked like target directory/CCP corruption. Active disk
sessions now run without a wall-clock limit, stop cleanly at transport EOF,
and retain the served image on failure. It also confirmed that `DEVICE` belongs
on the native-BIOS admission path: `DEVICE NAMES` must report the fixed `JUKU`
input/output entry there. Keeping it out of the placeholder RomBios DEVTBL path
preserves every qualified RomBios and C4/C5/C6 SYS byte.

Research starting points: [z80pack](https://github.com/udo-munk/z80pack),
[z88dk](https://github.com/z88dk/z88dk),
[Millfork](https://github.com/KarolS/millfork),
[uplm80](https://github.com/avwohl/uplm80),
[RomWBW](https://github.com/wwarthen/RomWBW), and the preserved
[8080 FIG-Forth 1.1 source](https://gist.github.com/tschak909/c45014672024b15b5244576783d011c1).
These links identify candidates and references only; the admission gate above
still applies to every imported source and binary.

## Completion order

1. Freeze and publish the physical network-first baseline.
2. Build a useful, licensed, reproducible A:/B: distribution.
3. Add status, shared diagnostics, boot records, and complete S21 integration.
4. Implement date/time and character-device support as native CP/M 3 calls.
5. Improve read performance and multi-volume media handling.
6. Add further native BIOS and protocol features only with measured benefit.
7. Curate strict-8080 utilities, then add optional development media from the
   audited catalogue.

This order keeps the already successful port usable at every milestone and
prevents performance or convenience work from obscuring hardware regressions.

## Completion audit (2026-08-18)

| Priority | State | Authoritative evidence |
| --- | --- | --- |
| 0. Frozen baseline | **Complete** | C4/C5 are immutable and hash-pinned; C5 booted CS00015 in 6.268 s. The exact C6 pair later passed the CS00015 blind boot, keyboard, sound, disk, diagnostic, write, warm-boot, soak, and reconnect matrix; display/cursor observation remains separate. |
| 1. Distribution | **Complete** | `distribution-check`, deterministic profile reports, provenance checks, native B: conversion, and distribution cosimulation pass. |
| 2. Native BIOS | **Complete** | `native-services-check` executes the character table, TIME, MULTIO, FLUSH, MOVE, USERF, status, diagnostics, and recovery paths. |
| 3. S21/console/locale | **Complete** | Four exact framebuffer oracles, ABI 1.1 configuration/remap tests, locale source oracles, 53x24/64x20 CS00015 evidence, and C6 local/N4 block-output separation. |
| 4. Diagnostics/observability | **Complete** | Diag 0.5 covers the safe shared matrix; Status 1.3 preserves its status-block pointer across BDOS output and is checked by exact transcript lines; operations 24h/25h/27h cover configuration, diagnostics, and retained bootstrap state. |
| 5. NetDisk/media safety | **Complete for the selected design** | The pinned 10/0/1 boot/DIR/TYPE counts, per-drive cache oracle, ordered multi-request service, explicit capabilities, media policies, synchronous-write recovery, and 64-cycle read/write/reconnect soak pass. Write-back caching remains deliberately out of scope. |
| 6. Manifest/recovery | **Complete** | C6 manifest validation, station-independent media advertisement, two bounded system slots, last-known-good promotion, immutable C4 fallback, complete vector/map export, and byte-reproducible package pass. |
| 7. Curated software/development | **Complete** | The 23-program DRI catalogue, every shipped DRI executable, ED/HEXCOM/PATCH/SID development image, and six project-owned gap tools pass strict-8080 execution. Exact `cpm-ls`/`HIST`/FIG-Forth decisions, seven individual DRI development-tool dispositions, Millfork/z88dk/uplm80 experiments, and live C6 disk/stack/RSX/TPA evidence for all 13 shipped programs are complete and fail-closed. |

`make check` is the complete ordinary desk gate. `make bench-candidate` additionally
rebuilds the immutable C4 package and proves that incomplete or tampered
physical evidence cannot pass the recorder audit. Those C5 commands preserve
their historical physical-promotion semantics.

`make release-candidate` remains the C5 desk packaging gate. It binds the ABI
1.1 C5 ROM and exact D15/D16 halves to the matching locale-native CP/M Plus
3.1 system, C4 fallback, published media/reports, license, and notice in a
byte-reproducible tar. This completes every desk-executable item in the frozen
C0--C6 baseline. Priority 7 subsequently completed the separately generated
full and development distribution profiles without changing those artifacts.
It deliberately does not promote C5: the blind hardware matrix passes, but the
display/cursor gate remains. See
[`cpm-plus-31-c5-release-candidate.md`](cpm-plus-31-c5-release-candidate.md).

`make c6-release-candidate` is the completed C0--C6 baseline gate. It rebuilds ABI 1.2,
runs its executable C/HDL boundaries, both local and N4 CP/M paths, the full
64-cycle read/write/reconnect soak, manifest and fallback checks, then creates
and independently reproduces the C6 simulator package. The later exact C6 pair
passed every monitor-independent physical item on CS00015. See
[`cpm-plus-31-c6-simulator.md`](cpm-plus-31-c6-simulator.md),
[`cs00015-c6-blind-qualification-20260818.md`](cs00015-c6-blind-qualification-20260818.md),
and [`plan-completion-audit.md`](plan-completion-audit.md).

For monitorless completion of the keyboard portion, the post-C4 profiles now
include `KEYTEST.COM`. Its single-key mode reports unbuffered local key codes
through N4; its `KEYTEST B` mode captures a complete line before reporting so
serial output cannot stall the polled keyboard between keys. Both have bounded
exits, and buffered mode passes an exact simulator transcript including Space
and Enter. A working external display is still required to complete C6's
physical visual promotion, but exact framebuffer/cursor oracles satisfy the
simulator-release scope of that completed baseline.

## Post-C6 maintenance and improvement roadmap

This roadmap begins after the completed C0--C6 and Priority-7 implementation
audit. It does not rewrite the immutable C4/C5 references or require a new ROM
ABI merely because a loaded CP/M system or its tests need maintenance.

### Goal and completion definition

The immediate goal is to turn the working C6/Priority-7 system into a
repeatably qualified physical baseline: a fresh operator must be able to run
the complete full and development workloads on CS00015, retain independently
auditable evidence, and obtain the same result without relying on remembered
blind keystrokes or optimistic interpretation of host disk traffic.

Two physical gates remain for that baseline:

1. retain passing full and development M2 evidence bundles; the full run must
   include the corrected multi-record `PIP` copy and CRC `4613` required by M1;
2. when a working display is available, run the four-mode M3 visual test and
   distinguish genuine framebuffer faults from monitor-specific cropping.

M4--M6 are subsequent improvements, not hidden release blockers. Their goals
are measured NetDisk responsiveness, a more useful strict-8080 distribution,
and reproducible per-machine diagnosis. Each must preserve the immutable
C4/C5 recovery references, the accepted C6 ABI and ROM, synchronous write
safety, 19,200-baud reference transport, and strict-8080 compatibility. Higher
baud rates, write-back caching, authenticated boot, and banked CP/M Plus remain
separately named research projects rather than implicit extensions of this
baseline.

### Current decisions and next actions

No new EPROM is required for the remaining M1--M3 acceptance work: C6 already
contains the required ROM ABI, while the corrected system, physical runner,
and `VIDTEST.COM` are network-loaded. Proceed in this order:

1. run the full M2 workload on CS00015 and retain its passing evidence bundle;
   this also closes M1 by exercising the corrected four-record PIP copy and
   checking CRC `4613`;
2. run the development M2 workload and retain its independent evidence bundle;
3. when a working display is available, run the M3 display workload once in
   each of the four S21 video modes and record geometry, cursor behavior,
   cropping, monitor identity, and photographs;
4. only then start M4 with a fresh measured baseline for cold login, first A:,
   first B:, alternating drives, sequential reads, and synchronous writes;
5. start M5 with a strict-8080 command-history prototype and a concrete
   pseudographic text-interface tool, admitting either only after the same
   source, license, size, memory, and exact-C6 execution gates as current
   utilities;
6. keep M6 work machine-specific: investigate CS00000's USART and CS00024's
   RAM/refresh/D57 evidence only on those machines, without changing CS00015's
   known-good reference behavior.

M4 and M5 should normally remain network-loaded system/media changes. A C7 ROM
is justified only when a measured improvement requires a new resident service
or ABI and cannot be implemented safely by the host, BIOS, or transient
program. Do not spend physical runs on catalogue exploration or changes that
have not already passed the simulator and fault-injection gates.

The repository-wide M1 regression also made the C4 build boundary explicit:
the stock-ROM/RAM-BIOS and network-ROM C4 system/V15 pairs are consumed from
their hash-checked prebuilt files, whose source boundary is cpm-plus-juku
`6ce52d8` plus juku-common `aeee23d`. Later common fonts and keyboard routines
no longer force an overlapping relink or silently alter either physical
recovery slot.
The physically qualified C5 system/V15 pair is likewise consumed from pinned
prebuilt files. Its source boundary is cpm-plus-juku `e970088` plus
juku-common `04c2541`; post-C5 systems must receive a distinct identity.
Simulator acceptance treats those frozen artifacts the same way: their exact
hashes and recorded physical qualification are authoritative, while current
source-font oracles apply to current relinks. A frozen C4 framebuffer is still
captured and compared byte-for-byte with the corresponding resident-ROM path;
it is not reinterpreted through a renderer from a later source boundary.

### Immediate goal: multi-record PIP correctness

Restore a truthful, hardware-qualified Priority-7 distribution by fixing
multi-record `PIP` copying, strengthening its simulator admission workload,
and verifying the corrected loaded system once on CS00015.

The 2026-08-18 blind Priority-7 run exercised all 13 admitted DRI programs and
all six project-owned utilities through C6/N4. `SETDEF`, `DUMP`, `HELP`,
`SHOW`, `DATE`, `SUBMIT`, `DEVICE`, `SET`, `HEXCOM`, `SID`, `PATCH`, and `ED`
passed. `HEXCOM` created and ran `HELLO.COM`; ED created, saved, and read back
`EDTEST.TXT`; both `SET` attribute transitions returned to CCP. The only
failure was `PIP COPY.TXT=README.TXT`: twice, all four data records and the
directory updates received successful synchronous NetDisk acknowledgements,
but PIP then stopped disk and N4 polling and did not return to `A>`. Ctrl+C did
not recover it. The exact `PIP COPY2.TXT=README.TXT` workload subsequently
reproduced the same prompt timeout in the production simulator. The existing
admission case copied only the smaller one-record `PROFILE.SUB`, so it did not
cover this boundary.

The retained simulator failure narrows this further. NetDisk completed every
read, write, and directory acknowledgement without a USART overrun, then the
8080 entered the default DMA buffer at `0080h`. It eventually fetched the
README text byte `76h` at `00C8h` as an 8080 `HLT` and stopped with
`PC=00C9h`, `SP=BFF6h`, interrupts disabled, and the zero-page WBOOT/BDOS
vectors still intact. Therefore the observed stop is not a wire timeout or a
successful copy followed by a missing prompt: some CP/M, BDOS, or native-BIOS
return state has redirected execution into DMA data. This state is the current
root-cause boundary; do not hide it with a longer host timeout or an automatic
reset.

Root cause identified on 2026-08-18: PIP's fast-copy path legitimately uses
BDOS function 44 and leaves the process-wide multi-sector count above one.
The project-owned CCP reload loop advanced DMA by one 128-byte record after
each BDOS sequential read but did not first restore that count to one. Warm
boot consequently loaded overlapping CCP chunks; execution of the corrupted
CCP eventually fell through low memory and the DMA buffer. `load$ccp` now sets
the BDOS multi-sector count to one before opening `CCP.COM`, matching its
single-record loop.

The exact immutable C6 ROM plus corrected network-loaded system now passes two
independent `README.TXT` copies, CRC `4613` after each, every full-profile
utility, explicit warm boot, A: writes/erase, native B:, zero retries, and
strict-8080 opcode admission in the production simulator. The structural gate
also requires the reset in the CCP loader. The HEXCOM/SID/PATCH/ED development
profile, clean/compound/server-restart/mid-session-restart matrix, manifest,
package reproducibility, runtime catalogue, frozen C4/C5 identity, legacy
timing reproductions, and four-mode console gates pass as well. One CS00015
copy/CRC run remains before M1 is closed.

The correction is complete only when:

- a reduced simulator matrix identifies the first failing record count and
  captures the final BDOS/BIOS calls plus CPU PC/SP at the stall;
- the responsible native-BIOS, cache/invalidation, MULTIO/FLUSH, or return-state
  defect is corrected without weakening synchronous write-through semantics;
- the ordinary admission test copies at least the four-record `README.TXT`,
  returns to `A>`, and verifies the destination as CRC16-CCITT `4613`;
- repeated copy, warm boot, host reconnect, and the complete C6/Priority-7
  regression matrix pass;
- one final CS00015 run performs `PIP COPY.TXT=README.TXT` followed by
  `CRC COPY.TXT`, returns to CCP, and reports `4613`.

This is expected to require a newly network-loaded CP/M system rather than an
EPROM burn. Preserve the two failed copy-backed images and host transcripts as
diagnostic evidence until the cause and regression are closed.

### Execution ledger

Work proceeds in this order. A later item may be prototyped at the desk, but it
must not displace an earlier correctness gate or be described as accepted
before its own evidence exists.

| Stage | Goal | Desk completion gate | Next physical evidence |
|---|---|---|---|
| M1 | Fix multi-record PIP | Reproduce the first failing record count; capture the control transfer into `0080h`; fix it; make four-record copy/CRC, repetitions, warm boot, reconnect, and all release tests pass. | One C6/N4 load on CS00015: copy `README.TXT`, CRC `4613`, prompt returns. No EPROM burn expected. |
| M2 | Automate physical acceptance | A paging-aware runner records commands, target replies, timeouts, volume mutations, host lifecycle, and artifact hashes without optimistic inference from disk traffic. | One full and one development-profile run; the operator supplies only power/reset and requested keys. |
| M3 | Close display acceptance | `VIDTEST.COM` and exact framebuffer oracles cover boundaries, glyph banks, joined box drawing, and both cursor phases in all four S21 modes. | Observe 40x24, 53x24, 64x20, and 80x24 on a working display; record any monitor-specific cropping separately. |
| M4 | Improve NetDisk responsiveness | Measure cold login, first A:, first B:, alternating A:/B:, sequential reads, and writes; change only behavior with a demonstrated end-to-end benefit and unchanged recovery/data-safety tests. | A short CS00015 timing comparison only after simulator fault injection and replay pass. |
| M5 | Improve the distribution | Prototype strict-8080 history and text-interface tools, retain reproducible source/license/size/runtime admission, and keep the recovery profile small. | Hardware smoke only for programs admitted by the exact-C6 simulator; no manual catalogue trawl on the bench. |
| M6 | Maintain per-machine diagnoses | Keep CS00015 as reference; keep CS00000 USART and CS00024 RAM/refresh/D57 hypotheses separate and evidence-backed. | Machine-specific tests only when that machine is available; never weaken the reference configuration to accommodate an unproven fault. |

Status on 2026-08-19:

- M1's root cause and software fix are complete. Its repository-wide
  simulator, recovery, package, legacy-timing, and repeated copy/CRC gates
  pass; only one CS00015 `PIP`/`CRC` confirmation remains.
- M2's desk implementation is complete. The manifest-bound full/development
  runner handles paging and interactive inputs, isolates writable media,
  records byte-addressed target replies and host lifecycle evidence, preserves
  timeout diagnostics, shuts the host down cleanly, and independently audits
  retained results. One full and one development CS00015 run remain.
- M3's desk implementation is complete. `VIDTEST.COM` is admitted to the
  full/dev/demo media, all sixteen oracle surfaces are deterministic, and the
  exact C6 executable passes seven live geometry/locale cases with both cursor
  phases. Four physical display observations still wait for a working monitor.
- M4 and M5 are measured improvements, not correctness work. They start only
  after M1/M2 make performance and distribution changes cheap to qualify.
- M6 is an evidence ledger rather than a shared-machine workaround: CS00015
  remains the reference while CS00000 and CS00024 keep independent diagnoses.

The next physical action is therefore deliberately small: boot the corrected
system through the existing C6/N4 ROM on CS00015, run
`PIP COPY.TXT=README.TXT`, then `CRC COPY.TXT`, and require CRC `4613` plus a
returned `A>` prompt. No EPROM burn is needed. After that, the next bench work
should be driven by the M2 runner rather than another hand-entered catalogue.

The completed M1 desk sequence covered one- through four-record variants, a
bounded instruction/BDOS/BIOS history around the jump below `0100h`, the
native `MOVE`, `MULTIO`, `FLUSH`, DMA, and CCP-return contracts, the exact
four-record admission workload, and the complete simulator/package regression.
The next useful CS00015 experiment is only the final copy-and-CRC confirmation;
repeating the old failing image would add no evidence.

### Follow-on work, in priority order

1. **Physical-test automation.** The full/development N4 runner, declarative
   workloads, private writable copies, target timeout diagnostics, durable
   evidence, clean host shutdown, bench-friendly wait, and independent audit
   are implemented and regression-tested. Complete one full and one
   development run on CS00015; retain both passing result directories. The
   full run also supplies M1's remaining PIP/CRC physical evidence.
2. **Physical display acceptance.** `VIDTEST.COM`, its strict-8080 gate, the
   independent sixteen-surface oracle, seven exact-C6 executable cases, and
   the 60-second physical display workload are complete. With the unchanged
   C6 ROM, inspect raw S21 `01h`, `03h`, `05h`, and `07h` for 40x24, 53x24,
   64x20, and 80x24 respectively. This is the only outstanding C6 physical
   promotion boundary; framebuffer oracles remain the software authority and
   monitor cropping must be recorded separately.
3. **Measured NetDisk performance.** Optimize initial A: login and first or
   alternating drive selection, retaining separate wire, target, console, and
   host timings. Steady-state `DIR` is already served from CP/M state and is
   not a useful optimization target. Preserve independent eight-record A:/B:
   read-ahead and synchronous invalidating writes. Do not add write-back
   caching without explicit flush, warm-boot, retry, disconnect, and power-loss
   contracts.
4. **Distribution usability.** Consider a project-owned, source-available
   strict-8080 command-history facility and further text-interface tools that
   use the connected pseudographic set. Keep hand-written 8080 assembly as the
   production baseline; use Millfork as the preferred measured high-level
   experiment and z88dk for C portability probes.
5. **Deferred software.** Keep `cpm-ls` audited but outside all profiles until
   an indexed-directory service or demonstrated workflow justifies its 55/188
   NetDisk reads and 14,913-byte image. Reconsider FIG-Forth only with a
   complete editor, assembler, documentation, and unambiguous package notice.
   Continue rejecting the unlicensed/source-less HIST reference binary.
6. **Physical fleet.** Keep CS00015 as the known-good reference. Treat
   CS00000's suspected USART fault and CS00024's RAM/refresh/D57 evidence as
   separate per-machine investigations, preserving their machine profiles
   rather than generalizing either fault into the production model.

### Explicitly separate future projects

Rates above the proven 19,200-baud mode-2/count-4 setting, cryptographic boot
authentication, write-back caching, and real banked CP/M Plus all require
separately named experiments with measured benefit and failure semantics.
XMODEM remains excluded because NetDisk/N4 already owns the USART and provides
checksummed, reconnectable disk and file transport. Banking remains outside
this non-banked port unless new Juku memory hardware is designed, built, and
characterized.
