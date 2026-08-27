# CP/M 3 volatile session state

The separately named session-native profile extends reserved BIOS
USERF entry 30 with one generic, keyed volatile-session slot. It exists for small state that must survive a
warm boot or transient replacement but must not cause disk writes. It is not a
configuration store and is cleared on every cold system load.

## USERF contract

Call through BDOS Function 50 with BIOS function 30.

| Selector | Input | Result |
| ---: | --- | --- |
| 6, read | `B` destination capacity, `DE` four-byte owner, `HL` destination | `A=0`, `B=length`; `A=1` empty/other owner; `A=2` too small |
| 7, write | `B=1..127`, `DE` owner, `HL` source | `A=0`, `B=length`; `A=2` oversized |
| 7, release | `B=0`, `DE` owner | clears only a matching owner; otherwise `A=1` |

Owner and payload bytes are opaque to CP/M. There is one slot, so a new
nonzero write replaces the prior owner atomically: length is cleared first,
then owner and payload are copied before the new length is published. Readers never observe a
partially published new blob.

## Fixed ownership map

| Range | Owner |
| --- | --- |
| `C5A0h..C5A1h` | hot-cache validity and drive |
| `C5A2h..C5A5h` | four opaque owner bytes |
| `C5A6h` | payload length and publication marker; zero means unclaimed |
| `C5C0h..C63Fh` | independent retained directory sector 1 |
| `D3C0h..D43Eh` | 127-byte payload while claimed; directory sector 2 otherwise |
| `D440h..D4BFh` | one reserved record containing the 119-byte session service |
| `D4C0h..D570h` | session-aware hot-cache code |

The former third hot record is deliberately retired to hold code. Before a
session claim, records 1 and 2 remain available. While claimed, the payload
owns record 2 but record 1 continues to fill and hit normally. A drive change
or disk write clears only cache-valid state; `HDINIT` on a cold load clears
both cache validity and the session length.

The hot-cache code ends before the existing CCP `!!` state at
`D571h..D5BFh`, the `D5C0h..D5FFh` resident self-test guards, and the `D600h`
ROM workspace. It does not alter the TPA, the independent A:/B: read-ahead
buffers, the existing CCP history, or immutable C5 artifacts.

The ordinary C6/C7 and C8 profiles remain byte-identical and retain all three
hot records. The session profile retains records 1 and 2 until claimed and
record 1 afterward; its measured boot/`DIR`/`TYPE` counts remain 8/0/1 and
B: login/first `DIR` remains 4/0.

## Acceptance

`make session-state-check` pins selectors 6/7 in the session profile,
the exact code address, 127-byte bound, publish ordering, strict 8080 code,
the hard `D571h` non-overlap boundary, cold-empty state, owner isolation,
size failures, release, warm-boot persistence, and unchanged NetDisk counts.
VC/8080's focused system owner additionally exercises real reads and writes
through repeated Function 47 transient reloads, then proves the backing disk
image remains byte-identical.
