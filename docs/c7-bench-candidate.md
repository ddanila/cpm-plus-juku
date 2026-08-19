# JukuNet C7 focused bench candidate

Status: **SIMULATOR-QUALIFIED; FOCUSED CS00015 RAW-KEY RUN PENDING**

C7 is deliberately small. It retains the C6 ABI 1.2 vectors, automatic
network boot, Fastboot V16, CP/M system, NetDisk v3, recovery media, and
fallback. It changes only the raw keyboard scan order so an ordinary matrix
contact wins over the global Shift/Ctrl lines, and carries the already
admitted VC-compatible CP437 box glyphs. C6 remains immutable.

## Programmer identities

| artifact | label | SHA-256 |
|---|---|---|
| combined ROM | `JukuNet C7` | `a05c74d948d9f01c5a89dc3ea69bfeb4fdf9ac48b3e37845d1edbf03e6e203b8` |
| D15 low, 8,192 bytes | `JukuNet C7 Low` | `8a1db7dcd0bdf6403bcd64ac7a7f12b278ae0c70778508ddbe90d4cc50e3f413` |
| D16 high, 8,192 bytes | `JukuNet C7 High` | `5512b75f1550ec4c305b721ad0ee179556c938780a197b3bed1001366c7e4b94` |

Program D15 and D16 with the two named half-images in
`out/cpm-plus-3.1-juku-c7-modified-raw-bench/`. Use the Willem's normal single
built-in read/verify only; no additional reread is required. Concatenating
D15 then D16 must reproduce the combined hash above.

Build all bound inputs and the deterministic archive with:

```sh
cd ~/fun/cpm-plus-juku && make c7-bench-candidate
```

The generated `manifest.json` binds every packaged byte. The boot manifest is
`out/cpm-plus-juku-c7-manifest.json`; it names `c7-native` and cannot be
mistaken for the immutable C6 artifact set.

## Evidence already complete

- deterministic C7 rebuild and unchanged production hash;
- immutable C5 and C6 hashes;
- complete ABI 1.2, V16 bootstrap, HDL, console, cursor, sound, and NetDisk
  regression gates inherited from C6;
- exact executable Shift+F8 fixture: column `0Eh`, PB `8Eh`;
- exact executable Ctrl+Up/Home fixture: column `0Ah`, PB `6Ah`;
- reproducible programmer/CP/M/media archive and manifest checks.

## Focused physical acceptance

Set S21 to logical `00000011` (`03h`), start the following command before
powering CS00015, and follow its three prompts:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py run /dev/ttyUSB0 --profile c7-raw --manifest out/cpm-plus-juku-c7-manifest.json --output out/physical-CS00015-c7-raw
```

The runner supplies all CP/M commands over N4. The operator only performs the
physical Shift+F8 and Ctrl+Up/Home chords and presses Esc when requested. A
pass requires CPU and USART diagnostics, both exact raw-key reports, Keyraw's
clean exit, warm boot, complete target/host logs, and a clean server shutdown.
Re-audit the retained record with:

```sh
cd ~/fun/cpm-plus-juku && python3 tools/physical_acceptance.py audit out/physical-CS00015-c7-raw
```

Until that audit passes, label C7 as a bench candidate rather than a
physically qualified replacement for C6.
