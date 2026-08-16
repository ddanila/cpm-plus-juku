# Reproducible CP/M Plus system toolchain

The two checked-in non-banked `CPM3.SYS` inputs can be regenerated entirely
from pinned repository inputs:

```sh
make cpm3-system-check
make regenerate-cpm3 regenerate-cpm3-rom
```

The build compiles ZXCC 0.5.7 from its unmodified pinned source archive. It
extracts RMAC and DRLINK from the pinned CP/M 3.1 source release and GENCPM
from the matching binary release. `regenerate_cpm3.py` verifies all archive
and tool hashes before executing them. DRLINK is exposed as `LINK.COM`, the
name used by the original build recipe.

## Deterministic normalization

Unmodified GENCPM places the six printable bytes `654321` in the SYS file's
distribution-serial header. The Juku distribution does not claim that Digital
Research serial, so the generator verifies the expected input and clears the
field.

The maintained GENCPM initializes the SCB date to CP/M day `0712h` (15
December 1982). The qualified Juku baseline uses CP/M day `06B5h` (13
September 1982, the CP/M Plus 3.0 release date). The generator locates that
runtime SCB field through the reverse-record SYS layout, verifies the GENCPM
value, and writes the named Juku baseline value. This is an initial clock
value, not an executable checksum.

Those two policies reproduce the older, qualified A000h stock-ROM/RAM-BIOS
SYS input. The later C000h network-ROM candidate was generated with GENCPM's
metadata unchanged; its recipe names `--metadata-policy gencpm`. Keeping this
difference explicit preserves both immutable histories instead of silently
rewriting either candidate. Fresh outputs are byte-for-byte identical to both
SYS inputs, and the normal `make check` gate performs both comparisons.
