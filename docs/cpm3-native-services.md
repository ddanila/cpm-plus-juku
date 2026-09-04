# Native CP/M Plus BIOS services

The immutable C4 system remains the compatibility reference. Native services
are built as separately named network-ROM artifacts:

- `out/cpm-plus-juku-network-rom-native-system.bin`;
- `out/cpm-plus-juku-network-rom-native-fastboot-v15.bin`;
- `out/cpm-plus-juku-network-rom-locale-native-system.bin` and matching
  fastboot-v15 bundle for the separately named ABI 1.1 C5 desk candidate;
- `out/cpm-plus-juku-network-rom-extended-native-system.bin` and matching
  fastboot-v16 bundle for the ABI 1.2 C6 simulator candidate;
- `out/cpm-plus-juku-network-rom-session-native-system.bin` and matching
  fastboot-v16 bundle for consumers of the volatile-session extension;
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
  In the ABI 1.2 build, selector C=5 sends a caller-owned `DE` span of `B`
  bytes (1..32) through duplicate-safe operation 28h. It is deliberately
  absent from the C5 object, whose system image remains byte-identical.
  In the session-native build, selectors C=6/7 expose one generic
  keyed 127-byte volatile-session blob;
  the caller supplies a four-byte owner and opaque bytes. The slot survives
  warm boot/transient replacement, clears on cold load, and performs no disk
  I/O. See [`cpm3-session-state.md`](cpm3-session-state.md).
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

The ABI 1.2 C6 binding additionally links the bounded N4 block sender and
requires the ROM's appended console-span, multi-request NetDisk, raw-keyboard,
and sound features. The current post-C6 system includes the one-record BDOS
reset before CCP reload plus the measured hot-directory cache. Its system and
fast-stage SHA-256 values are
`57de00733bea16a3ce6427b8e010649727c6b0d84144724c43c5114a1cf35091`
and `3c2cf62d43b7867844b18fb142fbae8c49bdc83a148fcb22bfac9a8a26b32d67`.
It remains compatible with the immutable C6 ROM and requires no EPROM change.
The latter is a Fastboot V16 stream descriptor plus checked compressed system;
its receive/decompress code is the exact 361-byte image embedded in the C6
ROM rather than a downloaded executable extension.
The current post-C6 adapter container occupies `C000h..D570h` (5,489 bytes),
including the sparse native services, read-ahead buffers, and measured
hot-directory cache. It remains below the fixed `D600h` ROM workspace and
does not change the 39,168-byte TPA.

The CCP loader itself is single-record code: it advances DMA by 128 bytes
after every BDOS sequential read. It therefore calls BDOS function 44 with a
count of one before opening `CCP.COM`. This is required because a fast PIP
copy legitimately leaves the process-wide multi-sector count above one; using
that retained count made successive CCP chunks overlap during warm boot.

`STATUS.COM` prints the system/protocol/ROM identities, resident memory map,
raw and decoded S21/video/locale selection, native feature flags, last MULTIO count,
and clock result counters. Its USERF selector also emits NetDisk-v3 operation
24h, so the host records the same S21, video, feature, and clock-status tuple.
The operation is idempotent, bounded, and optional: an absent N4 host cannot
starve the local status display or disk service.

The C12 system retains the `0100h..9BFFh` TPA but publishes ROM ABI 1.5 in the
same status record. Its matching `STATUS.COM` 1.6 queries `JCGCONCONFIG` and
prints both reset-latched S21 defaults and the active mode/bank plus independent
override flags. `CONSOLE.COM` 1.0 uses that same public vector for STATUS,
MODE, CHARSET, and DEFAULT; it does not duplicate timing, framebuffer, font, or
keyboard-transition logic in transient RAM. `DIAG.COM` 0.8 accepts a valid
active tuple that differs from S21 and retains the POF check. The exact C12
system and Fastboot SHA-256 values are respectively
`74abab89c14e8429eec943c8b7c77ad33675cbf411fde5190d4657a3d28bdb79`
and `51788bc93dac1e03a541239eb7f2837e3e03ef2519c3703aa052fe15b248f202`.

