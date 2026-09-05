# C12 CS00000 console regression fixtures

These are byte-exact N4 console captures from physical CS00000 on 2026-09-05,
running the C12 ABI 1.5 ROM and the manifest-bound C12 CP/M payload.
S21 reads 0F (80x24 / Estonian). No screen appearance is inferred from N4.

- `cold.console`: `out/physical-CS00000-c12-cold-20260905/console.bin`.
  The original cold profile passed STATUS and DIAG ALL; its audit passed.
- `full-resumed.console`:
  `out/physical-CS00000-c12-full-resumed-20260905/console.bin`.
  This used an explicit resumed workload after host replacement. The original
  run failed its final DEFAULT expectation because CONSOLE prints the video
  and charset override flags on separate lines. The capture retains the
  earlier receive-timeout/reconnect history and successful warm-boot state.

The test pins both hashes and replays replies through the current workload
executor. Modified copies exercise rejection of incorrect state and support
for S21 bit 0 and line-layout variants. These offline replays do not change
the retained physical session verdicts or qualify physical video/reset tests.
