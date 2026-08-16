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
