# Juku CP/M 3 command history

Status: **SIMULATOR-QUALIFIED; OPTIONAL HARDWARE SMOKE PENDING**

The full, development, and museum-demo profiles provide one persistent CCP
command and a small inspector:

```text
A>SHOW A:[SPACE]
A>!!
A>HIST
Juku History 1.0
Last: SHOW A:[SPACE]
Repeat with !!
A>HIST CLEAR
Juku History 1.0
History cleared
```

Recovery, native-recovery, and C6-recovery media retain the exact unmodified
Digital Research `CCP.COM`; they do not contain `HIST.COM`.

## Reproducible source boundary

`tools/build_cpm3_history_ccp.py` extracts `CCP3.ASM`, `CCPDATE.ASM`,
`LOADER3.ASM`, MAC, RMAC, and DRLINK from the pinned CP/M 3 source archive. It
first reproduces the published 3,200-byte CCP byte-for-byte at SHA-256
`f1837073d217075223d17dd81d068481819665273b59fbb3502c2f9068e8a671`.
Only after that proof does it apply `patches/ccp3-history.patch` and produce
the 3,379-byte derivative at SHA-256
`e27c1fcc2b185eaac395069b0e77575a026cff9d87130cd9bd117711746eedb7`.
The generated manifest records the source, patch, result, license, runtime
end, and reserved state range. The CP/M distribution grant in
`third_party/cpm3/LICENSE.md` permits this derivative.

The separate project-owned `HIST.COM` is assembled from `src/history.asm`, is
286 bytes at SHA-256
`3f3754e41bb7a501fdb6a8951a108287409a8efb6b03360de1ba0bf6d960faf2`,
and uses the repository BSD-2-Clause license. This implementation is not the
source-less z80pack HIST RSX investigated earlier; that external binary
remains rejected.

## Memory and behavior contract

The state is 79 bytes at `D571h..D5BFh`: two magic bytes, one length byte, and
up to 76 command bytes. The current post-C6 adapter ends at `D570h`; the ROM
self-test stack/guard begins at `D5C0h`. The CCP derivative ends at `0E33h`,
well below `1000h`, and the ordinary TPA remains `0100h..99FFh`.

The CCP saves a nonblank command no longer than 76 characters. A line
containing only spaces, an overlong line, and `HIST` itself do not replace the
useful entry. Two exclamation marks expand to the retained command without
changing it. `HIST` validates both magic bytes and the bounded length before
reading the state; `HIST C` and `HIST CLEAR` erase it.

## Admission evidence

`make history-check` proves the unmodified rebuild, deterministic derivative,
strict-8080 `HIST.COM`, exact identities, memory boundary, profile contents,
and untouched recovery CCPs. `make history-cosim-check` uses the exact C6 ROM,
current native system, and V16 Fastboot to:

- execute large DRI `SHOW`, forcing a CCP reload before inspecting history;
- repeat `SHOW` with the two-character token;
- retain the command across a spaces-only line and a 77-character line;
- inspect, clear, and confirm empty state;
- exercise warm boot and the ordinary disk/write regression with zero USART
  overruns or NetDisk retries;
- record 2--6 bytes of stack use for every `HIST.COM` path while the fetched
  opcode gate reports no Z80 or undocumented-8080 instruction.

That workload exposed two simulator instrumentation races: the host-visible
prompt byte can precede the final BDOS return, and a top-level `JMP 0005h` can
return either through page zero or into a still-resident CCP. The harness now
polls the frozen CPU state, while 8080-cosim commits `353ac1ad` and `fe5beb8c`
model both tail-exit forms. These are observability fixes; target behavior was
unchanged.
