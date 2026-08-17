# CS00015 C4 blind qualification, 2026-08-17

This record preserves the first physical run of the automatic network-first
ROM without relying on a connected display. The board was CS00015. The fitted
EPROMs were the C3-labelled pair, which is byte-identical to C4:

| socket | SHA-256 |
| --- | --- |
| D15 low 8 KiB | `3e8b9eb2f3752002821e6ec18dd59805108389c9d93aba40316bd2e18eb7684f` |
| D16 high 8 KiB | `f15b1b029edd845e0aa7622d61e9b84740957dce1f38a75867cedccef54494ac` |

## Failure found in the C3 matching runtime

Reset required no keypress. The host missed the one-shot C4 ready byte, used
the synchronized V15 fallback, sent the compressed system in 4.33 seconds,
and received a valid NetDisk request. N4 output then showed the CP/M Plus
banner and `A>` prompt. Remote input did not respond.

The host PTY still contained all five submitted bytes (`DIR` plus two carriage
returns from the probes). Thus neither the PTY, serial link, nor N4 transport
had lost the command. The CP/M ROM-ABI adapter had called the resident ROM's
deliberately blocking local `CONIN` after its first empty N4 poll. Once inside
that routine, it could not poll a remote byte that arrived after the prompt.

## C4 correction and rerun

The corrected binding enables N4 for the direct network-ROM consumer, checks
resident `CONSTAT` before entering resident `CONIN`, and loops through N4 while
the local keyboard is idle. The resident-ROM build uses eager idle polling and
immediately polls again after consuming a remote byte. These changes affect
only the downloaded CP/M system and V15 bundle; the EPROM pair did not need to
be rewritten.

The rerun used:

| artifact | SHA-256 |
| --- | --- |
| CP/M Plus ROM system | `a0a98915ba570b6816eadb096f9d885514dca9987c2070c123552397b1adc80e` |
| V15 fastboot bundle | `991eabf57360528c1a28fedab2013e94542348870aebd0de7ea8b60452765d3f` |

Observed boot evidence:

- automatic reset and synchronized V15 fallback, with no keypress;
- 7,301 compressed bytes sent in 4.329 seconds at 19,200/8N1;
- first valid NetDisk-v3 request 6.070 seconds after the bootstrap request;
- no bootstrap retry and no disk retry;
- N4 confirmed by target output request, then the banner and `A>` appeared;
- remote `DIR` listed `CCP.COM`, `DIAG.COM`, `WBOOT.COM`, and `README.TXT`;
- remote `DIAG CPU` reported `CPU: PASS` and returned to `A>`;
- explicit remote `WBOOT` returned to `A>`;
- a second remote `DIR` passed after warm boot.

The host was stopped cleanly after the second directory and the writable A:
image was saved. The run did not observe the physical screen, cursor, local
keyboard, write/erase behavior, repeated cold starts, or live host-loss and
reattachment, so none of those remaining C4 acceptance items is inferred as a
physical pass.

## Regression coverage

The automatic-ROM N4 cosim now waits 250 ms after observing `A>` before it
sends the first command. This forces the emulated CPU into the same idle local
input path that exposed the hardware failure. The corrected image completed
`DIR`, paginated `TYPE README.TXT`, `DIAG CPU`, explicit `WBOOT`, and
`ERA README.TXT`: 1,378 reads, one write, zero retries, zero resident overruns,
and zero bootstrap overruns. The complete legacy/direct/stock/network fault,
restart, and video-mode matrix also passed, as did the C4 ABI/POST and
structural HDL gates.

## Repeated cold boots and complete blind matrix

A later auditable session on the same day ran three independent power-on
boots of the exact C4 package. Every run used a fresh private writable copy of
A: and completed the same monitor-independent sequence: automatic boot without
a keypress, the CP/M Plus banner and `A>`, `DIR`, paginated
`TYPE README.TXT`, `DIAG CPU`, explicit `WBOOT`, `ERA README.TXT`, and a final
directory proving that the file was gone.

| cold boot | first valid NetDisk request | N4 transcript SHA-256 |
| ---: | ---: | --- |
| 1 | 6.070435849 s | `308a010722d53d859d005ed41f6368b4845c556148f6fa28a6eb091f1044ef92` |
| 2 | 6.069430049 s | `308a010722d53d859d005ed41f6368b4845c556148f6fa28a6eb091f1044ef92` |
| 3 | 6.068261806 s | `308a010722d53d859d005ed41f6368b4845c556148f6fa28a6eb091f1044ef92` |

All three runs used 7,301 compressed bytes, reported a 4.33-second bulk V15
transfer, and needed no extension or stream retry. The host missed both the
one-shot ROM-ready byte and final V15 reply in every run, then safely used the
synchronized probe/fall-through path. The first valid NetDisk request
independently confirmed execution; no system retransmission was attempted.
The identical 931-byte N4 transcripts make the command result repeatable as
well as the boot timing.

## Live host replacement and PTY false failure

The first automated replacement-host attempt appeared to fail: the new host
received continuous target N4 polls, but `DIR` never appeared. A traced rerun
showed more than two complete 8-bit sequence-number laps of valid, increasing
poll requests and valid empty replies while the host input queue remained
exactly zero. The Juku had neither hung nor stopped proving liveness.

The cause was entirely on the Linux host. The qualification worker queued
`DIR` immediately after spawning the server, and the server's subsequent
`tty.setraw()` used flush semantics, discarding that input before its first
poll. The corrected server selects raw mode without flushing, and the recorder
does not start its console worker until the server explicitly announces that
the N4 PTY is open and configured. Both boundaries have regressions.

Without resetting or rebooting CS00015, the corrected replacement host then
joined the already-running 19,200/8O1 session. Poll sequence `9Bh` delivered
`D`, `9Dh` delivered `I`, `9Fh` delivered `R`, and `A1h` delivered carriage
return. Each character was echoed through a following N4 output transaction;
the directory listed `CCP.COM`, `DIAG.COM`, and `WBOOT.COM`, then returned to
`A>`. This physically passes host loss and live NetDisk/N4 reconnection without
RESET. No ROM or downloaded CP/M correction was required.

The remaining C4 acceptance observation is local rather than blind: with a
monitor connected, confirm the resident 80x24 output, readable glyphs,
blinking underline cursor, and physical keyboard (including the repaired Space
key) against this exact candidate. Earlier RAM-console runs already qualify
the shared 53x24 and 64x20 implementations, but they are not substituted for
this final resident-C4 observation.
