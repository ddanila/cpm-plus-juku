# Network-first ROM inventory and byte budget

Status: **MEASURED BASELINE; AUTOMATIC BOOT FITS; SERVICE MIGRATION NEXT**

Measurement date: **2026-08-16**

## Reproduce the report

Run:

```sh
make rom-budget-check
```

`tools/rom_budget.py` assembles each shared source independently with the same
zmac build used by CP/M Plus, reads the linker's byte count, checks every
assigned envelope, and checks that the envelopes total exactly 6,144 and
10,240 bytes. It intentionally measures linked machine code and data, not
source lines or object-container sizes.

Current measured ingredients are:

| shared ingredient | linked bytes | intended first use |
| --- | ---: | --- |
| MODX-compatible console, including 665-byte font | 1,228 RAM baseline; 1,191 resident | resident ROM implemented |
| mode-3 console clear/scroll/packed-row helper | 119 | copied low RAM implemented |
| keyboard matrix scanner | 331 RAM baseline; 328 resident code | resident ROM implemented; three mutable bytes remain in low RAM |
| shared resident D57/D11 serial initializer and primitives | 86 | implemented resident ROM ABI service |
| NetDisk v3 client, including its present private serial primitives | 547 | resident ROM |
| remote console/status client | 368 | resident ROM, optional at boot |
| CPU diagnostic | 517 | quick POST and resident diagnostic service |
| byte-cell RAM diagnostic | 29 | quick POST and resident service |
| address-alias diagnostic | 59 | quick POST and resident service |
| retention diagnostic | 32 | resident service; not normal quick POST |
| checksum primitive | 18 | ROM/load integrity |
| complete diagnostic mechanisms | 655 | boot selects a bounded subset |
| sound routine plus tune | 114 | resident feedback/service |
| proven V15 direct core | 125 source bytes; 141 stored with target-ready prelude | automatic bootstrap seed |
| proven V15 receive/decompress extension | 267 | automatic load engine seed |

The sum is not a proposed final ROM size. Several current modules contain
consumer-specific state or duplicate serial loops which will be separated as
the ABI is implemented. The value of this inventory is that each envelope
already accommodates the complete unsplit implementation; refactoring is not
being credited as savings before it exists.

## Lower 6 KiB: reset-visible, boot-only

| ROM file range | bytes | envelope | reusable/current implementation evidence |
| --- | ---: | --- | ---: |
| `0000h..05FFh` | 1,536 | reset, deterministic hardware init, bounded quick POST | 623 shared mechanisms; 997-byte linked boot |
| `0600h..0BFFh` | 1,536 | automatic 19,200-baud boot transport | 125-byte source; 141-byte stored core |
| `0C00h..11FFh` | 1,536 | validation, decompression, timeout/retry recovery | 267 |
| `1200h..15FFh` | 1,024 | copied all-RAM helper image and staging | 196-byte gate plus 119-byte console helper |
| `1600h..17FFh` | 512 | boot manifest, integrity values, growth reserve | 0 |
| **total** | **6,144** | exact boot-only window | **1,134 reusable ingredients; 1,453 linked component bytes currently stored** |

The large headroom is intentional. The current builder places 997 bytes of
reset/POST code, a 141-byte automatic core, a 196-byte gate, and a 119-byte
helper without overlap. The 267-byte extension is still sent into RAM by the
host rather than stored in ROM. Later recovery work and moving the complete
receive/decompress path into the boot-only window must fit without borrowing
bytes from the runtime ABI. `network_first_rom_abi_check.sh` independently
checks the exact linked layout and deterministic image.

## Upper 10 KiB: runtime-mapped at `D800h..FFFFh`

| runtime range | bytes | envelope | measured implementation |
| --- | ---: | --- | ---: |
| `D800h..DCFFh` | 1,280 | console policy, geometry, ASCII font | 1,191 implemented; 89 bytes headroom |
| `DD00h..DE7Fh` | 384 | keyboard scan and translation | 328 implemented; 56 bytes headroom |
| `DE80h..E0FFh` | 640 | shared D57/D11 serial layer | 86-byte resident initializer/primitives implemented |
| `E100h..E3FFh` | 768 | NetDisk v3 protocol | 547, currently including serial loops |
| `E400h..E5FFh` | 512 | remote console and bounded status | 368 |
| `E600h..E8FFh` | 768 | common diagnostic mechanisms | 655 |
| `E900h..E9FFh` | 256 | sound and platform initialization | 114 |
| `EA00h..EFFFh` | 1,536 | near-term implementation growth | 0 |
| `F000h..F7FFh` | 2,048 | locale/font banks and future services | 0 |
| `F800h..FEFFh` | 1,792 | unassigned reserve | 0 |
| `FF00h..FFFFh` | 256 | ABI manifest, identity, feature bits, fixed vectors | ABI 1.0 implemented and range-fixed |
| **total** | **10,240** | exact runtime window | **3,289 measured** |

