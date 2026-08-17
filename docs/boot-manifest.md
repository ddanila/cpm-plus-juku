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
  capability query;
- every published A:/B: profile with image hash, geometry, physical layout,
  and recommended media policy;
- a stable build identity derived from the native system hash.

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
