# CS00015 CP/M Plus NetDisk-v3 timing diagnosis

## Bench signature

The first CP/M Plus 3.1 qualification on CS00015 reached the banner but then
printed `CP/M Error On A: Disk I/O` indefinitely. The host saw each opcode
`14h` directory request three times before the sequence advanced, matching the
client's three-attempt bound. A deliberately short seven-byte status-error
reply was accepted, while the real multi-record reply was not. The failure was
therefore in sustained host-to-Juku response handling, not basic 19,200-baud
framing, request transmission, synchronization, sequence matching, or CRC.

The stock-`TN` path also exposed two independent symptoms. Before the adapter
masked D10, stale frame and USART interrupts left a cursor/stalled-console
artifact. Masking the PIC removed that artifact on the physical board. The V15
payload completed and CP/M started, but the host did not observe the final
`JA` completion frame before the resident system reprogrammed D11.

## Faithful simulator reproduction

The regression uses CS00015's measured effective CPU clock of 1.70 MHz and
paces the emulator against wall time. This is essential: the Janet server's
guards are wall-clock sleeps, while an unpaced emulator can execute tens of
thousands of fictional CPU cycles during a 2 or 4 ms guard.

The 8251 model now consumes an already queued PTY stream at the D57-derived
wire cadence instead of restarting a whole character time after every late CPU
poll. A full receive register therefore causes a genuine overrun and loses the
new byte, as on the one-byte-buffer D11. Checkpoints record the overrun count.
No test injects a synthetic disk error: each negative fixture assembles the
real old algorithm or selects the real old server scheduling behavior.

The paced matrix reproduces all three boundaries:

| Fixture | Result | Mechanism |
| --- | --- | --- |
| old 400-iteration target drain | repeating disk I/O error, duplicate requests, modeled overruns | host response begins while command `35h` still owns the transmit turn |
| old queue-time-only 4 ms server guard | repeating disk I/O error, duplicate requests, modeled overruns | the guard expires while the USB-UART queue is still shifting the preceding descriptor |
| old stock-`TN` unmasked PIC | disk/console corruption with live frame and USART IRQs | CP/M enables interrupts with the monitor's sources and handlers still active |
| corrected direct `N` path | `A>`, `DIR`, `DIAG CPU`; zero retries and overruns | all three boundaries corrected |
| corrected stock `TN` path | `A>`, `DIR`, `DIAG CPU`; zero retries and overruns | all three boundaries corrected after stock bootstrap |

## Root causes and corrections

### Half-duplex target turnaround

The old request drain used 400 iterations of a 24-cycle loop, about 9,600
cycles or 5.65 ms at 1.70 MHz. The host receives the final checksum after it
leaves the shifter and waits another 2 ms, but that still allows its reply to
arrive roughly 2.5 ms before the target's old loop releases TxEN. The overrun
trace consequently loses `J`, sequence, status, and record count while D11 is
still in command `35h`.

The corrected 128-iteration delay is about 1.81 ms. It exceeds the worst-case
two-character pipeline bound (about 1.15 ms at 19,200/8O1), yet selects
receive-only command `34h` before the host's reply guard expires.

### Host record-boundary timing

`write()` reports that bytes entered the kernel/USB queue; it does not report
that they reached Juku. The old server queued a descriptor and immediately
started its 4 ms decoder guard. A roughly 100-byte first directory descriptor
takes about 57 ms on a 19,200/8O1 wire, so that guard was entirely consumed
long before the last descriptor byte arrived. The next descriptor followed
without an on-wire processing gap.

The server now accounts for every queued 11-bit character before starting the
4 ms record guard. This is equivalent to waiting for physical transmit drain
and remains valid for the PTY model. It costs no extra descriptor transmission
time: the sleep overlaps time that the UART must spend shifting those bytes in
any case.

### Fill expansion and PIC ownership

The fill decoder formerly loaded and stored a RAM counter on every output
byte, about 6,800 cycles for a 128-byte fill. It now keeps the counter in `A`,
reducing the hot loop to about 3,500 cycles and adding margin inside the
explicit record gap.

The CP/M Plus adapter masks every PIC input before its final `EI`. Its console,
keyboard, and NetDisk implementations are polled RAM code and do not retain
EktaSoft's interrupt service ownership. The regression assembles the old
unmasked branch and proves that frame/USART IRQs are actually taken.

The missing final V15 `JA` frame remains a separate acceptance item. Increasing
the tight extension changed its exact streaming length and exposed a direct
bootstrap timing boundary, so that speculative change was rejected. The final
bench run will determine whether the corrected disk turnaround also removes
the apparent completion loss before changing the already-qualified V15
transport.

## Qualification state

The failures are reproduced and both corrected boot variants are
simulator-qualified. The 2026-08-15 CS00015 rerun then established an important
split result:

- stock `TN` loaded and started the CP/M Plus payload, but the wrapper again
  missed the final V15 `JA` completion and returned the host to 9,600-baud
  discovery;
- CP/M consequently displayed repeated A: I/O errors because no 19,200-baud
  disk server remained attached;
- without resetting Juku, stopping that wrapper and starting the corrected
  NetDisk-v3 server manually at 19,200 recovered the machine to `A>`;
- `DIR` completed and the full `DIAG` program passed and returned to the prompt;
- after recovery, requests advanced without duplicate sequence numbers. The
  earlier sequence 01h..06h failures occurred while the wrapper had left the
  host at 9,600, not in the corrected resident protocol.

The resident NetDisk-v3 timing correction is therefore physically qualified.
One-command stock-ROM boot is not: final V15 completion detection/handoff is a
separate remaining defect. Closing it requires a host-observed final `JA`, no
fallback to discovery, and immediate service of the first disk request. A
longer sequential read remains desirable final qualification but no longer
blocks the disk-turnaround diagnosis itself.

Run the complete paced desktop matrix with `make check` from this repository.

## 2026-08-16 stock-ROM/manual-resume follow-up

Before burning the network-first ROM, CS00015 was retested with its existing
Ekta4401 monitor and the current all-RAM CP/M Plus payload. Two `TN` attempts
confirmed the same split boundary:

- stock Janet accepted station `01 -> 08`, loaded the 128-byte core, retried
  the extension once, and started CP/M;
- the host did not accept the final V15 stream completion, resumed 9,600-baud
  discovery, and the live CP/M displayed repeated A: I/O errors;
- without RESET, a production `--resume-disk` server attached at 19,200/8O1;
- `A>` returned, `DIR` produced normal disk requests, `DIAG` passed twice, and
  `WBOOT` returned to the prompt;
- request sequence numbers advanced through `64h` with no observed duplicate
  or retry in the resumed session.

The private evidence directory is
`out/stock-CS00015-baseline-20260816` (intentionally ignored rather than
published as mutable media). Its final files are fixed here by hash:

| file | bytes | SHA-256 |
| --- | ---: | --- |
| `host.log` | 2,348 | `3f32e14b30723129d6fc3738eb85dac823b685587a7f43dc6824cd0cee9730d6` |
| `resume.log` | 6,935 | `3d805a91ccdb1d1a60b86fe46385c47bdd1c09370c6b27d1af639238326a9c19` |
| private A: image | 409,600 | `b4402dc9be86fef9532e61fff491dc3b93dc0db40e68d575c89aab083160bec1` |

This follow-up strengthens the resident NetDisk and warm-boot result but does
not qualify the stock one-command V15 handoff. It also exposed deterministic
malformed compact glyphs. That independent display issue was traced to the
font generator's 8-vs-9-pixel source-sheet pitch, corrected, and promoted to
the C2 bench candidate before any network ROM was burned.
