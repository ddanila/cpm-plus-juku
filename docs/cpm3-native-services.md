# Native CP/M Plus BIOS services

The immutable C4 system remains the compatibility reference. Native services
are built as separately named network-ROM artifacts:

- `out/cpm-plus-juku-network-rom-native-system.bin`;
- `out/cpm-plus-juku-network-rom-native-fastboot-v15.bin`;
- `out/cpm-plus-juku-network-rom-locale-native-system.bin` and matching
  fastboot-v15 bundle for the separately named ABI 1.1 C5 desk candidate;
- `out/cpm-plus-juku-native-recovery.img` for post-C4 recovery use;
- `out/cpm-plus-juku-native-test.img` for the target-side regression only.

They retain the same non-banked memory map: BDOS begins at 9D00h, BIOS at
BC00h, the adapter at C000h, and the 39,168-byte TPA ends at 9CFFh. No banked
memory is claimed. GENCPM relocates the SCB to BB9Ch (clock BBF4h); FE00h
symbols in the DRI source are relocatable canonical addresses,
not runtime addresses for an absolute adapter module. Running
`make native-services-check` regenerates the native SYS,
builds core/transport code in C000h..C52Ah and native services in
CA00h..CB80h at most, while keeping fixed state in C640h..C95Fh,
boots it through the production network ROM, and runs both the normal CP/M
command matrix, `NATIVE.COM`, and `STATUS.COM`.

## Implemented slice

- DEVTBL reports one fixed `JUKU` input/output device. It represents the
  authoritative local keyboard/display plus transparent optional N4
  mirroring; it does not falsely expose the NetDisk USART as a raw terminal.
- DEVINI accepts device zero and rejects other device numbers diagnostically.
- console and auxiliary output status are ready; separate auxiliary input is
  not ready.
- MULTIO records the count supplied in A in private native-driver status, like
  DRI `bioskrnl.asm`'s private `@cnt`. It deliberately does not overwrite the
  BDOS-owned SCB `@MLTIO`; doing so was reproduced as a warm-boot/CCP reload
  failure. The disk driver remains synchronous/single-record until bounded
  coalescing is measured.
- FLUSH returns success because every current write is synchronous
  write-through and there is no target write cache.
- MOVE has 8080 memmove semantics for both overlap directions, zero lengths,
  and identical addresses. It returns source and destination advanced by the
  original count and BC zero, matching the reference LDIR implementation.
- reserved BIOS entry 30 is a versioned Juku USERF query. Selector C=0 returns
  a `JNS1` status block with features, raw S21, decoded video mode, and the
  last MULTIO count. Selector C=1 refreshes the block and publishes the same
  bounded tuple to the host. Selector C=2 publishes a bounded diagnostic tuple
  supplied in B/D/E/L as suite, pass mask, fail mask, and flags. Selector C=3
  performs an explicit host capability query and returns HL pointing to four
  bytes: NetDisk protocol, maximum read-ahead, feature flags, and drive count.
  Selector C=4 publishes retained bootstrap stage, CRC retry count, protocol,
  and ROM ABI minor through operation 27h.
  Unknown selectors fail with A=FFh and HL=0000h.
- TIME gets CP/M day plus BCD hour/minute/second through optional NetDisk-v3
  operation 22h. SET uses operation 23h to establish a host session offset
  without changing the host OS clock. An absent, invalid, or torn reply leaves
  the SCB unchanged and updates status counters; boot and disk never depend on
  this service.

S21 is sampled with the same drawing-derived scan order and active-low PB5
polarity as `juku-common`'s `RKCONFIG`. Video mode is `(raw_s21 >> 1) & 3`, so
ROM, CP/M console setup, and status reporting share one encoding.

The ABI 1.1 build calls the appended `JCGCONFIG` vector instead, so CP/M uses
the ROM's reset-latched byte rather than resampling live switches. Its system
and fast-stage SHA-256 values are respectively
`86b36bd70156d10bafba332bd02e8756473c76bde3e9cc4a50fbc530bfb8a3f2`
and `4aaff8f9a78c289e96bb1699453d3136f7c2f6c82f3bfb2323d46145028178b0`.
The C4/native ABI 1.0 artifact retains its bounded direct sampler and byte
identity.

