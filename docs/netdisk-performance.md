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
- A later larger cache must have independent per-drive validity and must not
  overlap C640h..C95Fh native state or the C780h..C909h resident cache.

Per-drive cache expansion and MULTIO-aware coalescing remain candidates for a
later ROM-ABI revision, but only initial-login or alternating-drive evidence
can justify their extra resident RAM/code. Steady-state `DIR` and short
sequential reads do not.
