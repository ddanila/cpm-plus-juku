# CP/M 3 nonzero-user warm boot

The Juku BIOS reloads `CCP.COM` from the recovery A: volume instead of keeping
a resident CCP. Its loader formerly inherited the transient program's current
CP/M user number. A warm boot or BDOS Function 47 chain started from user 1..15
therefore searched for `CCP.COM` in that user area and stopped with
`Juku CP/M Plus BIOS cannot load CCP.COM`.

Native C6, full, development, and demo volume profiles now install user-0
`CCP.COM` with CP/M's read-only and system attributes. CP/M 3's ordinary BDOS
open path can consequently resolve the public system file while the current
user is 1..15. This costs no resident BIOS bytes and leaves the immutable C4
recovery image unchanged. The volume builder validates declarative `r`, `s`,
`a`, and F1..F4 attributes, applies them with `cpmchattr`, and records nonempty
attributes in its reproducibility report.

The native C6/full `WBOOT.COM`, built from `wboot-user.asm`, deliberately
selects user 1 immediately before jumping through the warm-boot vector. The
existing production cosimulation therefore exercises the public CCP lookup on
every warm-boot run. The C4 profile retains the original three-byte
`wboot.asm`, so its immutable image remains byte-identical.
