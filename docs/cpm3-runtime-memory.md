# CP/M 3 shipped-utility runtime memory

Status: **COMPLETE; DISK AND LIVE STACK COSTS ADMISSION-GATED**

Every shipped Digital Research executable is exercised on the C6
network-first ROM and native CP/M 3 BIOS, not only on the retained
RomBios compatibility path. Each useful workload must return to CCP,
freeze its own command-scoped stack measurement, pass strict Intel
8080 fetched-opcode checks, and retain the ordinary warm-boot test.

The transient area is `0100h..99FFh` (39,168 bytes). The initial CCP stack at `9CFEh` is in the loader workspace above the TPA and is recorded for attribution, not charged to a program's TPA footprint.

The measured platform is bound by SHA-256 to the exact C6 ROM, extended native system, and V16 Fastboot artifacts; a matching memory map alone is not accepted as C6 evidence.

| Program | Profile and workload | Disk bytes / allocated | Loaded transient / resident | Observed stack | Runtime top / TPA left |
| --- | --- | ---: | ---: | ---: | ---: |
| `DATE.COM` | full: `DATE BAD` | 3,247 / 4,096 B | 3,247 B / none | `0D2Ch`→`0D22h`, 10 B | `0DAFh` / 35,921 B |
| `SETDEF.COM` | full: `SETDEF` | 4,244 / 6,144 B | 4,244 B / none | `1170h`→`1168h`, 8 B | `1194h` / 34,924 B |
| `DEVICE.COM` | full: `DEVICE NAMES` | 7,268 / 8,192 B | 7,268 B / none | `1C43h`→`1C39h`, 10 B | `1D64h` / 31,900 B |
| `HEXCOM.COM` | dev: `HEXCOM HELLO` | 1,131 / 2,048 B | 1,131 B / none | `05B3h`→`05A5h`, 14 B | `05B3h` / 37,965 B |
| `SHOW.COM` | full: `SHOW A:[SPACE]` | 8,376 / 10,240 B | 8,376 B / none | `1F4Bh`→`1F37h`, 20 B | `21B8h` / 30,792 B |
| `PATCH.COM` | dev: `PATCH SID` | 2,369 / 4,096 B | 2,369 B / none | `0A51h`→`0A47h`, 10 B | `0A51h` / 36,783 B |
| `SUBMIT.COM` | full: `SUBMIT MISSING` | 5,376 / 6,144 B | 3,840 B / 1,088 B RSX | `0EDFh`→`0ED7h`, 8 B | `1000h` / 35,328 B |
| `DUMP.COM` | full: `DUMP PROFILE.SUB` | 960 / 2,048 B | 960 B / none | `04D2h`→`04BEh`, 20 B | `04D2h` / 38,190 B |
| `PIP.COM` | full: `PIP COPY.TXT=PROFILE.SUB` | 8,632 / 10,240 B | 8,632 B / none | `22B7h`→`22A7h`, 16 B | `22B8h` / 30,536 B |
| `ED.COM` | dev: `ED EDTEST.TXT` | 9,254 / 10,240 B | 9,254 B / none | `2249h`→`2237h`, 18 B | `2526h` / 29,914 B |
| `HELP.COM` | full: `HELP DUMP` | 6,967 / 8,192 B | 6,967 B / none | `1A8Bh`→`1A81h`, 10 B | `1C37h` / 32,201 B |
| `SET.COM` | full: `SET COPY.TXT [RO]` | 10,368 / 12,288 B | 8,832 B / 1,090 B RSX | `21A8h`→`219Ah`, 14 B | `2380h` / 30,336 B |
| `SID.COM` | dev: `SID HELLO.COM` | 7,936 / 8,192 B | 7,936 B / none | `0200h`→`01FAh`, 6 B | `2000h` / 31,232 B |

Disk allocation uses the native 2,048-byte Juku allocation block and
is cross-checked against the generated volume report. Runtime top is
the greater of the loaded transient end and the measured private-stack
anchor. GENCOM's separately loaded RSX component is reported rather
than silently double-counted inside the ordinary transient span.

The stack figures are exact for the named useful admission workload;
they are regression baselines, not a claim about every possible input
path. Even the smallest recorded headroom is deliberately much larger
than the observed stack peak, so profile selection does not depend on
a razor-thin measurement.

`make distribution-cosim-check` produces and verifies the full-profile
metrics, including native `DEVICE NAMES`. `make
development-cosim-check` does the same for HEXCOM, SID, PATCH, and ED.
`make utility-catalogue-check` validates the exact 13-program set, TPA
geometry, component accounting, workload map, stack arithmetic,
negative mutations, and this generated report.
