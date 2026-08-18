# CP/M Plus and network-first ROM completion audit

Audit date: **2026-08-18**

Scope: every requirement in [`cpm-plus-feature-plan.md`](cpm-plus-feature-plan.md)
and [`network-first-rom-plan.md`](network-first-rom-plan.md). The audited
deliverable is the ABI 1.2 C6 simulator release. The later blind physical
qualification is recorded separately and never substitutes for unavailable
display observations.

The fail-closed top-level command is:

```sh
make c6-release-candidate
```

It must finish without a skipped command. `make check` remains the broader C4/
C5/source/distribution compatibility gate and is also run before publication.

## Network-first execution plan

| step | requirement | authoritative evidence | result |
| ---: | --- | --- | --- |
| 1 | Freeze stock/RAM-BIOS reference and reproducible artifacts | `verify-prebuilt`, C4 package checks, C5 pinned ROM/system hashes, `tests/c5_boot_manifest_test.py` | Complete; C6 rebuild proves C5 ROM and system byte identity. |
| 2 | Native compact console in RAM, exact fonts, cursor, four modes | `creep_console_oracle.py`, `tests/console_font_test.py`, `tests/cosim_check.py`, four 9,600-byte framebuffer comparisons | Complete; local output is the behavioral oracle for ROM. |
| 3 | 6 KiB/10 KiB inventory and call/size budget | `tools/rom_budget.py --check`, generated ROM metadata | Complete; both windows and copied-helper/gate sizes fail closed. |
| 4 | Fixed versioned ABI and safe call gate | `juku-common/platform/ROM-ABI.md`, `sync/network_first_rom_abi_check.sh`, `tests/network_first_rom_{abi,locale,extended}_test.py` | Complete through ABI 1.2; full fixed vector map, register/stack/DI/PIC/memory-mode/overlay checks pass. |
| 5 | Automatic 19,200-baud keyless boot, quick POST, identity-free host | `tests/network_first_rom_boot_test.py`, real C6 CP/M cosimulation, generated stage dictionary | Complete; valid host reaches `A>` and missed/absent/corrupt host paths retry without a required reset. |
| 6 | Move common services and prove TPA gain | C6 ROM test, extended CP/M local/N4 tests, `memory-map.json` | Complete; serial, keyboard, console/font, NetDisk, sound, and diagnostics are resident; TPA remains 39,168 bytes, +8,192. |
| 7 | Recovery and long soak | network compound/restart fixtures and `network-rom-long-soak-check` | Complete; real firmware branches cover truncation, delay, duplicate, CRC, overrun, stale bytes, server replacement, and 64 read/diagnostic/write cycles. |
| 8 | Qualify production artifacts without hardware blocking | exact C6 C-model run plus C4 structural HDL boundary | Complete for simulator release; the exact C6 pair later passed the CS00015 blind hardware matrix. |
| 9 | Promote only after parity | C6 package status, C5/C4 fallback slots, local and N4 parity tests, `cs00015-c6-blind-qualification-20260818.md` | Blind physical parity passed; only display/cursor observation remains. |

## ROM and boot acceptance contract

| requirement | evidence |
| --- | --- |
| Cold reset reaches CP/M without input at 19,200 | Exact C6 ROM-resident Fastboot V16 loader, compressed system stream, and host reach `A>` in both local and remote-console runs. No executable loader is downloaded. |
| Quick bounded POST with distinct failures | Boot test exercises CPU, RAM data/address, whole-ROM, PIT, and USART failure paths and measures target-ready timing. |
| Missing host recovers later without RESET | The delayed-host fixture discards both one-shot C7/JR16 indications, then the production JZ exchange resynchronizes and completes; absent/restarted C4 fixtures remain compatibility evidence. |
| ABI/mode/PIC/USART/stack contracts | Executable ABI checks assert fixed addresses, mode 1 return, copied mode-3 helper, masked PIC, DI, register and stack sentinels. |
| Console, keyboard, cursor coexist | Four exact framebuffer modes plus translated/remapped/raw key and complete cursor-phase fixtures pass; extended CP/M also runs with N4 absent. |
| DIR, sequential read, DIAG, warm boot, reconnect | Local and N4 C6 runs execute the full command matrix; long soak replaces the host mid-session. |
| Original failure fixtures remain meaningful | Legacy drain/PIC/host-guard and compound serial faults still fail or recover for their original modeled cause, without synthetic CP/M errors. |
| Programmer images and maps are reproducible | C6 release test concatenates D15+D16, checks every hash and manifest record, and builds two byte-identical tar archives. |
| 39,168-byte TPA retained | Live page-zero loader/BDOS vectors and generated RAM map assert `0100h..99FFh`; adapter ends at `CB6Bh`. |

