# Future C9 ROM policy

Status: **DECISION RECORDED; NO C9 BUILD AUTHORIZED**

C8 uses S21 bit 0 to select immediate automatic network boot versus a
concealed local-`N` recovery wait. The recovery path has no prompt, monitor, or
alternative boot destination. Pressing `N` merely begins the same network boot
that the automatic setting begins at reset.

A future C9 or later ROM will therefore always attempt network boot. S21 bit 0
is reserved for a later feature and has no assigned replacement meaning. A
future proposal must justify that bit with a user-visible or operationally
distinct behavior; it must not reuse the bit merely because it is available.

This decision does not change the immutable C8 image, its ABI 1.3 contract, or
existing C8 machines. It is also not enough reason to create, qualify, program,
or deploy C9 alone. The policy should enter the next ROM only when another
measured improvement already justifies a separately named candidate and full
simulator and physical qualification.

## CP/M Plus boundary

CP/M already ignores bit 0. It consumes S21 bits 2:1 for the four video modes
and bits 4:3 for the character bank; bits 7:5 remain reserved. No CP/M system,
disk, utility, or ABI change is required for the future unconditional-boot
policy.

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