The displayed map names the actual `0100h..99FFh` TPA and separate
`9A00h..9CFFh` loader; the older `0100h..9CFFh` text incorrectly included the
loader in the TPA. It also reports the BIOS and the complete `C000h..D5FFh`
adapter/state container. The native-services regression requires these exact
lines rather than accepting the title alone.

`DIAG.COM` 0.5 uses USERF selector 2 to emit NetDisk-v3 operation 25h after
each completed safe suite. The host logs and counts the result without adding
any dependency to local diagnostics. See
[`cpm3-diagnostics.md`](cpm3-diagnostics.md).

`STATUS.COM` also uses USERF selector 3 / NetDisk-v3 operation 26h. Unlike the
startup N3/N4 marker, this is a checksummed request/reply exchange that may be
repeated after host replacement. It reports the actual server protocol,
bounded read-ahead limit, console/time/status/diagnostic/B:/writable-A feature
bits, bounded N4 block-output capability, and advertised drive count. An older or absent server returns
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

`STATUS.COM` 1.2 extends the `JNS1` block to schema 1.1 and displays the C5/C6
record at D610h..D613h. C5 stage `20h` identifies its V15 downloaded-extension
path; C6 identifies the V16 core and ROM-resident loader. Later stages retain
the shared header/authentication (`30h`/`31h`/`32h`), compressed CRC
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

The C5/C6 binding adds eight-record buffers at CB80h..CF97h and
CFA0h..D3B7h. The resident ROM stores independent A:/B: counts and pointers
at D7DAh..D7DFh;
the alternating-drive regression loads B:, returns to A:, reloads an A:
transient, and proves both counts remain nonzero with the expected distinct
pointers. The immutable C4/native binding and memory map remain unchanged.

The named session-native loaded system coordinates its volatile-session slot
with the conservative directory hot set. Ownership metadata is at
`C5A2h..C5A6h`; the 119-byte session service occupies the former third cache
record at `D440h..D4BFh`. Before a claim, translated track-2 sectors 1 and 2
use `C5C0h..C63Fh` and `D3C0h..D43Fh`; a claim gives the first 127 bytes of
the latter to the payload while sector 1 remains independently cached.
Session-aware hot-cache code occupies `D4C0h..D570h`, ending immediately
before the independent CCP `!!` state at `D571h`. The ordinary C6/C7 and C8
artifacts retain their exact three-record implementation. No TPA or ROM
address changes.

`NATIVE.COM` calls the actual high-memory BIOS vectors on the emulated 8080.
It verifies the device table, FLUSH, A-register MULTIO convention, USERF
status, overlapping forward/backward MOVE, return pointers, and zero count.
The ordinary cosimulation then proves `DIR`, paged `TYPE`, shared diagnostics,
warm boot, write/erase, framebuffer behavior, and zero-retry NetDisk. A
separate compound run passed shortened, duplicated, and CRC-corrupted replies
with two target retries and three intentionally induced USART overruns.

The C6 gate runs the same matrix twice: once through authoritative local
display/keyboard with N4 absent, and once with the complete console carried
through N4. `N4BULK.COM` invokes USERF selector 5 and the host must record
exactly one operation-28h block containing `N4 BULK PASS`; returning locally
without a console-advertising host is intentionally a successful best-effort
no-op. `KEYRAW.COM` is also present only in the C6 recovery profile and proves
that the extended binding is installed before physical promotion. The frozen
C6 scanner is authoritative for unmodified contacts only: source review found
that a global SHIFT/CTRL return can make it report column zero before reaching
the ordinary modified key's column. `juku-common` master fixes that ordering,
but adoption requires a separately named ROM successor; C6 is not regenerated.

The CP/M Plus System Guide is the interface authority, including the TIME
requirement to preserve HL/DE and the standard device-table layout. The pinned
DRI `bioskrnl.asm`, `chario.asm`, and `move.asm` sources are executable-format
cross-checks for MULTIO, character modes, and pointer return behavior.
