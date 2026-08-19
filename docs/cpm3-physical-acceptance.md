# CP/M Plus physical acceptance runner

`tools/physical_acceptance.py` is the C6 acceptance path for the full,
development, display, and performance workloads. It is separate from the immutable C4 promotion
recorder: C4 retains its historical candidate, checklist, and hashes, while
this runner binds each new physical run to the current post-C6 loaded system
and the unchanged C6 ROM.

The runner requires `8080-cosim` commit `59034760` or later. That host records
the structured request stream consumed by the independent timing audit; an
older server which merely prints request lines is intentionally insufficient.

## What a passing run proves

The runner verifies the C6 boot manifest before opening the serial device. It
hash-checks the ROM and metadata, V16 stream, system image, selected A: image,
read-only native B:, workload, host server, both standard host modules, and
runner. The server and its `janet_netboot.py`/`janet_fastboot.py` dependencies
are copied together into `inputs/` and executed from that retained set; the
physical run therefore cannot silently import different live-tree code. A
fresh private copy of A: is made for each run and served in synchronous
write-through mode; the manifest image is never modified.

The host and target evidence are independent. `boot.json` proves that the
bound system reached its first valid NetDisk request at 19,200 baud. A run is
accepted only when the N4 transcript also contains every expected target
reply and the final CCP prompt for every command. Disk traffic alone cannot
turn a command into a pass.

Pager recognition is ASCII-case-insensitive because CP/M's built-in `TYPE`
and the DRI `DUMP` utility capitalize `Continue` differently.

The full workload runs 30 commands covering all 20 nonvisual acceptance
programs. It includes paginated reads, Status, buffered Keytest,
every admitted DRI utility, both four-record PIP/CRC copies, the nonzero-user
warm boot, and native B:. The development workload runs the baseline plus all
four admitted development programs, including scripted SID and ED sessions.
The B: directory assertion names `DIAG.COM`, which is licensed project
material in the manifest-bound approved-apps image; external game disks are
not treated as distribution acceptance media.
The injected Keytest line waits briefly after the `READY` marker so CP/M's
BDOS output-time flow-control poll cannot consume its first byte while the
marker line is still being completed.
The display workload boots the full image, runs `VIDTEST`, retains its complete
mode/locale transcript, leaves the page visible for 60 seconds, exits it, and
requires the returned CCP prompt. It automates target evidence but cannot
replace the human analog-display observation described in
[`cpm3-video-acceptance.md`](cpm3-video-acceptance.md). The declarative
definitions are:

- `physical/workloads/full.json`;
- `physical/workloads/development.json`;
- `physical/workloads/display.json`;
- `physical/workloads/performance.json`.

Every `Press RETURN to Continue` is handled automatically. Interactive input
steps are explicit hex payloads in the workload, recorded by hash, and sent
only after their target-side ready marker. The operator therefore supplies
only power/reset; no catalogue commands need to be typed by hand.

## Bench commands

Build and bind the current artifacts first:

```sh
cd ~/fun/cpm-plus-juku && make c6-manifest-check
```

Start the full run before powering or resetting CS00015:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py run /dev/ttyUSB0 --profile full --output out/physical-CS00015-full
```

Then run the development image in a separate session:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py run /dev/ttyUSB0 --profile development --output out/physical-CS00015-development
```

For one display mode (repeat with the four documented S21 settings):

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py run /dev/ttyUSB0 --profile display --output out/physical-CS00015-display-40x24
```

For the controlled M4 comparison, start the cache-off run, cold-power or reset
CS00015, and let all ten commands finish:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py run /dev/ttyUSB0 --profile performance --manifest out/cpm-plus-juku-c6-control-manifest.json --output out/physical-CS00015-m4-control
```

Then stop/power-cycle the target, run the otherwise identical cache-on system,
and audit the pair:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py run /dev/ttyUSB0 --profile performance --output out/physical-CS00015-m4-optimized
cd ~/fun/cpm-plus-juku && python3 tools/physical_performance.py out/physical-CS00015-m4-control out/physical-CS00015-m4-optimized --output out/physical-CS00015-m4-comparison.json
```

After the full, development, control, and optimized runs all exist, close the
entire blind hardware queue with one independent cross-run audit:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_closure.py out/physical-CS00015-full out/physical-CS00015-development out/physical-CS00015-m4-control out/physical-CS00015-m4-optimized --output out/physical-CS00015-closure.json
```

This final report does more than concatenate four passes. It requires the
current full/development systems and media, both successful PIP/CRC `4613`
copies, every development workflow, the controlled M4 decision, and identical
CS00015, C6 ROM, and host-server identities across all four retained bundles.
It deliberately reports the four-mode analog display observation as remaining;
blind N4 evidence cannot close that separate visual gate.

After all four display runs and photographs exist, record their human
observations with the schema and run the independent display auditor described
in [`cpm3-video-acceptance.md`](cpm3-video-acceptance.md). The blind closure
report and display acceptance report are intentionally separate: the first
proves target behavior visible over N4, while the second proves what the named
analog monitor actually showed.

