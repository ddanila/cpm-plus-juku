# JukuNet C8 resident-service migration plan

Status: **implemented and simulator-qualified; CS00015 qualification pending**

Decision date: **2026-08-19**

## Goal

JukuNet C8 will turn the remaining shared N4/host transport into a resident
ROM service, replace the placeholder ROM diagnostic vector with bounded real
diagnostics, improve monitorless POST failure reporting, and relink the
non-banked CP/M Plus system so the removed RAM code produces a measured TPA
gain.

C6 remains the physically qualified rollback ROM and C7 remains the exact,
hash-pinned focused raw-key candidate. C8 is a new ABI-minor candidate; neither
older image is regenerated under a new meaning.

## Measured starting point

- TPA is `0100h..99FFh`, 39,168 bytes.
- The loaded post-C6 adapter is a sparse `C000h..D570h` container.
- The ABI 1.2 CP/M image still links the extended N4/host module at `C2C0h`.
  Linked independently, that module is 733 bytes.
- Native CP/M service glue is 364 bytes. CP/M calling conventions and mutable
  policy remain in RAM; host-transport mechanisms are migration candidates.
- The hot-directory implementation is 177 bytes plus mutable cache data. It
  is CP/M-specific and is not a first C8 migration target.
- The resident ROM already owns console/font, keyboard, serial, NetDisk,
  sound, bootstrap and quick POST. That completed migration produced the
  earlier exact 8 KiB TPA gain.

## C8 ROM contract

1. Append one ABI 1.3 host-service dispatch vector. It owns bounded N4 console
   polling/input/output, capability negotiation, time transport, status,
   diagnostic and boot publication, bounded bulk output, reconnect state and
   all wire framing/retry behavior.
2. Keep CP/M-specific TIME commit, BIOS entry conventions, status layout and
   local-console policy in thin RAM wrappers.
3. Expand the existing diagnostic vector with documented, non-destructive
   selectors backed by `juku-common`: CPU, private scratch-RAM data/address/
   retention, resident-ROM integrity, D57 and D11 status, plus retained POST
   state. Destructive whole-machine tests remain separate diagnostic-ROM work.
4. Embed an unambiguous `JukuNet C8` build identity. Build identity remains
   diagnostic, never a compatibility key.
5. On POST failure only, emit a fixed three-tone binary-style code while
   retaining the existing low-RAM status byte and reset memory view:
   C1 short-short-long, C2 short-long-short, C3 short-long-long, C4
   long-short-short, and C5 long-short-long. Short gaps separate tones and a
   clearly longer pause separates repeated series. Successful boot and
   ordinary absent-host retry remain silent.

The single appended vector is deliberate: the copied low-RAM gate has only a
small remaining envelope. A selector dispatcher keeps existing ABI addresses
unchanged and avoids widening the mode-switch helper boundary.

## RAM ownership

ROM code and immutable tables move; mutable objects do not. C8 continues to
reserve RAM for the gate/helper, host and NetDisk sequence/status bytes,
keyboard/cursor state, disk caches, DMA, DPH/DPB structures, directory and
allocation vectors, SCB clock, stacks and CP/M status records.

The host-service implementation uses 27 bytes at `D7E0h..D7FAh` inside the
existing `D780h..D7FFh` ROM workspace. It does not consume the framebuffer,
the `D600h..D6FFh` boot/gate area, or the `D700h..D77Fh` mode-3 helper.

## Measured acceptance gates

1. Rebuild C4, C5, C6 and C7 byte-identically before accepting any C8 image.
2. Prove every new host selector, register/stack/memory-mode postcondition,
   timeout, malformed request and host-loss/reconnect path in cosimulation.
3. Prove all diagnostic selectors and all five audible POST failure codes.
4. Boot the real CP/M Plus system through C8 and repeat local and N4 console,
   A:/B:, TIME, STATUS, DIAG, bulk output, writes, warm boot, missed-ready,
   corrupt reply and server-replacement tests.
5. Remove the 733-byte RAM host implementation, relink the high-memory chain,
   and report the resulting initialized bytes, fixed/mutable objects and exact
   TPA. The minimum acceptance target is a 512-byte TPA increase. A 768-byte
   increase is pursued only if the layout permits it without weakening cache,
   recovery or stack margins.
6. Produce deterministic combined/D15/D16 images, hashes, manifest, memory
   map and a focused physical workload. C8 remains a simulator candidate until
   that workload passes on CS00015.

## Explicit non-goals

- no baud rate above the proven 19,200 setting;
- no write-back cache, compression experiment or new NetDisk protocol;
- no banking claim;
- no movement of mutable disk/cache structures into ROM;
- no relocation of BDOS, CCP or CP/M-specific policy into a Juku platform ABI;
- no destructive diagnostics during a live CP/M session.

## Implemented result

Implementation completed on 2026-08-20:

- ABI 1.3 appends the selector-driven `JROMHOST`/`JCGHOST` vector at
  `FF5Ch`/`D65Ch`. The resident module owns N4 framing, bounded polling,
  capability and time replies, status/diagnostic/boot publication, bulk
  output, host-loss recovery and reconnect counters.
- The old 733-byte RAM transport is replaced by a 147-byte CP/M binding at
  `C4C0h`. The binding retains CP/M TIME/SCB commit and register conventions.
- CP/M-specific native services and hot-directory policy remain in RAM. The
  adapter's fixed disk/cache/status objects are unchanged.
- GENCPM now places BDOS at `9F00h`, the SCB at `BD9Ch`, BIOS at `BE00h`, and
  the thin adapter at `C200h`. The loader moves to `9C00h`; exact TPA is
  `0100h..9BFFh`, 39,680 bytes. This is the planned 512-byte gain over C6/C7.
- Diagnostic selectors 1 through 8 cover CPU, scratch-RAM data/address and
  retention, complete resident-ROM checksum, D57, D11 and retained POST.
- POST failures repeat the documented three-tone code. Simulator tests inject
  every C1--C5 class and distinguish short/long timing from traced D57 writes.
- C4, C5, C6 and C7 stay byte-identical. C8 has deterministic combined,
  D15/D16 and metadata artifacts plus a CP/M system, Fastboot v16 stage and
  boot manifest.
- The end-to-end C8 checks boot after a missed one-shot readiness marker, reach
  `A>`, run `DIR`, `VER`, `STATUS`, ROM-backed `DIAG CPU`, warm boot, and then
  verify the warm marker. A separate N4 run reaches the same prompt and runs
  `DIR` and `VER` entirely through the resident remote console.

One simulator-found defect was fixed before qualification: the first selector
implementation decoded C through A and thereby destroyed A-carried payloads.
This made capability reads succeed but disabled N4 when the feature byte was
applied. The ABI self-test now explicitly proves payload preservation before
the complete CP/M/N4 regression.

The only promotion blocker is physical qualification on CS00015. C6 remains
the rollback image until C8 passes the focused cold-boot, local/N4, disk,
diagnostic, POST-audio and warm-boot bench workload.
