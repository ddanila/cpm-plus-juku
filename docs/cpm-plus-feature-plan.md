# CP/M Plus post-baseline feature plan

Status: **IMPLEMENTED AND PACKAGED; C6 BLIND HARDWARE MATRIX PASSED**

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

## Completion order

1. Freeze and publish the physical network-first baseline.
2. Build a useful, licensed, reproducible A:/B: distribution.
3. Add status, shared diagnostics, boot records, and complete S21 integration.
4. Implement date/time and character-device support as native CP/M 3 calls.
5. Improve read performance and multi-volume media handling.
6. Add further native BIOS and protocol features only with measured benefit.

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

`make check` is the complete ordinary desk gate. `make bench-candidate` additionally
rebuilds the immutable C4 package and proves that incomplete or tampered
physical evidence cannot pass the recorder audit. Those C5 commands preserve
their historical physical-promotion semantics.

`make release-candidate` remains the C5 desk packaging gate. It binds the ABI
1.1 C5 ROM and exact D15/D16 halves to the matching locale-native CP/M Plus
3.1 system, C4 fallback, published media/reports, license, and notice in a
byte-reproducible tar. This completes every desk-executable item in this plan.
It deliberately does not promote C5: the blind hardware matrix passes, but the
display/cursor gate remains. See
[`cpm-plus-31-c5-release-candidate.md`](cpm-plus-31-c5-release-candidate.md).

`make c6-release-candidate` is the completed-plan gate. It rebuilds ABI 1.2,
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
simulator-release scope of this completed plan.
