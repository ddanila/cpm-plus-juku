# CP/M Plus diagnostics

`DIAG.COM` 0.5 is the safe, shared diagnostic front end for the native
CP/M Plus profile. Its hardware probes come from the pinned `juku-common`
submodule, so ROM and operating-system diagnostics use the same tested
implementations rather than parallel copies.

The immutable C4 recovery image deliberately retains Juku Diag 0.4 extracted
from the accepted prebuilt image. The separately named native recovery, full,
demo, and applications profiles contain Diag 0.5. This separation lets the
diagnostics evolve without changing the C4 qualification artifact.

## Commands

With no argument, `DIAG` preserves the original private 256-byte RAM-data
baseline. `DIAG ALL` runs the complete non-destructive suite. Individual
selectors are:

- `CPU`, `MEM`, `ADDR`, `RET`, `RAM`, and `SUM` for processor and memory
  checks;
- `PIT` for a non-destructive latch/read check of D57 channel 0;
- `USART` for the D11 PE/OE/FE status bits without consuming received data or
  clearing the receiver;
- `ROM` for resident manifest and ROM-ABI integrity gates;
- `VIDEO` for framebuffer/output readiness;
- `KEY` for the keyboard/S21 input path;
- `IO` for PIT, USART, video, and keyboard together;
- `ALL` for the complete safe suite.

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

The native adapter marker at C642h gates this service, preventing Diag 0.5
from mistaking the immutable C4 entry 30 for the versioned USERF interface.
Host absence or rejection cannot block the local result, console, or disk.

`make native-services-check` proves both a single `DIAG CPU` report and a
combined `DIAG IO` report. The latter must publish pass mask `7Ch`, fail mask
zero, and flags zero while the production ROM, CP/M image, and NetDisk host are
running in cosimulation.