## CP/M Plus feature priorities

| priority | requirement set | authoritative evidence | result |
| ---: | --- | --- | --- |
| 0 | Immutable reference and recoverable baseline | C4/C5 packages, prebuilt comparisons, C4 fallback system slot | Complete. |
| 1 | Licensed reproducible recovery/full/demo A: and native B: | profile manifests, provenance hashes, free-space reports, distribution negative tests and B: cosim | Complete; C6 adds a separately named recovery/test A:. |
| 2 | Native character table, TIME, MULTIO, FLUSH, MOVE, USERF | `tests/native_services_test.py`, `NATIVE.COM`, exact status transcript, production cosim | Complete; bank calls remain truthful stubs because hardware is non-banked. |
| 3 | S21, video modes, locales, pseudographics, remap, console block | locale/source oracles, ABI C5/C6 fixtures, `KEYTEST`, `KEYRAW`, operation 28h | Complete; connected UI cells use five edge pixels and local I/O remains authoritative. |
| 4 | Shared safe diagnostics and observability | Diag 0.5, Status 1.3, retained D610h..D613h record, operations 24h/25h/27h, generated memory map | Complete; destructive live-CP/M tests are explicitly rejected. |
| 5 | Measured NetDisk performance and safe media | pinned 10/0/1 request counts, per-drive cache fixture, capability operation 26h, multi-request fixture, copy/snapshot/read-only tests, long write/reconnect soak | Complete for selected synchronous design. |
| 6 | Manifest, identity-free media, fallback slots and recovery | C6 boot manifest, last-known-good tests, C4 fallback, reproducible package | Complete. |

## Distribution and provenance requirements

- The recovery, native recovery, C6 recovery, full, museum-demo, and native B:
  profiles are declarative and byte reproducible.
- Each distributed third-party binary has a pinned source/license/version/hash;
  the mixed-license Juku 3000 game disks remain external recorded inputs rather
  than being silently redistributed.
- The normal full image has no autorun. The museum profile alone adds the
  opt-in `PROFILE.SUB`, and its cosimulation waits for the second CCP prompt.
- A: defaults read-only and supports explicit writable copy or atomic sparse
  snapshot. B: is read-only. Writes in the target remain synchronous.

## Explicit decisions, not missing work

These plan clauses were evaluations or guarded conditionals. Their recorded
disposition is part of completion:

- **Write-back cache:** rejected for this release. Measured read gains do not
  justify new flush, disconnect, and power-loss risk; FLUSH truthfully succeeds
  because no dirty target data exists.
- **Second directory cache:** rejected. The first interactive recovery `DIR`
  already costs zero disk turns after BDOS login state is populated.
- **Replace predictor with MULTIO bulk DMA:** deferred after measurement. The
  existing eight-record predictor yields 10/0/1 boot/DIR/TYPE turns. ABI 1.2
  nevertheless supplies the bounded ordered primitive for a future workload.
- **Cryptographic authentication:** deliberately out of C6. Whole-image hashes,
  CRC/Fletcher guards, manifest validation, and reproducible identity are
  mandatory; cryptography requires a separately measured 8080/EPROM/wire design.
- **Baud above 19,200:** experimental only. Mode-2/count-4 19,200 remains the
  production setting proven on hardware and in the timing model.
- **Banked CP/M Plus:** not claimed. The port is strict-8080, non-banked, and
  exposes truthful bank-selection stubs until real banked hardware exists.
- **Mandatory ROM menu/local disk boot:** intentionally absent. Network boot is
  the product; S21 bit 0 provides the concealed recovery wait.
- **Full HDL CP/M execution:** not duplicated. The exact C4 structural HDL gate
  covers the valuable hardware boundary; full firmware, cursor pixels,
  recovery, and soak use the cycle/device C model.

## Fleet boundary

Machine profiles in `8080-cosim/docs/machines/` prevent one board's fault from
becoming a global software assumption:

- CS00014: museum exhibition machine, stock ROM;
- CS00015: home reference, exact C6 pair fitted; blind C6 matrix passed;
- CS00000: USART suspicion remains board-local and unproven;
- CS00024: RAM/D57/raster/parser investigation remains board-local.

None of those open service items weakens the scoped C6 simulator result.

## Final release evidence

The checked package is `out/cpm-plus-3.1-juku-c6-simulator/` with matching
`.tar` and `.tar.sha256`. Its `manifest.json` is the publication authority;
`cpm-plus-juku-c6-manifest.json` binds boot/media inputs and
`memory-map.json` binds the full ROM vector and RAM placement. If any input is
rebuilt, all three must be regenerated and the complete release command must
pass again.
