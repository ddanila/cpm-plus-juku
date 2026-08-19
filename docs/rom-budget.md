# Network-first ROM inventory and byte budget

Status: **MEASURED THROUGH ABI 1.2 C6; 8 KiB TPA GAIN RETAINED**

Measurement date: **2026-08-18**

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
| MODX-compatible console, including 665-byte font and RAM-keyboard binding | 1,795 RAM baseline; 1,191 resident | resident ROM implemented |
| mode-3 console clear/scroll/packed-row helper | 119 | copied low RAM implemented |
| keyboard matrix scanner | 369 RAM baseline; 366 resident code | resident ROM implemented; mutable state remains in low RAM |
| shared resident D57/D11 serial initializer and primitives | 86 | implemented resident ROM ABI service |
| NetDisk v3 read-ahead/write-through client and versioned ABI binding | 676 resident; 547 RAM baseline | resident ROM implemented for reads and writes |
| remote console/status client | 372 | resident ROM, optional at boot |
| CPU diagnostic | 517 | quick POST and resident diagnostic service |
| byte-cell RAM diagnostic | 29 | quick POST and resident service |
| address-alias diagnostic | 59 | quick POST and resident service |
| retention diagnostic | 32 | resident service; not normal quick POST |
| checksum primitive | 18 | ROM/load integrity |
| complete diagnostic mechanisms | 655 | boot selects a bounded subset |
| sound routine plus tune | 114 | resident feedback/service |
| proven V15 direct core | 125 source bytes; 141 stored with target-ready prelude | immutable C4/C5 bootstrap seed |
| proven V15 receive/decompress extension | 267 C4 / 307 C5 | host-downloaded compatibility load engine |
| Fastboot V16 core | 49 source bytes; 128-byte fixed ROM/bundle descriptor | C6 bootstrap seed and C7 handoff |
| Fastboot V16 receive/decompress engine | 361 | embedded C6 boot-only loader; zero executable wire bytes |
| ABI 1.2 bounded console/multi/raw services | included in C6 resident image | appended fixed vectors; older ABI bytes unchanged |

The sum is not a proposed final ROM size. Several current modules contain
consumer-specific state or duplicate serial loops which will be separated as
the ABI is implemented. The value of this inventory is that each envelope
already accommodates the complete unsplit implementation; refactoring is not
being credited as savings before it exists.

## Lower 6 KiB: reset-visible, boot-only

| ROM file range | bytes | envelope | reusable/current implementation evidence |
| --- | ---: | --- | ---: |
| `0000h..05FFh` | 1,536 | reset, deterministic hardware init, bounded quick POST | 623 shared mechanisms; 997-byte C4 / 1,015-byte C5 / 1,027-byte C6 linked boot |
| `0600h..0BFFh` | 1,536 | checked receive/decompress engine | empty in C4/C5; exact 361-byte C6 V16 loader at `0600h` |
| `0C00h..11FFh` | 1,536 | bootstrap core and copied call gate | core at `0F00h`: 141-byte C4/C5 or 128-byte C6; gate at `1000h`: 196-byte C4 or 214-byte C5/C6 |
| `1200h..15FFh` | 1,024 | copied all-RAM helper image and staging | helper at `1400h`: 119-byte C4 or 128-byte C5/C6 |
| `1600h..17FFh` | 512 | boot manifest, integrity values, growth reserve | 0 |
| **total** | **6,144** | exact boot-only window | **1,453 C4 / 1,498 C5 / 1,858 C6 linked stored bytes** |

The large headroom is intentional. C4 places 997 bytes of reset/POST code, a
141-byte automatic core, a 196-byte gate, and a 119-byte helper without
overlap. C5 uses 1,015, 141, 214, and 128 bytes respectively; their matching
267-byte/307-byte extensions remain host-downloaded compatibility artifacts.
C6 completes the planned migration: 1,027-byte boot code copies its 361-byte
generic V16 receive/decompress engine from `0600h` to RAM, then enters the
128-byte core at `0F00h`; the 214-byte gate and 128-byte helper retain their
fixed windows. Thus the complete load engine is inside the boot-only 6 KiB and
no executable extension crosses the wire. `network_first_rom_abi_check.sh`
independently checks the exact linked layout and deterministic image.

## Upper 10 KiB: runtime-mapped at `D800h..FFFFh`

