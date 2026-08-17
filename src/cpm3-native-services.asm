; Native CP/M Plus BIOS services for the Juku network-ROM profile.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

.ifdef ROM_ABI_LOCALE
        include "rom-abi.inc"
.endif

        cseg
        public  NSCONOST
        public  NSAUXIST
        public  NSAUXOST
        public  NSDEVTBL
        public  NSDEVINI
        public  NSCAPINIT
        public  NSMULTIO
        public  NSFLUSH
        public  NSMOVE
        public  NSTIME
        public  NSUSERF
        extrn   NCTIME
        extrn   NCPUBLISH
        extrn   NCDIAG
        extrn   NCBOOT
        extrn   NCCAPS
        extrn   NCCFG

KEYCOLPORT     equ     004h
KEYROWPORT     equ     005h
NCRECONNECT    equ     0c65ch
NCLASTFAIL     equ     0c65dh
ROMABISTATUS   equ     0c651h
ROMLASTDISK    equ     0c65eh
ROMLASTTRIES   equ     0c65fh
ROMPOSTSTATUS  equ     0d610h
ROMBOOTSTAGE   equ     0d611h
NATIVEBOOT     equ     0c640h
NATIVEPOST     equ     0c641h

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
        jnz     NSDEVINIBAD
        call    NSCAPINIT
        ret
NSDEVINIBAD:
        mvi     a,0ffh                  ; useful diagnostic result for USERF
        ret

; Negotiate runtime host features exactly once after resident serial setup.
; The adapter calls this on cold boot; DEVINI also calls it defensively for a
; CP/M implementation which invokes native device initialization later.
NSCAPINIT:
        lda     NSCAPDONE
        ora     a
        jnz     NSCAPINITOK
        mvi     a,1
        sta     NSCAPDONE               ; negotiate only once per cold image
        call    NCCAPS
        ora     a
        jnz     NSCAPINITOK              ; legacy host keeps bounded reprobes
        inx     h
        inx     h
        mov     a,m                     ; explicit host feature flags
        call    NCCFG
NSCAPINITOK:
        xra     a
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
; C=1: refresh and publish the same status tuple to the N4 host, then return
;      the status block. Publication is best effort and never blocks status.
; C=2 publishes a diagnostic tuple in B/D/E/L. C=3 returns the host's
; explicit four-byte capability record. C=4 publishes retained bootstrap
; stage/retries/protocol/ABI minor. Other selectors fail.
NSUSERF:
        mov     a,c
        ora     a
        jz      NSUSERFSAMPLE
        dcr     a
        jz      NSUSERFPUBLISH
        dcr     a
        jz      NSUSERFDIAG
        dcr     a
        jz      NSUSERFCAPS
        dcr     a
        jnz     NSUSERFBAD
        call    NSREFRESHINFO
        lda     NSBOOTRETRY
        mov     b,a
        lda     NSBOOTPROTO
        mov     d,a
        lda     NSROMMINOR
        mov     e,a
        lda     NSBOOTSTAGE
        call    NCBOOT
        jmp     NSUSERFRET
NSUSERFCAPS:
        call    NCCAPS
        ret
NSUSERFDIAG:
        mov     a,b                     ; C=2: B/D/E/L -> suite/pass/fail/flags
        mov     b,d
        mov     d,e
        mov     e,l
        call    NCDIAG
        jmp     NSUSERFRET
NSUSERFPUBLISH:
        call    NSSAMPLES21
        mvi     d,01fh                  ; NSINFO feature flags
        lda     NSCLOCKSTATUS
        mov     e,a
        lda     NSVIDEOMODE
        mov     b,a
        lda     NSRAWS21
        call    NCPUBLISH
        jmp     NSUSERFRET
NSUSERFSAMPLE:
        call    NSSAMPLES21
NSUSERFRET:
        call    NSREFRESHINFO
        lxi     h,NSINFO
        xra     a
        ret

NSREFRESHINFO:
        lda     NATIVEBOOT
        sta     NSBOOTCOPY
        lda     NATIVEPOST
        sta     NSPOSTCOPY
        lda     ROMABISTATUS
        sta     NSROMABICOPY
        lxi     h,ROMLASTDISK
        lxi     d,NSDISKSTATUS
        mvi     c,2
NSREFRESHCOPY2:
        mov     a,m
        stax    d
        inx     h
        inx     d
        dcr     c
        jnz     NSREFRESHCOPY2
        lda     NCLASTFAIL
        sta     NSCONFAIL
        lda     NCRECONNECT
        sta     NSCONRECONNECT
.ifdef ROM_ABI_LOCALE
        lxi     h,ROMBOOTSTAGE
        lxi     d,NSBOOTSTAGE
        mvi     c,3
NSREFRESHBOOT:
        mov     a,m
        stax    d
        inx     h
        inx     d
        dcr     c
        jnz     NSREFRESHBOOT
.else
        xra     a
        sta     NSBOOTSTAGE
        sta     NSBOOTRETRY
        sta     NSBOOTPROTO
.endif
        ret
NSUSERFBAD:
        lxi     h,0
        mvi     a,0ffh
        ret

; Sample S21 using the drawing's scan positions 8..15. Closed switches are
; active low on PB5; bits are returned in the same raw order as RKCONFIG.
NSSAMPLES21:
.ifdef ROM_ABI_LOCALE
        call    JCGCONFIGADDR
        sta     NSRAWS21
        mov     a,b
        sta     NSVIDEOMODE
        ret
.else
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
.endif

NSCHRTBL:
        db      'JUKU  ',3,0
        db      0

; Stable status block v1. Flags: bit0 character table, bit1 overlap MOVE,
; bit2 host time, bit3 raw/decoded S21.
NSINFO:
        db      'J','N','S','1'
        db      1,1
        db      NSINFOEND-NSINFO
        db      01fh
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
NSBOOTCOPY:
        db      0                       ; 0 cold, 1 warm
NSPOSTCOPY:
        db      0                       ; reset POST status copied at cold boot
NSROMABICOPY:
        db      0                       ; ROM ABI initialization status
NSDISKSTATUS:
        db      0                       ; last BIOS read/write status
NSDISKTRIES:
        db      0                       ; attempts left after last wire request
NSCONFAIL:
        db      0                       ; last bounded N4 failure reason
NSCONRECONNECT:
        db      0                       ; saturated successful reprobe count
NSBOOTSTAGE:
        db      0                       ; retained reset/V15/system/disk stage
NSBOOTRETRY:
        db      0                       ; saturated compressed-stream failures
NSBOOTPROTO:
        db      0                       ; active fastboot protocol version
NSROMMAJOR:
        db      1
NSROMMINOR:
.ifdef ROM_ABI_LOCALE
        db      1
.else
        db      0
.endif
NSINFOEND:
NSCAPDONE:
        db      0

        end
