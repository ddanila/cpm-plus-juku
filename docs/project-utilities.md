# Juku CP/M Plus project utilities

The normal `full-a`, `museum-demo-a`, and `development-a` profiles contain a
small set of project-owned, strict-8080 tools for gaps not covered by standard
CP/M Plus commands. Recovery profiles remain unchanged.

| command | purpose | bounded behavior |
| --- | --- | --- |
| `CRC file` | CRC-16/CCITT-FALSE and record count | read-only; includes all bytes in each physical 128-byte CP/M record |
| `CMP file1 file2` | record-exact comparison | read-only; reports first record/offset or which file ends first |
| `MEM address [length]` | memory hex/ASCII view | read-only; exactly four address digits, optional two-digit length, maximum 40h bytes |
| `WC textfile` | line, word, and byte counts | stops at CP/M text EOF 1Ah; six-digit hexadecimal counts |
| `FIND textfile token` | case-insensitive matching lines | one token up to 31 characters; displayed lines are capped at 120 characters |
| `STRINGS file` | printable ASCII runs | minimum length four; scans physical records and treats 1Ah as binary data |
| `HIST [CLEAR]` | inspect or clear one persistent CCP command | validates bounded state; two exclamation marks at the CCP repeat the entry |
| `VIDTEST` | geometry/font/cursor acceptance page | read-only; derives S21 through CP/M 3, waits for one key, and never writes framebuffer memory directly |
| `PANEL` | compact machine/network status screen | read-only; uses the shared JNS1 status ABI and connected CP437 borders in 80x24 mode, with a collision-safe Estonian ASCII frame; waits for one key |

The volume includes `TOOLS.TXT` with the target-side synopsis. `TYPE`, `PIP`,
`REN`, `ERA`, and DRI `DUMP` retain their established CP/M names and are not
duplicated as `cat`, `cp`, `mv`, `rm`, or another hexdump.

## Simulator admission

`make distribution-cosim-check` runs useful paths through every command while
the shared simulator records actual fetched instructions in the full
0100h--99FFh TPA. It requires no Z80 prefixes or undocumented 8080 aliases.
The regression pins these independent results:

- `CRC README.TXT` is `4613` over four zero-padded physical records;
- `CMP` recognizes `CRC.COM` as itself and locates the first mismatch against
  `README.TXT` at record 0000h, offset 00h;
- `MEM 0100 10` displays the exact first 16 bytes of its loaded program;
- `WC README.TXT` reports 14h lines, 3Bh words, and 1FAh bytes;
- `FIND README.TXT Juku` returns four known matching lines;
- `STRINGS README.TXT` returns the known NetDisk description.
- a large `SHOW` command survives CCP reload, repeats through `!!`, remains
  retained across blank/overlong input, and is then displayed and cleared by
  `HIST`.

`make vidtest-cosim-check` separately validates `VIDTEST` because its useful
result is a live framebuffer rather than a text reply. Seven exact-C6 runs
cover every geometry and locale bank and capture both cursor phases; the
independent oracle covers all sixteen video/locale combinations. See
[`cpm3-video-acceptance.md`](cpm3-video-acceptance.md).
The separately licensed CCP derivative and exact-C6 history admission are in
[`cpm3-command-history.md`](cpm3-command-history.md).
`make panel-cosim-check` executes `PANEL` through local and N4 console paths,
captures both cursor phases, and compares all 9,600 framebuffer bytes with the
source-glyph oracle. Its machine values come from the same versioned JNS1
record as `STATUS.COM`; it contains no direct peripheral reads or duplicated
diagnostic implementation. See [`cpm3-panel.md`](cpm3-panel.md).

`STATUS`, `DATE`, `DIAG PIT`, and the native-service test already cover the
safe clock/timing requirement. No unrestricted `PORT` command is shipped:
Juku peripheral reads can have acknowledgement or reset side effects, and
the existing diagnostic suites are the maintained allow-list.