These are link fences, not permission to fill every service to its fence. The
ABI table is deliberately at the top of ROM so its address survives internal
layout changes. No service may grow across a fence without changing this
document and the executable budget check.

## Call and ownership graph

```text
target-state reset/runtime graph
  -> hardware init
  -> quick POST -> CPU / RAM / address / ROM-check mechanisms
  -> automatic boot -> serial -> checked receive / ZX0 -> RAM system
  -> CP/M Plus entry (current RAM baseline selects mode 3; final ABI path uses mode 1)

CP/M Plus thin BIOS bindings in RAM
  -> fixed ROM ABI table at FF00h
       -> console policy/font -> copied RAM framebuffer helper -> mode 3 -> mode 1
       -> keyboard -> PPI matrix
       -> NetDisk v3 -> shared serial -> D57/D11
                       -> low-RAM cache, DMA and protocol state
       -> remote console/status -> shared serial
       -> diagnostics -> hardware-specific front ends
       -> sound -> D57 channel 1
```

The console edge through a copied RAM helper is mandatory. The high ROM
overlay rejects writes as well as hiding framebuffer reads; code executing in
the upper ROM also disappears when mode 3 exposes framebuffer RAM. The
resident service therefore handles text policy, geometry and font lookup in
mode 1, then calls a small low-RAM helper which switches to mode 3, performs
the bounded pixel, clear or scroll operation, restores mode 1, and returns.
Ordinary CP/M code does not select mode 3.

NetDisk cache data, CP/M DMA, directory/allocation/check vectors, serial state,
cursor state, keyboard state, ABI work area, stack, and the copied video helper
remain RAM. Only code and immutable tables are candidates for resident ROM.

## RAM and TPA consequence

The frozen baseline has a 31 KiB TPA and 5,114 bytes above its CP/M 3 BIOS:

- 4,080 initialized adapter bytes at `A000h..AFEFh`;
- 1,034 bytes of mutable state/buffers through `B409h`.

The already measured console, keyboard, NetDisk and remote-console modules
account for 2,474 initialized bytes. Moving them behind the ROM ABI would leave
1,606 initialized adapter bytes before further policy cleanup, plus the 1,034
mutable bytes and a bounded RAM framebuffer helper. This supports a
conservative first relink target of at least **33 KiB TPA**, a real 2 KiB gain.
It is not yet an achieved result: the system must be relinked, its maps checked,
and all behavior rerun before the README may claim it. A 34 KiB target remains
plausible if shared serial extraction and buffer placement remove another
aligned 1 KiB without weakening cache or stack safety.

The ROM-ABI platform binding is now 897 bytes. It replaces the 2,132-byte
baseline platform object plus the separate 331-byte keyboard, for 1,566 bytes
of linked-code saving. The resident console itself is 1,191 bytes and its
mode-3 helper 119; full cosim proves its final 9,600-byte framebuffer identical
to the RAM oracle after the same transcript. Fixed NetDisk and remote-console
origins still extend both adapter files to 4,080 initialized bytes, so this does
not yet change the 31 KiB TPA. Whole NetDisk migration must remove those holes
before the system is relinked upward; the service crosses the memory-mode
boundary once per operation rather than once per byte.

## Decisions entering resident-service migration

- Keep the whole current implementation inside each initial envelope; do not
  depend on hypothetical compression or dead-code removal.
- Put the versioned manifest and fixed jump vectors in `FF00h..FFFFh`.
- Run CP/M Plus in memory mode 1 so the runtime ROM is visible; cross to mode 3
  only inside the copied framebuffer helper.
- Extract one shared serial layer for boot, NetDisk and remote status instead
  of preserving three subtly different polling loops.
- Keep 19,200 baud, D57 mode 2/count 4 as the production contract.
- Keep the full CPU diagnostic callable. The complete current POST reaches
  target-ready in 725,602 cycles (about 427 ms at 1.70 MHz), which is accepted;
  shrink it only if later physical timing shows a real usability cost.
- Treat the first locale/font bank and the large reserves as optional growth;
  they may not postpone the baseline automatic boot and TPA gain.