| runtime range | bytes | envelope | measured implementation |
| --- | ---: | --- | ---: |
| `D800h..DCFFh` | 1,280 | console policy, geometry, ASCII font | 1,191 implemented; 89 bytes headroom |
| `DD00h..DE7Fh` | 384 | keyboard scan and translation | 328 implemented; 56 bytes headroom |
| `DE80h..E0FFh` | 640 | shared D57/D11 serial layer | 86-byte resident initializer/primitives implemented |
| `E100h..E3FFh` | 768 | NetDisk v3 protocol | 676 implemented; 92 bytes headroom |
| `E400h..E5FFh` | 512 | remote console and bounded status | 368 |
| `E600h..E8FFh` | 768 | common diagnostic mechanisms | 655 |
| `E900h..E9FFh` | 256 | sound and platform initialization | 114 |
| `EA00h..EFFFh` | 1,536 | near-term implementation growth | 0 |
| `F000h..F7FFh` | 2,048 | console extensions, locale/font banks, and extended services | C5 locale bank plus C6 bounded console/multi/raw/sound implementation |
| `F800h..FEFFh` | 1,792 | unassigned reserve | 0 |
| `FF00h..FFFFh` | 256 | ABI manifest, identity, feature bits, fixed vectors | immutable ABI 1.0/1.1 plus compatible ABI 1.2 appended vectors through `FF59h` |
| **total** | **10,240** | exact runtime window | **3,460 measured** |

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

The frozen baseline's live page-zero chain places the CP/M loader at `7A00h`
and BDOS at `7D00h`. Its exact transient span is `0100h..79FFh`, or 30,976
bytes (30.25 KiB). It also has 5,114 bytes above its CP/M 3 BIOS:

- 4,080 initialized adapter bytes at `A000h..AFEFh`;
- 1,034 bytes of mutable state/buffers through `B409h`.

Removing the legacy RAM disk transaction and packing the ROM-ABI platform
binding with the remote console produces a 928-byte initialized adapter,
versus 4,080 bytes for the baseline. The system has been regenerated and relinked with loader
`9A00h`, BDOS `9D00h`, BIOS `BC00h`, and adapter `C000h`. Its exact transient
span is `0100h..99FFh`, or 39,168 bytes (38.25 KiB): an exact 8,192-byte gain.
The live test verifies page zero -> loader `9A06h` -> BDOS `9D06h`, rather than
inferring the gain from link addresses alone.

The dedicated initialized container occupies `9000h..D5FFh`; the adapter code
is `C000h..C39Fh`. Sparse mutable state is kept at `C5ECh..C909h`, below the
fixed ROM gate/workspace beginning at `D600h`. The resident console is 1,191
bytes, its mode-3 helper 119, and the resident read/write NetDisk service 676.
Full cosim reaches `A>`, completes `DIR`, paginated `TYPE README.TXT`,
`DIAG CPU`, explicit `WBOOT`, and `ERA README.TXT`, performs 53 reads and at
least one resident write with no retry or resident
overrun, and proves the final 9,600-byte framebuffer equal to the frozen RAM
oracle.

The separately named C5/C6 consumers add eight-record A:/B: caches at
`CB80h..CF97h` and `CFA0h..D3B7h`, in an otherwise unused part of the same
`C000h..D5FFh` container. The TPA remains `0100h..99FFh`, and C4 stays
byte-exact.

The immutable C6 loaded-system baseline has a 2,924-byte native binding at
`C000h..CB6Bh`. The current post-C6 loaded system uses `C5A0h..C5A1h` for
hot-directory state, `C5C0h..C63Fh` plus `D3C0h..D4BFh` for three measured
directory records, and `D4C0h..D570h` for its 177-byte implementation. Its
sparse adapter container is therefore 5,489 bytes at `C000h..D570h`. This
leaves both the fixed `D600h` ROM workspace and the standalone resident
self-test's `D5C0h..D5FFh` stack/guards untouched, while retaining the
loader/BDOS/BIOS placement and `0100h..99FFh` transient span. The generated
release map derives the end address from the actual adapter and names every
hot-cache and reserved range.

JukuNet C8/ABI 1.3 moves the remaining 733-byte N4/host transport into ROM and
replaces it with a 147-byte CP/M-specific binding at `C4C0h`. GENCPM is then
re-run with adapter top `C200h`: loader `9C00h`, BDOS `9F00h`, SCB `BD9Ch`,
BIOS `BE00h`, and adapter `C200h`. Fixed cache, disk and status storage through
`D570h` is unchanged. Exact C8 TPA is `0100h..9BFFh`, 39,680 bytes—512 bytes
more than C6/C7 and 8,704 bytes more than the original RAM-BIOS baseline. The
27-byte resident host state occupies `D7E0h..D7FAh` inside the existing ROM
workspace and costs no TPA.

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
