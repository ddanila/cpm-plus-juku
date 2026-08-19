# Project history

The first simulator-proven Juku CP/M Plus baseline was developed temporarily
on CP/Mish's public `juku` branch. Its complete original patch remains
available in `ddanila/cpmish` as commit
`59b8528e6c73ee1ea704b9f6bddcfcf96fc82eca` (subject: “Add simulator-proven
Juku CP/M Plus”, 2026-08-15).

Once the experiment proved that a genuine Digital Research CP/M 3 system could
boot on the Juku model, it was separated here rather than presented as a new
CP/Mish version. CP/Mish commit
`40451f3fe14c0030dd26c80eb796db9a25f258c2` (subject: “Separate CP/M Plus into
its own project”, 2026-08-15) removes the duplicate implementation while
deliberately retaining the prototype in that repository's published history.

The standalone tree begins with commit `4267d00`. During extraction, reusable
Juku platform and direct-fastboot modules moved to `ddanila/juku-common` commit
`aa1b4bfa2cc623c946e5d31ae6003d9b341dc4ce`. CP/Mish and this project consume
the same pinned shared sources but retain independent BIOS policy, memory map,
system generation, artifacts, tests, and release plans.

On 2026-08-16 the network-first ROM consumer completed its first measured
relink milestone. `juku-common` commit `84e3a59` added the dedicated fastboot
layout; this repository regenerated CP/M Plus with loader/BDOS/BIOS at
`9A00h`/`9D00h`/`BC00h` and moved its thin adapter to `C000h`. The live
page-zero chain proves a 39,168-byte transient span, exactly 8 KiB larger than
the frozen baseline, while the complete simulator matrix retains all legacy
failure reproductions and passes direct, stock, and automatic-ROM boot paths.

The same day, `juku-common` commit `8f7de93` and `8080-cosim` commit
`0ed8ccee` moved synchronous writes behind ABI 1 using NetDisk-v3 operation
`15h`. The real CP/M regression erases `README.TXT` through the resident
write-through path, while cache invalidation, CRC, retry bounds, and the frozen
RAM artifacts remain proven. Removing the unreachable RAM transaction and
packing the remote console reduced initialized ROM-consumer adapter RAM from
1,360 to 912 bytes without changing the measured TPA.

The recovery checkpoint, supported by `8080-cosim` commit `385ff167`, then
extended the deterministic matrix through target
reset with stale bootstrap bytes, shortened/delayed/duplicated/corrupt disk
replies, modeled 8251 overruns, and replacement by a fresh stateless disk
server. Clean and faulted runs all reach the real prompt and complete directory,
diagnostic, and write-through operations without a manual target reset.

After those gates passed, `8080-cosim` commit `ac347cdb` named the unchanged
ROM bytes `network-first-abi1-cs00015-c1` and released them only for controlled
CS00015 qualification. `make bench-candidate` now assembles the exact D15/D16,
CP/M system, fastboot, and disk inputs into one hashed package; promotion still
depends on the documented physical matrix.

`8080-cosim` commit `68da3972` subsequently closed the full cursor-cycle
oracle without changing the C1 ROM hash. The CP/M regression gained a
three-byte `WBOOT.COM`, paginated sequential file reads, replacement of the
disk server after the prompt, and a 16-cycle post-reconnect soak. That run
completed 271 reads and one synchronous write with no target retry or overrun;
the updated A: image hash is fixed by the C1 package record.

`8080-cosim` commit `fefe01cb` then carried the candidate across a focused
structural-HDL boundary without changing its production ROM hash. The exact C1
image reaches reset/POST target-ready `C4h` through `juku_top`/`vm80a`; test-only
dispatch around the unchanged resident bytes proves the framebuffer helper,
matrix keyboard, serial ABI, and a CRC-checked 128-byte NetDisk-v3 DMA record.
`make bench-candidate` now includes this structural gate while retaining the C
model for full CP/M, recovery, cursor-pixel, and soak coverage.
The combined release run also exposed that the deliberately unmasked-PIC
negative fixture can corrupt the memory-mode latch after proving its intended
live-interrupt failure. Its oracle now exempts only that corrupted branch from
the healthy-mode invariant; every corrected and transport-only path retains
the exact required mode.

