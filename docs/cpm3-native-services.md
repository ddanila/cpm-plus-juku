# Native CP/M Plus BIOS services

The immutable C4 system remains the compatibility reference. Native services
are built as separately named network-ROM artifacts:

- `out/cpm-plus-juku-network-rom-native-system.bin`;
- `out/cpm-plus-juku-network-rom-native-fastboot-v15.bin`;
- `out/cpm-plus-juku-native-test.img` for the target-side regression only.

They retain the same non-banked memory map: BDOS begins at 9D00h, BIOS at
BC00h, the adapter at C000h, and the 39,168-byte TPA ends at 9CFFh. No banked
memory is claimed. GENCPM relocates the SCB to BB9Ch (clock BBF4h); FE00h
symbols in the DRI source are relocatable canonical addresses,
not runtime addresses for an absolute adapter module. `make
native-services-check` regenerates the native SYS,
builds the adapter in C000h..C4FFh, boots it through the production network
ROM, and runs both the normal CP/M command matrix and `NATIVE.COM`.

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
  last MULTIO count. Unknown selectors fail with A=FFh and HL=0000h.
- TIME gets CP/M day plus BCD hour/minute/second through optional NetDisk-v3
  operation 22h. SET uses operation 23h to establish a host session offset
  without changing the host OS clock. An absent, invalid, or torn reply leaves
  the SCB unchanged and updates status counters; boot and disk never depend on
  this service.

S21 is sampled with the same drawing-derived scan order and active-low PB5
polarity as `juku-common`'s `RKCONFIG`. Video mode is `(raw_s21 >> 1) & 3`, so
ROM, CP/M console setup, and status reporting share one encoding.

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
