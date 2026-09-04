# Reset-safe stock-ROM host profile

The stock-ROM recovery profile deliberately keeps the serial link at
9,600 baud, 8O1 through every phase: Janet ROM loading, accelerated system
transfer, and NetDisk v3. This makes a warm or cold target reset observable
without guessing which baud rate is active and lets a listening host restart
CP/M automatically.

The profile preserves the useful stock-assisted boot optimizations. The Janet
loader sends only the 128-byte core, the core downloads a compact extension,
and that extension receives the ZX0-compressed 16 KiB CP/M system. Its distinct
`JF17` / `ZH` identity prevents an older 19,200-baud `JF15` artifact from being
used accidentally in reset-recovery mode. Historical `JF15` outputs remain
unchanged for reproduction and comparison.

The generated pair is:

- `out/cpm-plus-juku-stock-recovery-system.bin`: a `JUKURM1` image loading at
  `7000h`, entering at `9C00h`, with a 9,600-baud NetDisk platform adapter.
- `out/cpm-plus-juku-stock-recovery-fastboot-v17.bin`: its matching checked
  `JF17` accelerated bootstrap bundle.

Build and verify it with:

```sh
make out/cpm-plus-juku-stock-recovery-system.bin \
     out/cpm-plus-juku-stock-recovery-fastboot-v17.bin
make stock-recovery-check
```

The check verifies the system header and CRC, 9,600-baud sign-on, explicit D57
count-8 and 8251 8O1 setup, `JF17` metadata, compressed-stream CRCs, and a
deterministic rebuild of the bundle.
