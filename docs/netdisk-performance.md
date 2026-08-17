# NetDisk-v3 performance baseline

The native CP/M Plus cosimulation records per-command accepted read requests,
records delivered, request/reply wire bytes, and paced wall time. It uses the
production 19,200-baud 8O1 NetDisk-v3 path with three-record read-ahead and the
real framebuffer renderer. `make native-services-check` pins the request
counts so an optimization cannot silently become a regression.

## Recovery A: baseline

The minimal native recovery image currently measures:

| Phase | Read requests | Records | Request bytes | Reply bytes | Paced elapsed |
| --- | ---: | ---: | ---: | ---: | ---: |
| reset through first `A>` | 22 | 66 | 207 | 4,309 | 9.78 s |
| first interactive `DIR` | 0 | 0 | 0 | 0 | 3.34 s |
| `TYPE README.TXT` | 2 | 6 | 18 | 546 | 20.48 s |

The `DIR` result is decisive: CP/M's login scan has already populated the BDOS
directory state, so a second protocol-level directory cache would save no wire
turns for this command. The sequential file read is also only two turns. At
19,200/8O1 its 564 measured wire bytes have a roughly 0.32-second serialization
floor; almost all of the 20.48-second command is paging and local framebuffer
output, not disk I/O. Larger disk packets or compression therefore cannot make
this visible workload materially faster.

The useful remaining disk target is initial login (22 turns), followed by
first selection of a second drive. Any later protocol experiment must measure
those phases separately and preserve the zero-turn recovery `DIR` and two-turn
sequential read.

## Full A: and native B: baseline

The separately named full distribution, with the approved native-geometry B:
attached, measures:

| Phase | Read requests | Records | Request bytes | Reply bytes | Paced elapsed |
| --- | ---: | ---: | ---: | ---: | ---: |
| reset through first `A>` | 23 | 69 | 216 | 4,974 | 10.24 s |
| first interactive A:`DIR` | 2 | 6 | 18 | 459 | 4.65 s |
| A:`TYPE README.TXT` | 3 | 9 | 27 | 918 | 21.02 s |
| first `B:` selection/login | 11 | 33 | 99 | 434 | 2.72 s |
| first B:`DIR` after login | 1 | 3 | 9 | not isolated | 3.46 s |

This is the better optimization workload: the richer A: needs two turns after
login, while first B: login needs eleven. Even here, B: login is only 2.72
seconds and the visible sequential-file delay is dominated by output. A future
per-drive cache must demonstrate a useful reduction in the 23/11-turn login
figures, not merely improve an artificial raw-sector loop.

## Explicit console capability result

Before runtime capability negotiation, a disk-only full-distribution session
made 186 rejected N4 polls while trying to discover a remote terminal. They
were bounded and harmless, but mixed console discovery traffic into disk
measurements. Native cold boot now sends operation 26h once and applies its
feature byte. An explicit no-console result disables N4 reprobes; an older host
which rejects the query keeps the legacy bounded behavior, and a host which
advertises console keeps live reconnect.

After this change the recovery `DIR` has exactly zero total request and reply
bytes, not merely zero accepted disk reads. This makes command measurements
clean and removes avoidable half-duplex traffic from ordinary local-console
sessions.

## Safety constraints

- C4 and its ROM/RAM-BIOS artifacts remain byte-identical.
- Writes remain synchronous write-through and invalidate resident read-ahead
  before their first attempt.
- A: defaults to read-only at the host; copy, snapshot, and explicit
  write-through policies remain unchanged.
- B: remains read-only.
- C5/C6 use independent A: (`CB80h..CF97h`) and B: (`CFA0h..D3B7h`) buffers and
  resident validity/pointer metadata. An alias guard preserves safe behavior
  for an older consumer that supplies one shared pointer.

The per-drive slice is now executable rather than speculative: the C5 test
selects and lists B:, loads its diagnostic transient, returns to A:, loads the
A: copy, then validates that both entries remain live. C5 explicitly raises
the bounded reply/cache capacity from three to eight records, while the host
default remains three for C4 and older clients.

The paced C5 comparison is:

| Phase | 3-record baseline | C5 8-record | reply bytes | elapsed |
| --- | ---: | ---: | ---: | ---: |
| recovery-A login | 22 requests / 66 records | 10 / 80 | 4,309 -> 4,072 | 9.78 -> 9.63 s |
| first A:`DIR` | 0 / 0 | 0 / 0 | 0 -> 0 | 3.34 -> 3.19 s |
| A:`TYPE README.TXT` | 2 / 6 | 1 / 8 | 546 -> 549 | 20.48 -> 20.49 s |
| first B: login | 11 / 33 | 4 / 32 | workload-dependent | 2.72 -> 2.72 s |

This is a turnaround/robustness gain, not a visible-speed breakthrough. It
costs no TPA, keeps the wire volume flat for measured phases, and is pinned by
the C5 regression at 10/0/1 boot/`DIR`/`TYPE` requests. CP/M's MULTIO hint
cannot improve these commands further without a new bulk-DMA BIOS contract;
the existing translated predictor already fills the eight-record cache before
the next individual `READ`. Such a protocol is deferred until a real workload
shows benefit beyond these counts.

## C6 bounded operations and soak

ABI 1.2 supplies an ordered list service for 1..8 ordinary ten-byte resident
NetDisk requests. It is not silently substituted into the production BIOS:
the measured eight-record translated predictor already achieves the pinned
10/0/1 boot/`DIR`/`TYPE` request counts without another buffer/copy contract.
The executable C6 fixture rejects zero and oversized lists and executes mixed
valid descriptors through the same single-request implementation, preserving
synchronous write and invalidation semantics. A later workload may adopt it
without another ROM ABI change.

The release soak deliberately replaces the stateless host after `A>`, then
runs 64 cycles of directory activity, safe diagnostics, synchronous write and
erase through the real CP/M/ROM/serial paths. Its server timeout is derived
from the requested cycle count; the earlier fixed 180-second harness limit was
identified as a host-test defect rather than misreported as target disk decay.
The release gate requires every cycle, the reconnect marker, exact diagnostic
count, one write cycle per requested cycle, zero unrecovered retries, and zero
resident USART overruns.
The accepted C6 run records 1,193 read requests, 257 synchronous writes, zero
retries, and zero resident/bootstrap overruns across all 64 cycles.

ABI 1.2 also adds bounded N4 output operation `28h`. This improves unattended
observability, not disk timing. Capability bit `40h` advertises it, the request
contains an explicit 1..32-byte length, duplicate replay cannot duplicate
visible output, and lack of N4 remains a successful best-effort no-op so local
console/disk behavior is unchanged.
