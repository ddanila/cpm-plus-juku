        title   'Juku CP/M Plus volatile session slot'

; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.
;
; One keyed 127-byte blob survives warm boots and transient replacement but
; is reset by a cold system load.  The service code replaces the second hot-
; directory cache record at D440h; its payload uses the second former record
; at D3C0h. Directory record 1 remains cached throughout the session.

        cseg
        public  NSSESSREAD
        public  NSSESSWRITE
        extrn   NSMOVE

SESSOWNER     equ     0c5a2h          ; four opaque owner bytes
SESSLEN       equ     0c5a6h
SESSDATA      equ     0d3c0h          ; 127 bytes available through D43Eh

; USERF selector 6: B=destination capacity, DE=owner, HL=buffer.
; A=0/B=length on success, A=1 when empty/other owner, A=2 when too small.
NSSESSREAD:
        call    NSSESSMATCH
        ora     a
        rnz
        lda     SESSLEN
        cmp     b
        jc      NSSESSREADFIT
        jz      NSSESSREADFIT
        mvi     a,2
        ret
NSSESSREADFIT:
        mov     c,a
        mvi     b,0
        lxi     d,SESSDATA              ; source; caller HL is destination
        call    NSMOVE
        lda     SESSLEN
        mov     b,a
        xra     a
        ret

; USERF selector 7: B=source length (1..127), DE=owner, HL=buffer.
; A zero-length write releases the slot only when the owner matches.
NSSESSWRITE:
        mov     a,b
        ora     a
        jz      NSSESSCLEAR
        jm      NSSESSTOOBIG
        push    b
        push    h
        xra     a                       ; unpublish the old value while copying
        sta     SESSLEN
        lxi     h,SESSOWNER
        lxi     b,4
        call    NSMOVE
        pop     h                       ; caller source
        pop     b
        push    b
        mov     c,b
        mvi     b,0
        xchg                            ; caller source in DE
        lxi     h,SESSDATA              ; destination
        call    NSMOVE
        pop     b
        mov     a,b                     ; publish only after the complete copy
        sta     SESSLEN
        xra     a
        ret

NSSESSCLEAR:
        call    NSSESSMATCH
        ora     a
        rnz
        sta     SESSLEN
        ret

NSSESSTOOBIG:
        mvi     a,2
        ret

; Compare the four-byte owner while retaining the caller's HL buffer and B.
NSSESSMATCH:
        lda     SESSLEN
        ora     a
        jz      NSSESSMISS
        push    h
        lxi     h,SESSOWNER
        mvi     c,4
NSSESSMATCHLOOP:
        ldax    d
        cmp     m
        jnz     NSSESSMATCHBAD
        inx     d
        inx     h
        dcr     c
        jnz     NSSESSMATCHLOOP
        pop     h
        xra     a
        ret
NSSESSMATCHBAD:
        pop     h
NSSESSMISS:
        mvi     a,1
        ret

        end
