; Native CP/M Plus BIOS services for the Juku network-ROM profile.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

        cseg
        public  NSCONOST
        public  NSAUXIST
        public  NSAUXOST
        public  NSDEVTBL
        public  NSDEVINI
        public  NSMULTIO
        public  NSFLUSH
        public  NSMOVE
        public  NSTIME
        public  NSUSERF
        extrn   NCTIME

KEYCOLPORT     equ     004h
KEYROWPORT     equ     005h

; The current aggregate console is one physical CP/M 3 character device:
; local display/keyboard, with optional transparent N4 mirroring. It is not a
; user-selectable raw USART, so it truthfully advertises fixed in/out and no
; configurable baud code.
NSDEVTBL:
        lxi     h,NSCHRTBL
        ret

NSDEVINI:
        mov     a,c
        ora     a                       ; device zero is the only valid entry
        rz
        mvi     a,0ffh                  ; useful diagnostic result for USERF
        ret

NSCONOST:
NSAUXOST:
        mvi     a,0ffh                  ; authoritative local output is ready
        ret

NSAUXIST:
        xra     a                       ; no separately assigned AUX source
        ret

; CP/M 3 announces the next bounded sequential transfer in A. The current
; synchronous driver remains single-record. Like DRI bioskrnl.asm's private
; @cnt, keep this in BIOS-owned status rather than overwriting BDOS's @MLTIO.
NSMULTIO:
        sta     NSLASTMULTIO
        ret

; There is no target-side write cache. Every accepted NetDisk write is
; acknowledged only after host write-through, therefore FLUSH is immediate.
NSFLUSH:
        xra     a
        ret

; CP/M 3 MOVE: DE=source, HL=destination, BC=count. Preserve memmove semantics
; for overlap and return both pointers advanced past the copied range.
NSMOVE:
        mov     a,b
        ora     c
        rz
        mov     a,h
        cmp     d
        jc      NSMOVEFORWARD
        jnz     NSMOVEBACK
        mov     a,l
        cmp     e
        jc      NSMOVEFORWARD
        jz      NSMOVESAME
NSMOVEBACK:
        push    b
        dad     b
        push    h                       ; returned destination end
        xchg
        dad     b
        push    h                       ; returned source end
        dcx     h
        xchg
        dcx     h
NSMOVEBACK1:
        ldax    d
        mov     m,a
        dcx     d
        dcx     h
        dcx     b
        mov     a,b
        ora     c
        jnz     NSMOVEBACK1
        pop     d
        pop     h
        pop     b
        lxi     b,0
        ret
NSMOVEFORWARD:
        ldax    d
        mov     m,a
        inx     d
        inx     h
        dcx     b
        mov     a,b
        ora     c
        jnz     NSMOVEFORWARD
        ret
NSMOVESAME:
        dad     b
        xchg
        dad     b
        xchg
        lxi     b,0
        ret

; Optional host clock. NCTIME commits a GET only after a complete valid reply
; and keeps SET session-local on the host. Boot and disk never call this path.
; Preserve HL/DE exactly as required by the CP/M 3 System Guide.
NSTIME:
        push    h
        push    d
        call    NCTIME
        sta     NSCLOCKSTATUS
        ora     a
        lxi     h,NSCLOCKOK
        jz      NSTIMECOUNT
        lxi     h,NSCLOCKFAIL
NSTIMECOUNT:
        inr     m
        jnz     NSTIMERET
        inx     h
        inr     m
NSTIMERET:
        pop     d
        pop     h
        ret

; Reserved CP/M 3 BIOS entry 30 is the versioned Juku USERF extension.
; C=0: return HL -> read-only status block after refreshing S21.
; Other selectors return A=FFh, HL=0000h.
NSUSERF:
        mov     a,c
        ora     a
        jnz     NSUSERFBAD
        call    NSSAMPLES21
        lxi     h,NSINFO
        xra     a
        ret
NSUSERFBAD:
        lxi     h,0
        mvi     a,0ffh
        ret

; Sample S21 using the drawing's scan positions 8..15. Closed switches are
; active low on PB5; bits are returned in the same raw order as RKCONFIG.
NSSAMPLES21:
        push    b
        push    d
        mvi     b,8
        mvi     c,8
        mvi     d,0
NSS21LOOP:
        mov     a,b
        out     KEYCOLPORT
        in      KEYROWPORT
        cma
        ani     020h
        mov     e,a
        mov     a,d
        add     a
        mov     d,a
        mov     a,e
        ora     a
        jz      NSS21NEXT
        mov     a,d
        ori     1
        mov     d,a
NSS21NEXT:
        inr     b
        dcr     c
        jnz     NSS21LOOP
        mov     a,d
        sta     NSRAWS21
        rrc
        ani     3
        sta     NSVIDEOMODE
        pop     d
        pop     b
        ret

NSCHRTBL:
        db      'JUKU  ',3,0
        db      0

; Stable status block v1. Flags: bit0 character table, bit1 overlap MOVE,
; bit2 host time, bit3 raw/decoded S21.
NSINFO:
        db      'J','N','S','1'
        db      1,0
        db      NSINFOEND-NSINFO
        db      00fh
NSRAWS21:
        db      0
NSVIDEOMODE:
        db      0
NSLASTMULTIO:
        db      0
NSCLOCKSTATUS:
        db      0                       ; last clock status
NSCLOCKOK:
        dw      0                       ; successful clock replies
NSCLOCKFAIL:
        dw      0                       ; failed clock replies
NSINFOEND:

        end
