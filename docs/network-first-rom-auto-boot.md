# Network-first ROM automatic-boot checkpoint

Status: **SIMULATOR-QUALIFIED DESK MILESTONE; NOT A PROGRAMMING RELEASE**

Date: **2026-08-16**

This checkpoint completes execution-plan step 5: the from-scratch 16 KiB ROM
resets the modeled Juku, performs bounded POST, announces a direct 19,200-baud
session, loads the real CP/M Plus system without a keypress or Janet identity,
and reaches the existing NetDisk-v3 baseline. The dedicated consumer stays in
mode 1 for resident serial, keyboard, console, and NetDisk-read calls. Its CP/M
system is now regenerated for the compact map and exposes an exact 39,168-byte
(38.25 KiB) transient span, 8 KiB larger than the frozen RAM-BIOS baseline.

## Reset and transfer path

1. Reset enters ROM mode 0 with interrupts disabled and a private stack at
   `D5F0h`. It configures D27 all-input, D26 mode `82h` plus PC7-high BSR,
   initializes the stock D54/D55/D57 raster/refresh chain, and initializes the
   8259 with original `D6h/FEh` MCS-80 vectors before masking every source.
2. POST exercises the shared 8080 CPU diagnostic, restored scratch RAM at
   `D400h..D4FFh`, address lines A0..A11 from `C000h`, the additive checksum of
   the complete 16 KiB ROM, D57 channel-0 count latch/readback in the valid
   live mode-2 range `1..4`, and D11 idle transmitter status.
3. Success stores `00h` at `D610h`. Failures store `C1h` CPU, `C2h` RAM data,
   `C3h` RAM address, `C4h` complete ROM, or `C5h` PIT/USART and halt safely in
   mode 0.
4. The ROM copies the fixed ABI gate to `D620h`, framebuffer helper to `D700h`,
   and a 141-byte V15 core to `0100h`. The `D600h` transition selects mode 1
   and jumps to the core.
5. The core establishes D57 mode 2/count 4 and D11 19,200/8N1, transmits C4 as
   a target-ready byte, accepts the checked 267-byte extension, and transfers
   the ZX0-compressed CP/M Plus image.
6. The dedicated ROM-ABI consumer validates the resident manifest, calls
   `JCGINIT`, selects 19,200/8O1 through `JCGSERINIT`, initializes the shared
   resident keyboard, 80x24 console, and versioned NetDisk-v3 read-ahead and
   synchronous write-through service.

The POST status `C4h` and wire-ready byte `C4h` are intentionally on different
channels: a ROM-integrity failure only writes RAM and halts, while a successful
target transmits C4 after serial initialization.

## Host recovery contract

`--network-rom` implies direct V15 and skips stock Janet discovery completely.
The normal host waits briefly for target-ready C4, preventing speculative
prefix traffic during reset and POST. C4 is not a permanent dependency: a
server started after that byte was lost, or restarted during an incomplete
header search, falls back after three seconds to the V15 parser's overlapping
`A5 3A` synchronization probes. Missing the announcement therefore does not
require a Juku RESET. Reset during an extension body is now covered by the
complete recovery matrix: the restarted target discards stale bytes already
present on the same serial link and accepts a later complete retransmission.
Resident disk-server restart and malformed-reply coverage are recorded in
[`network-first-rom-recovery.md`](network-first-rom-recovery.md).

No client/server station arguments are needed. The direct path retains neutral
station values only for report-schema compatibility; they are not placed on
the wire and do not select the machine.

## Reproducible evidence

From `8080-cosim`:

```sh
python3 spinoffs/jukuravi/network-rom/build_network_rom.py
sync/network_first_rom_abi_check.sh
sync/janet_netboot_check.sh
```

From this repository:

```sh
make network-rom-cosim-check
```

The accepted output is:

```text
NETWORK-FIRST-ROM-BOOT-TEST: PASS ...
  POST C1/C2/C3/C4/C5; ready=725602 cycles;
  absent host; corrupt recovery; keyless 19200 handoff
JUKU CP/M PLUS 3.1: PASS
  automatic network ROM boot, A>, DIR, TYPE README.TXT, DIAG CPU,
  warm boot, ERA README.TXT, reads=53, writes=1, retries=0, resident-overruns=0,
  bootstrap-overruns=0
```

The ABI check injects a shifted physical `T` through D26 ports 4/5, then proves
an exact 9,600-byte `Z` plus underline frame through the 119-byte helper. The
CP/M check asserts that the copied gate reports ready at `D620h`, status at
`C5F1h` is zero,
`D785h` records 8O1, and the complete `DIR`, paginated `TYPE README.TXT`,
`DIAG CPU`, `WBOOT`, and erase sequence is consumed by resident code while
mode 1 remains selected. Its complete
framebuffer matches the RAM-console run byte for byte. The normal system remains
byte-identical. Packing the binding and remote console shrinks initialized
adapter RAM from 4,080 to 912 bytes. The test additionally checks the live
page-zero chain through loader `9A06h` to BDOS `9D06h`, proving an exact
8,192-byte TPA gain over the frozen `7A06h`/`7D06h` chain.

At CS00015's measured 1.70 MHz, 725,602 cycles are approximately 427 ms from
reset to target-ready C4. Failure paths are separately bounded below 1.5
million cycles. The tests inject a changed CPU vector, stuck RAM bit, address
alias, complete-ROM bit flip, D57 readback fault, and D11 readiness fault. They
also leave the target without a host, send a corrupted extension before a
valid one, verify missed-C4 host recovery, and exercise the real CP/M prompt,
directory, transient loader, and diagnostic program. The checkpoint also pins
the PPI modes, PC7-preserving mode transition, PIC vectors/mask, and every
stock raster/refresh timer write used during the network load.

Current deterministic candidate hashes are recorded by
`8080-cosim/spinoffs/jukuravi/network-rom/juku-network-rom-abi1.json`. The JSON
names `network-first-abi1-cs00015-c2` and records `physical qualification
pending`; it is the authoritative controlled-bench release gate. The complete
package and burn mapping are in
[`network-first-rom-bench-candidate.md`](network-first-rom-bench-candidate.md).

## Host command for C2 qualification

For the named C2 D15/D16 pair, the matching identity-free command is:

```sh
cd ~/fun/cpm-plus-juku && ../8080-cosim/tools/janet_disk_server.py \
  /dev/ttyUSB0 out/cpm-plus-juku-network-rom-system.bin \
  out/cpm-plus-juku.img \
  --fast-stage1 out/cpm-plus-juku-network-rom-fastboot-v15.bin --network-rom \
  --disk-baud 19200 --disk-protocol 3 --writable --timeout 86400
```

C2 is ready for a controlled CS00015 burn but is not promoted. Automatic boot,
resident read-ahead and write-through, CP/M SYS regeneration, the measured TPA
gain, and simulated recovery qualification are complete. The next milestone
is the physical matrix documented in the candidate record.
