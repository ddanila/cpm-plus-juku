# Digital Research CP/M Plus 3.1 inputs

The binary inputs in this directory come from John Elliott's Unix CP/M 3.1
release dated 2026-06-07:

- upstream: <https://www.seasip.info/Cpm/software/dri.html>
- archive: `cpm3bin_unix.zip`
- archive SHA-256:
  `ec24f6e1fa173d33bcd2555dfae8296471fc8ea144c72e8cbe2166971451da82`

`ccp.com`, `bdos3.spr`, and `gencpm.dat` are copied byte-for-byte from that
archive. `gencpm.dat` supplies the upstream non-banked defaults; the
regeneration script deliberately overrides its memory-top answer with `9Fh`.
`scb.asm` is copied from the matching `cpm3src_unix.zip` source archive
(SHA-256 `d90cda1f25112ace3b436c4054304ace423331caa1f034c44f26698728a9fdb7`).

`cpm3.sys` was generated from those inputs, the source-controlled Juku
`src/cpm3-bios.asm`, and the DRI RMAC/LINK/GENCPM tools with a non-banked 9Fh
memory top. The generated map is:

```
BIOS3.SPR  9C00h  0400h
BDOS3.SPR  7D00h  1F00h
```

This deliberately leaves `A000h..AFFFh` for the project-owned Juku hardware
adapter and `B000h..B409h` for its runtime state. At runtime the CP/M loader
occupies `7A00h..7CFFh`, so the exact transient span is `0100h..79FFh` (30,976
bytes, historically rounded to the 31 KiB baseline).

`cpm3-network-rom.sys` is the separately generated resident-ROM consumer. It
uses a non-banked `BFh` memory top and the map:

```
BIOS3.SPR  BC00h  0400h
BDOS3.SPR  9D00h  1F00h
```

The thin adapter starts at `C000h`. The runtime loader occupies
`9A00h..9CFFh`, producing the measured transient span `0100h..99FFh` (39,168
bytes, 38.25 KiB), exactly 8 KiB above the frozen baseline.

Regenerate the checked-in SYS file with ZXCC and a directory containing the
DRI `RMAC.COM`, `LINK.COM`, and `GENCPM.COM` development tools:

```sh
tools/regenerate_cpm3.py --zxcc /path/to/zxcc \
    --tools /path/to/cpm3-tools

tools/regenerate_cpm3.py --zxcc /path/to/zxcc \
    --tools /path/to/cpm3-tools --adapter-address 0xc000 \
    --top-page 0xbf --output third_party/cpm3/cpm3-network-rom.sys
```

The recipe converts both assembler sources to CP/M line endings, assembles the
Juku BIOS and standard SCB module, links `BIOS3.SPR`, answers GENCPM
deterministically, and rejects a map inconsistent with the selected adapter.
The checked-in SHA-256 values are:

- baseline: `60f9da29c77599a08639fdf3236205c5ba4431301d66dbb46b7f5dd22d206c1f`;
- network ROM: `9427093f64dedd6c7be3db055983073c76436d07530a8b20b4f83fcb6c5edff1`.

CP/M-hosted tool revisions are part of reproducibility. The tools used for the
network-ROM SYS have SHA-256
`d3132c8e356d0c8e71b53757445e7ef89e55dfda9dbda11c48cf7ede6c2c40f3`
(`RMAC.COM`),
`714115910168df0900a41698551d518c921fe8329dae78378756f2445a4dc175`
(`LINK.COM`), and
`3a71036c6a6571f62dcb93f9434c140354d3601d17cabc0d38702811b2a33d87`
(`GENCPM.COM`). A normal build does not execute or require these tools; it
consumes the reviewed SYS files above.

The Juku BIOS source is BSD-2-Clause project code. CP/M and its derivatives
are distributed under the current DRDOS grant reproduced in `LICENSE.md`.
