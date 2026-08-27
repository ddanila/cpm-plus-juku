# C9 unconditional-network-boot policy

Status: **IMPLEMENTED IN THE C9 SIMULATOR/HDL CANDIDATE; PHYSICAL
PROGRAMMING NOT AUTHORIZED**

C8 uses S21 bit 0 to select immediate automatic network boot versus a
concealed local-`N` recovery wait. The recovery path has no prompt, monitor, or
alternative boot destination. Pressing `N` merely begins the same network boot
that the automatic setting begins at reset.

C9 therefore always attempts network boot. S21 bit 0 is reserved for a later
feature and has no assigned replacement meaning. A future proposal must
justify that bit with a user-visible or operationally distinct behavior; it
must not reuse the bit merely because it is available.

This decision does not change the immutable C8 image, its ABI 1.3 contract, or
existing C8 machines. The policy entered C9 only alongside the independently
justified bounded resident-host transport and ABI 1.4 telemetry. That
separately named candidate has completed simulator/HDL qualification, but this
decision still does not authorize programming or deployment.

## CP/M Plus result

CP/M already ignores bit 0. It consumes S21 bits 2:1 for the four video modes
and bits 4:3 for the character bank; bits 7:5 remain reserved. No CP/M system,
disk or utility change was required for unconditional boot itself. The
separate C9 ABI 1.4 host telemetry is exposed through the matching `STATUS`
1.4 system profile.

The current CP/M Plus implementation has no urgent feature gap. Remaining work
is deliberately evidence-driven:

- preserve S21 as the cold-reset console default while considering the
  separately specified runtime mode and character-bank override in
  [`runtime-console-switching.md`](runtime-console-switching.md);
- physically observe all four video modes when a usable display is available;
- profile alternating-drive and long sequential workloads before proposing a
  new NetDisk contract or predictor;
- add distribution utilities only for a demonstrated workflow and with source,
  license, strict-8080, disk, TPA, and stack evidence;
- keep Millfork as the preferred optional high-level-language experiment;
- keep write-back caching, cryptographic boot, XMODEM, and banked CP/M outside
  the baseline until their benefit and failure semantics are concrete.