The physical boundary is now executable rather than a prose-only checklist.
`tools/physical_qualification.py` verifies C1, records repository and EPROM
identity, preserves per-boot host logs and timing, works on a private writable
disk copy for each attempt, and refuses acceptance without three cold boots
plus every manual display, keyboard, command, write, warm-boot, and recovery
observation. A new
production `--resume-disk` server mode (`8080-cosim` `8a3300e2`) permits the
required host-loss/later reattachment test without resetting or retransmitting
a system image.

The first stock-ROM setup attempt usefully exposed a shutdown boundary before
qualification began: terminal Ctrl+C reached both the recorder and its child,
and a second signal interrupted the child's non-atomic disk rewrite. The
reference package was never at risk because every run uses a private A:. The
recorder now starts the server in an isolated process group and forwards one
SIGINT, while `8080-cosim` commit `75c7a0fd` atomically replaces writable
volumes.

The ensuing 2026-08-16 stock-ROM CS00015 baseline deliberately exercised the
new all-RAM CP/M before burning the network ROM. Stock `TN` again loaded and
started the system but missed the final V15 completion and fell back to 9,600,
leaving repeated A: I/O errors. Attaching the production server directly at
19,200 without resetting recovered `A>`. `DIR` generated clean disk traffic,
`DIAG` passed twice, and `WBOOT` returned to the prompt; request sequences
advanced through `64h` without retries. The captured private evidence hashes
are recorded in `docs/cs00015-netdisk-v3-timing.md`.

That run also exposed stable malformed compact glyphs. The previous
framebuffer checks compared consumers that shared the same generated font, and
the older transcript oracle parsed that generated table, so neither could
detect a source-extraction error. `juku-common` commit `ec662a2` corrected the
font sheet's vertical pitch from 8 to 9 pixels and added a human-readable
source-glyph oracle. The old table now fails first at U+0032 row zero. The
corrected CP/M BIOS framebuffer matches an independently rendered 875-byte
transcript in all 9,600 bytes. C1 was never burned; `8080-cosim` commit
`c2581698` names the corrected exact ROM C2 and reruns the C model and all
three structural-HDL gates.

By 2026-08-17 the byte-identical C3/C4 ROM baseline had completed three
CS00015 automatic cold boots at 6.068--6.070 seconds. Each run produced the
same remote-console transcript and completed directory, sequential-read,
diagnostic, warm-boot, and write/erase checks. A live replacement host also
delivered `DIR` without RESET after a recorder fix stopped raw-mode setup from
flushing prequeued input. This leaves only exact resident display, cursor, and
local-keyboard observation before C4 promotion.

The post-baseline work then completed the separately named ABI 1.1 C5 desk
candidate: reset-latched S21 video/locale/boot policy, key remapping, retained
bootstrap diagnostics, native CP/M 3 services, independent eight-record A:/B:
caches, explicit capabilities, reproducible distribution profiles, and bounded
native/C4 system slots. `make release-candidate` now binds the exact C5 ROM
halves to the matching locale-native CP/M Plus 3.1 system, media reports,
licenses, and manifest in a byte-reproducible tar. C5 remains unpromoted until
its complete physical acceptance matrix is recorded.

On 2026-08-18 the Priority 7 external-software and host-compiler audit replaced
candidate-name guesses with exact, executable evidence. Kevin Boone's GPLv3
`cpm-ls` now has a reproducible z88dk port and passes strict-8080 execution,
but measured 55/188-read normal/long listings keep it out of default profiles.
The core FIG-Forth 1.1 listing likewise builds and returns cleanly to CCP but
lacks the complete editor/assembler/documentation package required for
admission. Unexplained z80pack `HIST` binaries and Z80-generating `uplm80` are
rejected. Matching Millfork and z88dk `hello`, `cat`, and `wc` fixtures rebuild
byte-for-byte and pass strict execution, while hand-written 8080 assembly
remains the production baseline.

