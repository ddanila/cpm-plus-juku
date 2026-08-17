# CP/M Plus 3.1 C6 simulator release

Status: **SIMULATOR-QUALIFIED; PHYSICAL PROMOTION IS A SEPARATE STEP**

The C6 set is the first complete ABI 1.2 network-first candidate. It is an
immutable, reproducible desk artifact intended to remove hardware availability
from development and acceptance of software behavior. It does not overwrite
or weaken the physically established C5 reference.

## Bound artifacts

| artifact | SHA-256 |
| --- | --- |
| combined C6 ROM | `0487d5150f9b662a193b3f031aadd90002ee232477d355d3877a757a247c2f09` |
| D15 low half | `8cf403663ed860f7e5ab56f382e42bddf6e8951e478e89313074c03ab31f2750` |
| D16 high half | `3a60561d0e5f8a8d8e9a1f1c355e503db5daeadec174b45380de732690c9bdf1` |
| extended CP/M system | `6dbe02421fb88cc964b9536f0f5c51f0e31a652a6017cb4a8d3178394849b70b` |
| Fastboot V16 system stream | `40c1560348b2615064cf8d2f216c5c85a020f9b1384707ec83e93d94a94a3706` |
| C6 recovery A: | `5b114df3b053af325e8254afd2134997cff180c13c6cfee17645059390367905` |
| reproducible release tar | `dd88e85eeba6bb056d127b4557fd1030e5b0bd9378c7baeb5b29bf82e79f88df` |

The generated boot manifest binds those files, the separately named D15-low
and D16-high halves, the native B: image, full/demo volumes, and the immutable
C4 compatibility slot. `memory-map.json` is generated from the same inputs and
records the complete fixed ABI-vector map rather than a hand-maintained subset.

C5 remains pinned independently: its ROM is
`9ed6273f44c1b09dcb5fcd3ca94e5a1aad813b285607558a7d8cb98b1a5e6e7a`
and matching system is
`86b36bd70156d10bafba332bd02e8756473c76bde3e9cc4a50fbc530bfb8a3f2`.
The C6 build checks both hashes/bytes so an additive ABI change cannot silently
rewrite the physical baseline.

C6 Fastboot V16 keeps its complete generic 361-byte receive, CRC, ZX0
decompression, and retry engine in the lower 6 KiB of ROM at file offset
`0600h`. The 49-byte core is padded to its fixed 128-byte descriptor at
`0F00h`. The wire artifact therefore carries zero executable extension bytes:
after `C7`/`JR16`, it sends only `JZ`, a bounded length, 7,895 compressed
system bytes, and CRC-16/IBM. The simulator also discards both one-shot ready
indications before starting the host and proves that the overlap-safe header
exchange recovers without RESET.

## Added ABI 1.2 services

- `FF53h`: render a low-RAM span of 1..256 bytes with one ROM gate crossing;
- `FF56h`: execute 1..8 ordinary NetDisk request descriptors in order;
- `FF59h`: return an instantaneous untranslated keyboard matrix sample;
- `FF41h`: implemented silence and the shared bounded diagnostic tune;
- USERF selector 5 / NetDisk operation `28h`: duplicate-safe N4 output of
  1..32 bytes, negotiated by a new capability bit.

Every older vector retains its address and contract. The low-RAM gate still
fits its 214-byte window and the mode-3 framebuffer helper remains exactly 128
bytes. The extended adapter is 2,924 bytes at `C000h..CB6Bh`; the transient
area remains `0100h..99FFh`, 39,168 bytes and 8 KiB above the frozen RAM-BIOS
system.

## Simulator acceptance

`make c6-release-candidate` is the single fail-closed release command. It:

1. regenerates the combined ROM, halves, and metadata;
2. runs the C4/C5/C6 ABI executable checks and focused HDL boundary;
3. validates the C6 manifest and immutable C4 fallback;
4. boots the real C6 CP/M image once through local console/keyboard with N4
   absent and once through the complete N4 remote-console path;
5. runs A:/B: selection, `DIR`, paginated sequential `TYPE`, diagnostics,
   raw-key presence, block N4 output, warm boot, synchronous write/erase, and
   zero-overrun checks;
6. runs 64 read/diagnostic/write cycles across a deliberate stateless server
   replacement, with no manual reset (1,193 reads, 257 writes, zero retries
   and zero resident/bootstrap overruns in the accepted run);
7. creates the package twice and requires byte-identical tar bytes, then
   rechecks every manifest file hash, ROM split, system slot, ABI service, TPA,
   and vector-map value.

The local and remote console runs are deliberately separate. An absent N4 host
must not affect local display/keyboard, while an advertised N4 host must carry
both ordinary bytes and exactly one bounded `N4 BULK PASS` request. This avoids
the invalid test assumption that a target should emit remote output when the
host explicitly reports no console capability.

## Physical promotion boundary

No physical observation is required to call this simulator artifact complete.
When CS00015 and a display are convenient, promotion consists of programming
the named halves and repeating a short cold-boot, display/cursor, keyboard,
A:/B:, diagnostic, warm-boot, and live-reconnect matrix. A failed physical
promotion creates a C7 fix or board-specific service record; it does not erase
the C5 or stock-ROM recovery paths and does not invalidate the simulator
artifact's accurately scoped claim.
