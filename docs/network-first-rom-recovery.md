# Network-first ROM recovery qualification

Status: **COMPLETE IN SIMULATION; PHYSICAL QUALIFICATION PENDING**

Date: **2026-08-16**

This checkpoint completes execution-plan step 7 for the network-first ROM.
The tests exercise faults at both bootstrap and resident NetDisk boundaries and
require the real CP/M Plus system to recover without another manual reset once
a valid host is available.

## Automated matrix

| fault | exercised behavior | accepted result |
| --- | --- | --- |
| Host absent at reset | ROM waits and continues overlapping V15 synchronization probes | A later host can attach without resetting Juku |
| Ready byte missed | Host times out of its C4 wait and begins safe synchronization | Bootstrap completes |
| Corrupt bootstrap extension | Target rejects the CRC and accepts a later valid extension | Bootstrap completes |
| Target reset halfway through an extension | A new target instance starts on the same PTY while stale body bytes remain | Stale bytes are discarded; a complete retransmission executes |
| Truncated NetDisk reply | Only half of the first reply is sent | Resident service times out and retries |
| Delayed replies | Every compound-fault reply is held for 50 ms | Resident service remains within its bounded wait contract |
| Duplicate full reply | One valid frame is immediately repeated | Modeled 8251 overruns occur; parser resynchronizes |
| Bad NetDisk CRC | The final CRC byte of a later reply is inverted | Reply is rejected and the request is retried |
| Disk server restart | The first server exits after receiving a request but before replying; a fresh stateless server takes over | The unchanged target retries and completes |
| Live disk reconnect | After `A>` appears, the active server exits on the first `DIR` request and a fresh stateless server takes over | `DIR` and all later commands complete without target reset |
| Duplicate target request | Host sees the same sequence and request again | Cached reply is replayed; resident writes remain idempotent |

Every clean and injected-fault CP/M run must reach `A>`, execute `DIR`, run
`DIAG CPU`, and erase `README.TXT`. The compound run currently records three
host-observed retries and three modeled resident-phase 8251 overruns. The clean
run records zero retries and zero overruns. The extended post-reconnect soak
runs 16 further `DIR` plus `DIAG CPU`/warm-boot pairs and finishes with 271
reads, one synchronous write, no target retry, and no overrun.

## Recovery rules fixed by this milestone

- Bootstrap and disk waits are bounded. Silence does not leave either side in
  a permanent half-session.
- Synchronization searches overlap, so a partial prefix cannot hide the next
  valid prefix.
- CRC failure, short input, extra stale bytes, and USART overrun all return to
  a complete-frame boundary before state is committed.
- A read cache entry is committed only after a checked reply. A write
  invalidates cached data before its first attempt.
- Writes are synchronous and use a stable sequence number across retries. The
  server caches the last complete request/reply pair, so retransmission cannot
  apply the same write twice.
- The host carries no required target identity or volatile session state. A
  newly started disk server can resume service from the next complete request.

The variable-length reply filter used by the tests is a fault-injection hook;
ordinary server operation still emits complete protocol-sized replies.

## Reproduce

From `8080-cosim`:

```sh
python3 tests/janet_disk_server_test.py
sync/network_first_rom_abi_check.sh
```

From this repository:

```sh
make network-rom-cosim-check
make network-rom-soak-check
make check
```

The remaining boundary is physical qualification. The exact bytes are now
packaged and hashed as `network-first-abi1-cs00015-c1`, but remain unpromoted
until the complete CS00015 cold/warm boot, disk, keyboard, display, cursor,
recovery, and repeated-timing matrix passes.