The same audit completed the target development workflow without relaxing the
source-required boundary. Digital Research ED was added only to the separate
development profile and now passes a prompt-synchronized insert, save, CCP
return, and exact TYPE readback under strict 8080 execution. SID remains an
exact assembly-source rebuild. ASM and LOAD are absent from the pinned CP/M 3
release, while the source-less MAC, RMAC, and DRLINK binaries remain host-side
ZXCC reproduction inputs and cannot enter a target image.

The Priority 7 closeout then moved every admitted Digital Research program
onto the current C6 admission path. Nine full-profile and four development
programs now have exact disk allocation, transient/RSX placement, and
command-scoped live stack evidence under the 39,168-byte TPA, in addition to
their canonical static 8080 listings. The simulator executes all thirteen on
the network-first ROM/native BIOS and fails on any Z80 prefix, undocumented
alias, mismatched profile report, or altered memory record. Six project-owned
gap tools pass the same fetched-opcode path. With the external candidates and
compiler experiments given explicit measured dispositions, `make check` now
closes the complete feature plan through Priority 7 rather than only the
frozen C0--C6 platform baseline.

The final requirement audit caught that those full/development runtime jobs
still inherited the harness's ABI 1.0 ROM default even though their matching
TPA geometry made the measurements look C6-compatible. Both jobs now select
the exact ABI 1.2 C6 ROM, extended native system, and V16 stream explicitly,
and every metrics document carries their names, sizes, and SHA-256 identities.
The admission checker rejects an ABI 1.0 substitution before considering any
stack result. Running the development path on C6 also replaced an accidental
ED prompt dependency with the command's actual post-insert `CR/LF + *` prompt.
The legacy timing regressions also stopped reusing shared adapter objects: each
fixture now builds private platform, keyboard, NetDisk, and console modules
from Make's exact `juku-common` selection, so an unrelated local rebuild cannot
silently change or break the frozen failure oracle.

On 2026-08-19 the remaining M4 physical gate became a controlled executable
experiment. The current source now builds a 2,924-byte cache-off control and
the ordinary 5,489-byte cache-on adapter against the same C6 ROM, V16 protocol,
recovery A:, native B:, and workload. Exact simulation pins 10/0/1 plus B: 4/1
against 8/0/1 plus B: 4/0. A structured host request trace and the physical
runner's shared monotonic command boundaries produce independently audited
read, record, write, retry, wire-byte, and first-disk-request timing evidence;
the pair auditor rejects mismatched systems, hosts, media, workloads, counts,
retries, or absent synchronous erase writes.

The ordinary `make check` gate now includes that controlled comparison rather
than leaving it as a documented side command. The physical workload also ends
with the shared non-destructive `DIAG USART` probe: each retained control and
optimized run must have zero protocol retries, complete its synchronous erase,
and observe clean D11 parity/overrun/framing status. This final status sample
is recorded as such and is not misrepresented as a historical error counter.

The resulting source state passed the complete ordinary gate and the separate
C6 release-candidate gate. The latter retained the exact 64-cycle result of
992 reads, 257 synchronous writes, zero retries, and zero modeled overruns and
reproduced archive SHA-256 `1a4f963315252596`. The audit leaves the full/dev,
controlled M4, and analog-display CS00015 runs explicitly physical rather than
promoting them from simulator evidence.

The four remaining blind result bundles now have one closure auditor. It
rehashes and independently audits each retained run, then requires exact
current full/development artifacts, both PIP/CRC `4613` copies, the development
workflow, the controlled M4 decision, and one shared CS00015/C6-ROM/host
identity. Its report keeps the analog four-mode display gate open rather than
mistaking remote-console success for a visual observation.

The remaining visual boundary now has an equally explicit but separate
record. A machine-readable four-mode schema retains monitor identity, raw S21,
geometry, edge/cropping notes, readable glyphs, locale stability, both cursor
phases, joined 80x24 CP437 lines, and hashed photographs. Its auditor rechecks
the exact physical runner artifacts and target transcript for every mode and
rejects mixed hosts, wrong modes, unexplained cropping, stale photographs, or
an absent cursor phase. This completes the desk plan for display evidence; it
does not claim the four pending CS00015 observations have been performed.
