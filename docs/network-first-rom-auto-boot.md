# Network-first ROM automatic-boot checkpoint

Status: **SIMULATOR-QUALIFIED DESK MILESTONE; NOT A PROGRAMMING RELEASE**

Date: **2026-08-16**

This checkpoint completes execution-plan step 5: the from-scratch 16 KiB ROM
resets the modeled Juku, performs bounded POST, announces a direct 19,200-baud
session, loads the real CP/M Plus system without a keypress or Janet identity,
and reaches the existing NetDisk-v3 baseline. It does not yet claim a larger
TPA because CP/M Plus deliberately continues with the proven all-RAM BIOS.

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
6. The loaded system takes all-RAM mode 3 and starts the already-qualified
   19,200/8O1 NetDisk-v3 RAM BIOS.

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
require a Juku RESET. Restart during an extension or compressed-payload body is
still part of the later recovery matrix and is not claimed by this checkpoint.

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
  POST C1/C2/C3/C4/C5; ready=722002 cycles;
  absent host; corrupt recovery; keyless 19200 handoff
JUKU CP/M PLUS 3.1: PASS
  automatic network ROM boot, A>, DIR, DIAG CPU,
  reads=36, retries=0, resident-overruns=0, bootstrap-overruns=0
```

At CS00015's measured 1.70 MHz, 722,002 cycles are approximately 425 ms from
reset to target-ready C4. Failure paths are separately bounded below 1.5
million cycles. The tests inject a changed CPU vector, stuck RAM bit, address
alias, complete-ROM bit flip, D57 readback fault, and D11 readiness fault. They
also leave the target without a host, send a corrupted extension before a
valid one, verify missed-C4 host recovery, and exercise the real CP/M prompt,
directory, transient loader, and diagnostic program. The checkpoint also pins
the PPI modes, PC7-preserving mode transition, PIC vectors/mask, and every
stock raster/refresh timer write used during the network load.

Current deterministic desk artifact hashes are recorded by
`8080-cosim/spinoffs/jukuravi/network-rom/juku-network-rom-abi1.json`. The JSON
status remains `automatic-boot desk image; not for physical programming` and
is the authoritative release prohibition.

## Host command reserved for the physical candidate

After the later D15/D16 release gate is explicitly changed, the matching
identity-free command will be:

```sh
cd ~/fun/cpm-plus-juku && ../8080-cosim/tools/janet_disk_server.py \
  /dev/ttyUSB0 out/cpm-plus-juku-system.bin out/cpm-plus-juku.img \
  --fast-stage1 out/cpm-plus-juku-fastboot-v15.bin --network-rom \
  --disk-baud 19200 --disk-protocol 3 --timeout 86400
```

Do not burn the present split artifacts. The next milestone is resident-service
migration: serial/memory-mode primitives, keyboard, compact console/font, then
NetDisk framing and batching. Each must match its RAM oracle, remove the old
RAM copy, and produce a measured relinked TPA before step 6 is complete.
