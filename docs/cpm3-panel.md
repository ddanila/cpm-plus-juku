# Juku CP/M Plus control panel

Status: **M5 DESK-QUALIFIED; OPTIONAL PHYSICAL SMOKE PENDING**

`PANEL.COM` is the first real text-interface consumer of the connected CP437
glyph set. It presents a compact machine, console, network, and safety summary
in 80x24 mode. It is project-owned BSD-2-Clause strict-8080 code and is present
only in the full, development, and museum-demo profiles. Recovery profiles are
unchanged.

The panel does not read PIT, USART, S21, or other hardware ports. It obtains
raw S21, selected video mode, ROM ABI, retained boot stage/retry count, last
disk status, and N4 reconnect count from the versioned JNS1 record returned by
the existing CP/M 3 USERF service. This keeps `STATUS.COM` and `PANEL.COM` on
one native source of truth and avoids duplicating diagnostic code in a
transient program. Fixed lines identify the strict Intel 8080, 39,168-byte TPA,
19,200-baud NetDisk-v3 baseline, synchronous writes, and retained C4/C5
recovery paths.

The connected CP437 glyphs exist only in the five-pixel 80x24 renderer. PANEL
therefore checks the selected mode before clearing the screen. Other S21 modes
receive a short explanatory message and return to CP/M rather than displaying
question marks or an invalid border. In 80x24 it draws a full-screen frame,
uses blank rows between sections, leaves the final cell for the real
blinking underline cursor, and waits for one key. Local display and keyboard
remain authoritative; N4 can mirror the same output and provide the exit key.

The exact C6 ROM renders the connected single-line
`DAh/BFh/C0h/C4h/B3h` set, and PANEL uses it for English, Russian CP866, and
the remapped-English bank. `C4h` is also ISO-8859-1 `Ä`, so the Estonian bank
correctly gives that byte to the selected letter. PANEL therefore uses an
explicit `+/-/|` ASCII frame only in Estonian instead of corrupting the letter
or relying on double-line cells which the fitted C6 ROM does not contain. A
dedicated Estonian N4 framebuffer run guards that fallback. The bottom-right
cell remains reserved for the cursor in either frame.

## Admission evidence

| item | measured result |
|---|---|
| `PANEL.COM` | 1,349 bytes; SHA-256 `db8e2696c39b6466b629a7f8fca837cc921ad57662f319b6b6b94c77d1a1e74c` |
| loaded range | `0100h..0644h` |
| observed stack | 12 bytes, `9CFEh..9CF2h`, one segment, no explicit SP write |
| remaining measured TPA | 37,807 bytes after image plus observed stack |
| English hidden/visible framebuffer | SHA-256 `b15d2b862aa7bfcebe4b470ed8a55c254ec998841a0d1470cf16cb912b83672f` / `462d35ce8e146306734658613ef9a5a37ba09ac9021ac66368046d11ff98d7c2` |
| Estonian hidden/visible framebuffer | SHA-256 `43bb9b8710ad9ae6be52553d700167e0504c4b83cc77545e5de2c0efa4fc6cdf` / `fa591622fdc5525aacb54bdec1fc48fbfa8555e1f506ee4ee72049df99e8281f` |

`tools/panel_oracle.py` constructs the documented 80x24 transcript and renders
it from the human-readable Creep/CP437 source glyphs. It verifies every border
code before producing the two 9,600-byte cursor phases. This is independent of
the 8080 drawing loop and does not use OCR or screenshots.

`make panel-cosim-check` then boots the exact C6 ROM, current V16 system, and
full image. The English local and Estonian N4 console paths load PANEL from
NetDisk, match both framebuffer phases byte-for-byte, accept the exit key,
return to CCP, warm boot, and complete the ordinary write/erase regression
with zero retries and zero USART overruns. The local run records six NetDisk
requests, 48 read-ahead records, and the stack measurement above. Static
fetched-opcode admission observes no Z80 prefixes or undocumented 8080
aliases.

A hardware run is intentionally short: use S21 mode 3, boot the unchanged C6
ROM and current full image, enter `PANEL`, confirm joined borders and plausible
values, then press one key. No EPROM burn is required. Exact pixels remain the
simulator oracle; a photograph records analog monitor cropping separately.
