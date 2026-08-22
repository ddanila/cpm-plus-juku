# CP/M Plus diagnostics

`DIAG.COM` 0.6 is the safe, self-contained diagnostic front end for CP/M Plus.
Its hardware mechanisms come from the pinned `juku-common` submodule and are
linked into the transient program. DIAG does not call a stock-ROM or JukuNet
ROM diagnostic procedure, so the same binary runs meaningfully with either
firmware family.

The immutable C4 recovery image deliberately retains Juku Diag 0.4 extracted
from the accepted prebuilt image. The separately named native recovery, full,
demo, and applications profiles contain Diag 0.6. This separation lets the
diagnostics evolve without changing the C4 qualification artifact.

## Commands

With no argument, `DIAG` prints its command summary and returns. `DIAG HELP`
does the same. A selected command prints only the short version/ROM identity
header and its result; usage is not repeated on every invocation. `DIAG ALL`
runs the complete non-destructive suite. Individual selectors are:

- `CPU`, `MEM`, `ADDR`, `RET`, `RAM`, and `SUM` for processor and memory
  checks;
- `PIT` for a non-destructive latch/read check of D57 channel 0;
- `USART` for the D11 PE/OE/FE status bits without consuming received data or
  clearing the receiver;
- `ROM` for a direct read-only fingerprint/integrity pass over the complete
  ROM-visible `D800h..FFFFh` window;
- `VIDEO` for portable CP/M BIOS output readiness;
- `KEY` for two stable direct S21 scans through D26, independent of ROM code;
- `IO` for PIT, USART, video, and keyboard together;
- `ALL` for the complete safe suite.

Each invocation reports its detected ROM. Exact fingerprints identify the six
archived EktaSoft releases, JMON 2.2/3.3, EktaSoft 4.4 #01/#02, and JukuNet
C4--C8; a compatible future JukuNet image falls back to its manifest version
and build string. Unknown images print their four-byte fingerprint. The
RomBios-compatible all-RAM baseline is switched to mode 1 only for the bounded
ROM read and the prior memory-mode byte is restored before BDOS output.

`DIAG DESTRUCT` is intentionally refused while CP/M is live. Destructive RAM,
address-bus, or retention work belongs in the ROM diagnostics, where the
operating system and user data cannot be overwritten accidentally.

## Machine-readable result

Every completed native diagnostic command publishes one bounded, idempotent
NetDisk-v3 operation `25h` with four bytes: suite identifier, pass mask, fail
mask, and flags. Bits in the two masks are:

| Bit | Meaning |
| ---: | --- |
| `01h` | CPU |
| `02h` | RAM/memory |
| `04h` | D57 PIT |
| `08h` | D11 USART |
| `10h` | ROM/integrity |
| `20h` | video |
| `40h` | keyboard/S21 |
| `80h` | retention |

The native adapter marker at C642h gates this service, preventing Diag 0.6
from mistaking the immutable C4 entry 30 for the versioned USERF interface.
Host absence or rejection cannot block the local result, console, or disk.

`make diag-check` proves that every compiled fingerprint/identity matches its
archived ROM image and that the source has no ROM diagnostic call. `make
diag-compat-cosim-check` boots the byte-exact EK37/RomBios 3.43m path and runs
no-argument `DIAG` plus `DIAG ALL`; the JukuNet C8 gate checks
help-versus-selected output. `make
native-services-check` retains the machine-report checks; `DIAG IO` must
publish pass mask `7Ch`, fail mask zero, and flags zero.
