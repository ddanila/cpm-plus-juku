# CP/M Plus multi-record PIP warm-boot correction

Status: **SIMULATOR-QUALIFIED; CS00015 CONFIRMATION PENDING**

This note records the post-C6 loaded-system correction for the repeatable
`PIP COPY.TXT=README.TXT` stop. The immutable C6 ROM in CS00015 does not
change; only the CP/M system and its compressed V16 stream change.

## Observed failure

On 2026-08-18 CS00015 completed all four source-record reads, destination
writes, and directory writes with successful NetDisk acknowledgements, but
did not return to `A>`. A second attempt behaved identically. The production
simulator reproduced the exact command and retained the failed RAM and served
disk image.

The copied file itself was correct. The retained simulator state instead
showed corrupted command-processor execution:

- every disk acknowledgement completed and USART overruns remained zero;
- the CPU eventually entered the default DMA/command area at `0080h`;
- it fetched README byte `76h` at `00C8h` as an 8080 `HLT` and stopped at
  `PC=00C9h`, with the page-zero WBOOT and BDOS vectors still intact;
- a stop at `PC=0080h` preserved the preceding execution path: warm boot
  loaded CCP, entered it at `0100h`, and then ran corrupted low memory.

This ruled out a host timeout, serial failure, bad destination data, and a
missing remote-console prompt.

## Root cause

DRI PIP's fast-copy path uses BDOS function 44 to select a multi-sector count.
For a multi-record file it can leave that process-wide count above one when it
exits through warm boot.

The project-owned `load$ccp` loop was single-record code. It set DMA, called
BDOS sequential read, and advanced the destination by exactly 128 bytes. It
did not reset function 44 first. With a retained count of four or twelve,
BDOS returned multiple CCP records per call while the loader advanced only
one record. Successive chunks overlapped, producing a corrupted `CCP.COM` in
the TPA. A one-record `PROFILE.SUB` copy left the count at one, which is why
the old admission workload passed.

## Correction

Before opening `CCP.COM`, `load$ccp` now performs:

```asm
        mvi     e,1
        mvi     c,44
        call    bdos
```

The structural native-services test requires this sequence. It does not alter
BIOS write-through behavior, NetDisk caching, the ROM ABI, or the immutable
C6 EPROM bytes.

## Simulator evidence

The exact C6 ROM with the corrected system passed:

- two independent four-record PIP copies of `README.TXT`;
- CRC16-CCITT `4613`, four records, for both destinations;
- every full-profile strict-8080 utility and explicit warm boot;
- A: write/attribute/erase and physical-layout B: access;
- the HEXCOM, SID, PATCH, and ED development workflow;
- clean, compound-corruption, server-restart, and mid-session-restart runs;
- zero retries in clean runs and successful bounded recovery in injected
  faults;
- C6 manifest binding, reproducible package, runtime-memory, and static
  strict-8080 gates.

Corrected artifact identities are:

| Artifact | SHA-256 |
| --- | --- |
| immutable C6 ROM | `0487d5150f9b662a193b3f031aadd90002ee232477d355d3877a757a247c2f09` |
| post-C6 system | `f3dbd9c8c161a2dd13e562fe3e8824273815f3f0fbbd2f9ef4c4a79aa2217cce` |
| post-C6 V16 stream | `20bc372f890346fe1643ac8a38b01f68251fcf97a8a082416faa27dde70b7e1a` |

## Remaining physical gate

No EPROM burn is needed. Load the corrected system through the already fitted
C6 ROM, then run:

```text
PIP COPY.TXT=README.TXT
CRC COPY.TXT
```

M1 closes when CS00015 returns to `A>` after both commands and reports
`CRC16-CCITT: 4613  records: 0004`.
