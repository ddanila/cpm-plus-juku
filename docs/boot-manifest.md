# Native boot and media manifest

`make manifest-check` generates
`out/cpm-plus-juku-native-manifest.json` from the exact native system,
fastboot stage, and distribution reports. It is a host-visible contract, not a
second source of build values.

The manifest records:

- JUKURM1 load address, entry address, payload length, CRC-16/IBM, file size,
  and SHA-256;
- fastboot format/version, file size, and SHA-256;
- required Intel 8080, ROM ABI 1.0, fastboot v15, NetDisk v3, 19,200-baud, and
  framing settings plus the required runtime service set, including explicit
  capability query and retained bootstrap report;
- every published A:/B: profile with image hash, geometry, physical layout,
  and recommended media policy;
- a stable build identity derived from the native system hash.
- two named, hash-bound system/bootstrap slots: current native and immutable
  C4 compatibility.

The production Janet server accepts `--boot-manifest`. Before opening the
serial device it verifies the selected system, optional fast stage, A:,
optional physical B:, NetDisk version, and disk baud. A stale binding or media
mismatch therefore fails closed rather than reaching real hardware. The
manifest path, hash, and build identity are also copied into boot timing JSON.

The manifest advertises images without Janet station identity. It does not
add a ROM menu, authentication, or a second recovery protocol; those remain
separate measured decisions.

This static artifact contract is complemented by NetDisk-v3 operation 26h:
after boot, the target can explicitly query the connected server's protocol,
read-ahead bound, runtime feature bits, and drive count. The manifest prevents
the host from opening a stale artifact set; the on-wire query prevents target
software from guessing runtime services from a banner or station identity.
Operation 27h separately publishes the C5 retained bootstrap stage/retry tuple;
it is an observability report, not a replacement for capability negotiation.

The production host can pair the two manifest slots with an atomic
last-known-good state file. Every slot gets the configured bounded restart
budget; exhaustion moves automatically to the other slot. A slot is promoted
only when the running target sends its first valid disk request, not when the
bootstrap bytes were merely accepted. State includes both system and fast-stage
hashes and is ignored if either no longer matches the selected manifest.

The ABI 1.1 C5 desk candidate has a separate generated manifest,
`out/cpm-plus-juku-c5-manifest.json`. It binds the C5 ROM and its metadata to
the matching locale-native system/fastboot pair, declares ROM ABI 1.1, names
that primary slot `c5-native`, and retains the immutable C4 compatibility
slot. Keeping this separate prevents the ordinary ABI 1.0 native manifest
from silently becoming a C5 claim. The deterministic package and promotion
boundary are described in
[`cpm-plus-31-c5-release-candidate.md`](cpm-plus-31-c5-release-candidate.md).

The ABI 1.2 C6 simulator candidate similarly has
`out/cpm-plus-juku-c6-manifest.json`. It binds the C6 ROM/metadata, extended
system and Fastboot V16 stage, dedicated C6 recovery volume, and immutable C4
fallback. Its requirements explicitly say Fastboot 16; the ROM metadata binds
the 361-byte embedded loader and zero-byte executable wire extension.
Its required feature list adds bounded console span, ordered NetDisk multi,
raw keyboard, and sound. `tests/c6_boot_manifest_test.py` rejects a stale C5
system, missing service, wrong slot, media mismatch, or changed build identity.
The deterministic simulator package and its non-claim of physical promotion
are described in [`cpm-plus-31-c6-simulator.md`](cpm-plus-31-c6-simulator.md).
