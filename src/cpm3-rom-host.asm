; Thin CP/M Plus bindings for JukuNet ABI 1.3 resident host services.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.
;
; The N4 framing, timeout, retry, capability, clock and bulk implementation
; lives in the C8 ROM. This module preserves the established BIOS-facing
; entry contracts and performs the one CP/M-specific operation which does
; not belong in firmware: committing a successful clock reply to the SCB.

        include "rom-abi.inc"

SCBDATE        equ     0bdf4h

        cseg
        public  NCENA
        public  NCSTAT
        public  NCIN
        public  NCOUT
        public  NCTIME
        public  NCPUBLISH
        public  NCDIAG
        public  NCBOOT
        public  NCCAPS
        public  NCCFG
        public  NCBULK
        public  NCHOSTSTATE

NCENA: push    b
        mvi     c,JROMHOSTENABLE
        call    JCGHOSTADDR
        pop     b
        ret

; A is the explicit host feature byte returned by NCCAPS.
NCCFG: push    b
        mvi     c,JROMHOSTCONFIG
        call    JCGHOSTADDR
        pop     b
        ret

NCSTAT:
        push    b
        mvi     c,JROMHOSTSTAT
        call    JCGHOSTADDR
        pop     b
        ret

NCIN:  push    b
        mvi     c,JROMHOSTIN
        call    JCGHOSTADDR
        pop     b
        ret

; Preserve all caller-visible registers, matching the old RAM transport.
NCOUT: push    psw
        push    b
        push    d
        push    h
        mvi     c,JROMHOSTOUT
        call    JCGHOSTADDR
        pop     h
        pop     d
        pop     b
        pop     psw
        ret

; CP/M 3 TIME: C=00h fetches the host clock, C=FFh publishes the current
; date/time. The ROM returns a pointer to five bytes for GET. Preserve HL
; and DE exactly as required by the CP/M 3 System Guide.
NCTIME:
        push    h
        push    d
        mov     a,c
        ora     a
        jz      NCTIMEGET
        inr     a
        jnz     NCTIMEFAIL
        lxi     h,SCBDATE
        mvi     c,JROMHOSTTIMESET
        call    JCGHOSTADDR
        jmp     NCTIMERET
NCTIMEGET:
        mvi     c,JROMHOSTTIMEGET
        call    JCGHOSTADDR
        ora     a
        jnz     NCTIMEFAIL
        lxi     d,SCBDATE
        mvi     b,5
NCTIMECOPY:
        mov     a,m
        stax    d
        inx     h
        inx     d
        dcr     b
        jnz     NCTIMECOPY
        xra     a
        jmp     NCTIMERET
NCTIMEFAIL:
        mvi     a,1
NCTIMERET:
        pop     d
        pop     h
        ret

NCPUBLISH:
        push    b
        mvi     c,JROMHOSTSTATUS
        jmp     NCPUBLISH1
NCDIAG:
        push    b
        mvi     c,JROMHOSTDIAG
        jmp     NCPUBLISH1
NCBOOT:
        push    b
        mvi     c,JROMHOSTBOOT
NCPUBLISH1:
        push    psw
        push    d
        push    h
        call    JCGHOSTADDR
        pop     h
        pop     d
        pop     psw
        pop     b
        ret

NCCAPS:
        mvi     c,JROMHOSTCAPS
        jmp     JCGHOSTADDR

NCBULK:
        push    b
        push    d
        push    h
        mvi     c,JROMHOSTBULK
        call    JCGHOSTADDR
        pop     h
        pop     d
        pop     b
        ret

; Return HL -> {last failure, saturated reconnect count}.
NCHOSTSTATE:
        mvi     c,JROMHOSTSTATE
        jmp     JCGHOSTADDR

        end
