# Future runtime console switching

Status: **PROPOSAL RECORDED; NO IMPLEMENTATION AUTHORIZED**

S21 defines the console configuration applied at cold reset. A future CP/M Plus
utility may override that configuration for the current powered session without
changing the switches or rebooting the machine. The intended interface is:

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

The current diagnostic comparison between S21-derived video mode and the active
status field must be revised before runtime switching is enabled. Until then,
the comparison remains useful for the current fixed-at-reset implementation.

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

The preferred implementation is an appended ABI service in a future C10 or
later ROM that owns active mode and character-bank transitions and publishes
the expanded status. C9 is fixed as the bounded-host ABI 1.4 candidate and
does not include this feature. A carefully specified loaded-system override is
acceptable only if it can preserve the same atomicity and compatibility. This
proposal is not sufficient reason by itself to produce another ROM; it should
accompany a measured improvement that justifies a new candidate and its
qualification work.
