# C12 runtime console switching

Status: **IMPLEMENTED AND LOCAL/REMOTE CO-SIM QUALIFIED; PHYSICAL ACCEPTANCE PENDING**

S21 defines the console configuration applied at cold reset. C12 ABI 1.5 and
`CONSOLE.COM` can override that configuration for the current powered session
without changing the switches or rebooting the machine. The interface is:

```text
CONSOLE STATUS
CONSOLE MODE 40|53|64|80
CONSOLE CHARSET ENGLISH|ESTONIAN|RUSSIAN|USER
CONSOLE DEFAULT
```

`CONSOLE DEFAULT` reapplies the reset-latched S21 video and character-bank
settings. A warm boot should preserve an explicit runtime override; reset or
power cycling returns to the S21 defaults.

## State and diagnostics

The observable console state must distinguish these values instead of treating
them as interchangeable:

- raw reset-latched S21;
- the video mode and character bank decoded from S21;
- the active video mode and character bank;
- whether either active value is overridden.

`CONSOLE STATUS` and `STATUS` should report both the boot defaults and active
values. A difference is valid and must not itself be diagnosed as a fault.

In particular, future diagnostics must obey these rules:

- `DIAG KEY` verifies that S21 can be read and decodes to supported defaults;
- `DIAG VIDEO` verifies the active geometry, timing, renderer, and published
  active state;
- `DIAG ALL` passes when a deliberate runtime override differs from S21;
- `CONSOLE DEFAULT` clears the override and makes the active state match S21.

`STATUS.COM` 1.6 reports the S21 default, active mode/bank, and independent
override flags. `DIAG.COM` 0.8 validates the active tuple and POF state without
requiring it to equal S21. Local and N4 co-simulation switch 80x24/Estonian to
40x24/Russian, pass `DIAG VIDEO`, preserve that pair across `WBOOT`, and restore
the exact S21 default with `CONSOLE DEFAULT`.

## Transition requirements

A mode change must be atomic from the perspective of console writers: suspend
local and N4 console output, hide the cursor, program the timing and geometry,
clear or safely redraw the framebuffer, reset cursor and blink state, publish
the new active state, and resume output. Clearing the screen is preferable to
retaining bytes whose layout has a different row width.

A character-bank change must switch the display font and matching keyboard
translation together. It should clear or redraw the display so existing cells
do not retain glyphs from the previous bank, then publish the active bank.

Failures must leave either the complete old state or the complete requested
state; partially changed timing, geometry, font, or keyboard mappings are not
acceptable.

## ROM ABI boundary

C8 is immutable and its ABI 1.3 does not expose a stable setter for the resident
console configuration. Its console initialization reads the reset configuration
again, so this feature must not be presented as an already available CP/M-only
change.

The implemented service is feature bit `1000h`, ROM vector `FF5Fh`, and low-RAM
gate entry `D65Fh`. Selector 0 queries; selector 1 sets B=mode/C=bank; selector
2 restores the default. Invalid selectors or values return A=`FFh`/carry set
without state or pixel changes. The active byte and flags use `D7FDh..D7FEh`,
after the resident-host state; the fixed workspace and TPA do not grow.

C9, C10, and C11 remain immutable. The C12 package is deliberately marked
`physical_programming_authorized: false` until the attended CS00000 switch,
raster, keyboard-translation, warm-boot, default-restore, and recovery matrix
passes.
