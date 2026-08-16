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