`STATUS.COM` prints the system/protocol/ROM identities, resident memory map,
raw and decoded S21/video/locale selection, native feature flags, last MULTIO count,
and clock result counters. Its USERF selector also emits NetDisk-v3 operation
24h, so the host records the same S21, video, feature, and clock-status tuple.
The operation is idempotent, bounded, and optional: an absent N4 host cannot
starve the local status display or disk service.

`DIAG.COM` 0.5 uses USERF selector 2 to emit NetDisk-v3 operation 25h after
each completed safe suite. The host logs and counts the result without adding
any dependency to local diagnostics. See
[`cpm3-diagnostics.md`](cpm3-diagnostics.md).

`STATUS.COM` also uses USERF selector 3 / NetDisk-v3 operation 26h. Unlike the
startup N3/N4 marker, this is a checksummed request/reply exchange that may be
repeated after host replacement. It reports the actual server protocol,
bounded read-ahead limit, console/time/status/diagnostic/B:/writable-A feature
bits, and advertised drive count. An older or absent server returns
"unavailable" without affecting local display, disk, or boot.

Cold boot also issues this query once after resident serial initialization.
If the host explicitly clears the console feature, native CP/M disables N4
reprobes for that session; if the query is rejected as an older-host extension,
the bounded legacy reprobe policy remains. A console-advertising host retains
normal N4 input/output and live reconnect. Cosimulation proves both branches.

The fixed native status record retains reset POST status at cold boot, changes
its cold/warm marker only on a real CP/M warm entry, records the last resident
NetDisk status and remaining attempt count, and counts successful N4 reprobes
after bounded host loss. The status regression observes cold state through
`STATUS.COM`, executes `WBOOT`, and then checks the warm marker directly in the
simulator checkpoint. C4 remains byte-identical because clock, publisher, and
recording code are assembled only in the separately named native profile.

`STATUS.COM` 1.2 extends the `JNS1` block to schema 1.1 and displays the C5
record at D610h..D613h. Stages distinguish POST (`10h`), V15 core (`20h`),
extension wait/header/authentication (`30h`/`31h`/`32h`), compressed CRC
recovery (`E2h`), CP/M entry (`40h`), and the first successful disk turn
(`50h`). The retry byte saturates instead of wrapping. USERF selector 4 mirrors
the final tuple through duplicate-safe operation 27h, and the host logs and
counts it exactly once. ABI 1.0 returns a deterministic zero tuple rather than
reading unassigned C4 RAM bytes. `make bootstrap-observability-check`
corrupts the first compressed V15 stream, proves one target-side `E2h` retry,
then verifies the recovered `50h` report and matching host/target retry counts.

The native fixed layout is deliberately non-overlapping: core and transport
code end at C52Ah, cold/warm and transport state occupy C640h..C65Fh, the
directory buffer and resident three-record cache occupy C680h..C909h, and the
adapter's transient disk workspace begins at C920h. Native-only service code
is linked separately at CA00h and ends no later than CB80h, inside the existing
C000h..CFFFh adapter
allocation; this leaves room for future measured native services without
growing the TPA or colliding with mutable state. Address-watch tracing
reproduced and eliminated two integration faults: placing the workspace at
C600h overwrote native service code, while C780h overwrote the NetDisk cache.
The regression now executes real reads, STATUS/capabilities, diagnostics,
warm boot, and write/erase through this map.

The C5-only binding adds eight-record buffers at CB80h..CF97h and
CFA0h..D3B7h. The resident ROM stores independent A:/B: counts and pointers
at D7DAh..D7DFh;
the alternating-drive regression loads B:, returns to A:, reloads an A:
transient, and proves both counts remain nonzero with the expected distinct
pointers. The immutable C4/native binding and memory map remain unchanged.

`NATIVE.COM` calls the actual high-memory BIOS vectors on the emulated 8080.
It verifies the device table, FLUSH, A-register MULTIO convention, USERF
status, overlapping forward/backward MOVE, return pointers, and zero count.
The ordinary cosimulation then proves `DIR`, paged `TYPE`, shared diagnostics,
warm boot, write/erase, framebuffer behavior, and zero-retry NetDisk. A
separate compound run passed shortened, duplicated, and CRC-corrupted replies
with two target retries and three intentionally induced USART overruns.

The CP/M Plus System Guide is the interface authority, including the TIME
requirement to preserve HL/DE and the standard device-table layout. The pinned
DRI `bioskrnl.asm`, `chario.asm`, and `move.asm` sources are executable-format
cross-checks for MULTIO, character modes, and pointer return behavior.