Once both reports pass, produce the one final physical-promotion decision:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_promotion.py out/physical-CS00015-closure.json out/physical-CS00015-display-acceptance.json --output out/physical-CS00015-promotion.json
```

This command does not trust two `status: pass` strings. It follows their exact
input paths, rehashes and re-audits all eight retained runs plus the observation
document and photographs, reconstructs both lower-level decisions, and then
requires one CS00015, C6 ROM, optimized system/Fastboot, and host identity.
Only that report has an empty `remaining` list.

Re-audit the retained final report later without recreating it by hand:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_promotion.py --audit out/physical-CS00015-promotion.json
```

The audit follows both recorded report paths, verifies their hashes, and then
re-executes the blind, display, and final cross-identity decisions from their
original run bundles and photographs. An edited final report or changed input
cannot remain a pass.

The control is not a fallback or release image. It is built from the same
current sources and immutable C6 recovery A: as the optimized run, with only
`HOT_DIRECTORY` omitted. Its exact system/Fastboot identities are
`e68158497438b19c` / `294e85b80ce824fc`; the optimized identities are
`57de00733bea16a3` / `3c2cf62d43b78678`. The audit requires 10/0/1 and B: 4/1
for the control, 8/0/1 and B: 4/0 for the optimized system, zero retries, and
synchronous erase writes in both. A final `DIAG USART` must also report clean
D11 PE/OE/FE state; this is an end-of-workload hardware-status observation,
not a claim that physical 8251 errors can be counted retrospectively. The
runner records—but does not manufacture a pass from—elapsed timing from the
first disk request to `A>`.

The default 30-minute operator wait is a host-side bench policy. The runner
recognizes the verified server's initial `Booting` line before target attach
and derives enough complete V16 rediscovery attempts to cover that interval;
an operator power/reset delay therefore cannot consume a short fixed startup
window. This does not change the ROM's bounded V16 parser, NetDisk retry
policy, or recovery semantics. Each command remains bounded to ten minutes
and the complete host session to three hours. These limits can be reduced
explicitly for automated benches.

The runner always asks the isolated host process to stop with one `SIGINT` and
waits for its atomic media shutdown. A forced termination makes the run fail.
It retains:

```text
result.json    complete machine-readable decision and artifact identities
boot.json      bootstrap and first-NetDisk timing evidence
console.bin    raw target N4 replies
host.log       complete Janet/NetDisk/N4 server log
events.jsonl   timestamped host, target, command, input, and shutdown events
requests.jsonl timestamped structured NetDisk/N4 request trace
cpm-plus-juku-<profile>.img  private post-run writable A:
inputs/        exact manifest, binaries, media, workload, host modules, runner
```

On a target timeout or wrong reply, `result.json` remains usable and records
the failed command, byte offsets, response hash, console tail, and host tail.
The host still shuts down cleanly.

## Independent audit

Recheck a retained result without rerunning hardware:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py audit out/physical-CS00015-full
```

The audit rehashes every bound artifact and evidence file, validates the boot
identity, verifies the private volume chain, reconstructs each command reply
from its byte offsets in `console.bin`, and requires every marker and prompt.
It independently rebuilds per-boot and per-command read, record, write, retry,
and wire-byte counts from `requests.jsonl`; the host and runner share the
kernel monotonic clock, so request attribution does not depend on log text.
Boot timing additionally records the interval from the first real disk request
to `A>`, excluding how long the operator took to power or reset the machine.
Changing a transcript, workload, host log, boot result, artifact, command
status, or post-run volume invalidates the result.

`make physical-acceptance-check` exercises paging, interactive input, timeout
diagnostics, a complete fake-host lifecycle, clean shutdown, evidence audit,
tamper rejection, an independently launched retained standard host, all four
real workload definitions, and the current C6 manifest.

`make physical-closure-check` additionally proves the exact four-bundle
identity/coverage contract and rejects wrong systems, missing CRC evidence,
incomplete development coverage, mixed hosts, or mixed boards.
`make display-acceptance-check` proves the four-mode human-observation schema,
exact transcript/artifact binding, monitor-cropping policy, photograph hashes,
and representative negative cases.
`make physical-promotion-check` proves that neither lower-level report can be
omitted, prematurely closed, or mixed across board, ROM, system, host, or
display mode, and that the retained final report fails after either it or a
lower-level input changes.
The already established exact-C6 full and development cosim suites remain the
runtime authority until the two corresponding CS00015 result directories have
also passed this physical audit.

## 2026-08-19 CS00015 result

The full workload passed 30/30 commands, the development workload passed
10/10, and both same-source performance workloads passed 10/10 with zero
retries. The independent M4 comparison accepted 10 -> 8 cold reads and 1 -> 0
first-B:-`DIR` reads; the four-run blind closure passes. Exact identities,
timings, coverage, recovery observations, and the remaining display-only gate
are recorded in
[`cs00015-post-c6-acceptance-20260819.md`](cs00015-post-c6-acceptance-20260819.md).
