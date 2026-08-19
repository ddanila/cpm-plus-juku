# CS00015 post-C6 acceptance — 2026-08-19

Status: **BLIND CLOSURE PASSED; FOUR-MODE ANALOG DISPLAY OBSERVATION PENDING**

## Scope

CS00015 ran the manifest-bound post-C6 full, development, cache-off control,
and cache-on optimized workloads over the physical D11/D57/D104 serial path.
All input and output after power-on used the N4 remote console; the external
display was unavailable. The retained evidence therefore proves the complete
monitor-independent target matrix and the M4 disk decision, but makes no new
claim about analog geometry, glyph appearance, pseudographics, or cursor
visibility.

Each run retained the exact manifest, system, Fastboot stream, ROM, A:/B:
media, workload, host server and imported modules, runner, raw console,
structured NetDisk/N4 trace, host log, and private post-run A: image. The four
results independently pass `physical_acceptance.py audit`, and their combined
`physical-CS00015-closure.json` passes `physical_closure.py`.

## Bound identities

| item | SHA-256 |
| --- | --- |
| combined JukuNet C6 ROM | `0487d5150f9b662a193b3f031aadd90002ee232477d355d3877a757a247c2f09` |
| optimized system | `57de00733bea16a3ce6427b8e010649727c6b0d84144724c43c5114a1cf35091` |
| optimized Fastboot V16 | `3c2cf62d43b7867844b18fb142fbae8c49bdc83a148fcb22bfac9a8a26b32d67` |
| cache-off control system | `e68158497438b19ca3773d2ec11d91a0ddf888e351c0d9cd559e8b4c6e223ea7` |
| cache-off control Fastboot V16 | `294e85b80ce824fcf08829369d3ce2ff3c1a7d6268e246a0c780dbe92f32adcd` |
| full A: | `21fb8112aa908624fc52b17993b9d0a383c83ad4443059703c4b9e48e1453fd5` |
| development A: | `5ff16bf3e2a8588674a6b12b3d8f9640cea16c152ff2e692140b9ec5634ddfcd` |
| recovery/performance A: | `67d0a99b2979642d6f7d5d9c20ef705be685c99f1ab7846b8cf4f3ea383a54b0` |
| approved native B: | `1003053769cac8c8b8dc3fef21039f3ce55071d4274701fe929effff6dcdb8b6` |
| retained host server | `f05fdbd535181e67c46cc95ca5a848e4031c6eee9a6f5bfd7276ba349b29c7c7` |
| retained runner | `b37dd330f4ba02f56ba9fe93a4a3edefe5deaab2b582120900edb93416564e4b` |

The full, development, and optimized runs use the same optimized system,
Fastboot, ROM, and host. The control differs only in the same-source
`HOT_DIRECTORY` omission and its resulting system/Fastboot bytes.

## Physical results

| run | target commands | first disk request to `A>` | boot reads | total reads/writes | retries | result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| full | 30 | 4.126 s | 9 | 271 / 18 | 0 | pass |
| development | 10 | 4.363 s | 9 | 90 / 7 | 0 | pass |
| M4 cache-off control | 10 | 3.654 s | 10 | 42 / 1 | 0 | pass |
| M4 cache-on optimized | 10 | 3.234 s | 8 | 34 / 1 | 0 | pass |

The full workload exercised every one of its 20 nonvisual acceptance
programs, two differently capitalized DRI pagination prompts, buffered local
keyboard injection, two PIP/CRC `4613` copies, attributes, negative command
paths, warm boot under user 1, writable A:, and approved native B:. The
development workload additionally rebuilt and ran HELLO through HEXCOM,
entered/exited SID, ran PATCH, edited and saved a file with ED, read it back,
and warm-booted. Both private writable images changed as expected while their
manifest inputs remained immutable.

Both performance runs used the same recovery A:, B:, ROM, host, workload,
baud, media policy, and physical board. Each ended with clean `DIAG USART`,
completed warm boot, synchronously erased `README.TXT`, and proved the erased
directory state. The independent comparison reports:

- cold login: 10 requests / 80 records to 8 requests / 64 records;
- first A: `DIR`: zero additional requests in both runs;
- first B: login: four requests in both runs;
- first B: `DIR`: one additional request to zero;
- cold disk-to-prompt observation: 3.654 s to 3.234 s;
- no NetDisk retry in either run.

This physically accepts the M4 hot-directory cache. Elapsed time remains an
observation because N4 console output dominates several command durations;
the request-count reduction is the promotion decision.

## Recovery and runner findings

The first development power-on occurred after the old fixed host window had
expired. Starting a fresh host while CS00015 remained powered attached to the
ROM's persistent overlap-safe V16 scanner, transferred the system, and reached
`A>` without RESET. This is additional real-board evidence for late-host
recovery.

The session also exposed a runner defect: its documented 30-minute operator
wait began only after boot, while the retained host had just three complete
pre-boot retries and exited after about 30 seconds. The runner now recognizes
the verified host's initial `Booting` line as ready and derives enough complete
bootstrap restarts from `--operator-wait`; a regression pins 600 restarts for
the default 1,800-second window. This changes future bench orchestration, not
the target, ROM, system, or validity of the retained successful runs.

Preflight runs also caught and corrected retained-host import completeness,
private-volume basename binding, Keytest handoff settling, case-insensitive
DRI pager handling, and the approved B: directory expectation. Failed traces
were kept under distinct dated `out/` directories and were never relabeled as
passes.

A RESET-only attempt during preflight exhausted the V16 header retries, while
cold power-on and live late-host attachment passed. It is retained as a
separate recovery observation rather than being confused with this successful
cold-boot matrix; future host/ROM timing work may reproduce and narrow it.

## Decision and remaining boundary

`physical-CS00015-closure.json` has SHA-256
`c61c8584764d08ae92b5e8de5647c84845cce5007d7c3d1721e98a2de34e01c4`
and reports `pass`. Its only remaining item is the four-mode analog display
observation. No further blind CS00015 experiment is required for this plan.

Final physical promotion still requires the four S21/VIDTEST sessions and
photographs described in
[`cpm3-video-acceptance.md`](cpm3-video-acceptance.md). Those observations can
be performed later without another EPROM burn, then combined with this blind
closure by `physical_promotion.py`.
