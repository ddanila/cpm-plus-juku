# CP/M Plus physical acceptance runner

`tools/physical_acceptance.py` is the C6 acceptance path for the full,
development, and display workloads. It is separate from the immutable C4 promotion
recorder: C4 retains its historical candidate, checklist, and hashes, while
this runner binds each new physical run to the current post-C6 loaded system
and the unchanged C6 ROM.

## What a passing run proves

The runner verifies the C6 boot manifest before opening the serial device. It
hash-checks the ROM and metadata, V16 stream, system image, selected A: image,
read-only native B:, workload, host server, and runner. A fresh private copy of
A: is made for each run and served in synchronous write-through mode; the
manifest image is never modified.

The host and target evidence are independent. `boot.json` proves that the
bound system reached its first valid NetDisk request at 19,200 baud. A run is
accepted only when the N4 transcript also contains every expected target
reply and the final CCP prompt for every command. Disk traffic alone cannot
turn a command into a pass.

The full workload runs 29 commands covering all 19 nonvisual acceptance
programs. It includes paginated reads, Status, buffered Keytest,
every admitted DRI utility, both four-record PIP/CRC copies, the nonzero-user
warm boot, and native B:. The development workload runs the baseline plus all
four admitted development programs, including scripted SID and ED sessions.
The display workload boots the full image, runs `VIDTEST`, retains its complete
mode/locale transcript, leaves the page visible for 60 seconds, exits it, and
requires the returned CCP prompt. It automates target evidence but cannot
replace the human analog-display observation described in
[`cpm3-video-acceptance.md`](cpm3-video-acceptance.md). The declarative
definitions are:

- `physical/workloads/full.json`;
- `physical/workloads/development.json`;
- `physical/workloads/display.json`.

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

The default 30-minute operator wait is a host-side bench policy. It prevents a
human power/reset delay from consuming the server's short normal startup
window; it does not change the ROM's bounded V16 parser, NetDisk retry policy,
or recovery semantics. Each command remains bounded to ten minutes and the
complete host session to three hours. These limits can be reduced explicitly
for automated benches.

The runner always asks the isolated host process to stop with one `SIGINT` and
waits for its atomic media shutdown. A forced termination makes the run fail.
It retains:

```text
result.json    complete machine-readable decision and artifact identities
boot.json      bootstrap and first-NetDisk timing evidence
console.bin    raw target N4 replies
host.log       complete Janet/NetDisk/N4 server log
events.jsonl   timestamped host, target, command, input, and shutdown events
working-a.img  private post-run writable A:
inputs/        exact manifest, binaries, media, workload, host, and runner
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
Changing a transcript, workload, host log, boot result, artifact, command
status, or post-run volume invalidates the result.

`make physical-acceptance-check` exercises paging, interactive input, timeout
diagnostics, a complete fake-host lifecycle, clean shutdown, evidence audit,
tamper rejection, all three real workload definitions, and the current C6 manifest.
The already established exact-C6 full and development cosim suites remain the
runtime authority until the two corresponding CS00015 result directories have
also passed this physical audit.
