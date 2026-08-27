        title   'Juku CP/M Plus hot-directory cache'

; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.
;
; C6's resident NetDisk cache holds one eight-record reply per drive. CP/M 3
; revisits the first three directory records after its initial scan, by which
; time that reply has been displaced by later directory groups. Preserve
; the measured records in otherwise unused high RAM. The ordinary profile
; retains all three. SESSION_STATE reserves record 3 for service code and lets
; its payload claim record 2 while keeping record 1 independently cached. The cache is
; read-only, shared by the currently active drive, and invalidated before any
; write to that drive. It therefore cannot weaken synchronous write-through.

        cseg
        public  HDINIT
        public  HDLOOK
        public  HDSAVE
        public  HDINVAL

SEKDSK          equ     0c93ah
SEKTRK          equ     0c93bh
SEKSEC          equ     0c93dh
MEMADR          equ     0c94eh

; SESSION_STATE uses D3C0h for its payload and D440h for service code.
HOTVALID        equ     0c5a0h
HOTDRIVE        equ     0c5a1h
SESSLEN         equ     0c5a6h
HOTDATA1        equ     0c5c0h
HOTDATA2        equ     0d3c0h
HOTDATA3        equ     0d440h

HDINIT:
        xra     a
        sta     HOTVALID
.ifdef SESSION_STATE
        sta     SESSLEN
.endif
        dcr     a
        sta     HOTDRIVE
        ret

; Return carry clear and copy the cached record to the current DMA address on
; a hit. Return carry set without changing DMA on a miss.
HDLOOK:
        call    HDSELECT
        rc
        lda     HOTVALID
        ana     c
        jz      HDMISS
        lda     SEKDSK
        mov     b,a
        lda     HOTDRIVE
        cmp     b
        jnz     HDMISS
        xchg                           ; DE = cache source
        lhld    MEMADR
        xchg                           ; HL = source, DE = DMA destination
        mvi     b,128
HDLOOK1:
        mov     a,m
        stax    d
        inx     h
        inx     d
        dcr     b
        jnz     HDLOOK1
        xra     a                      ; success and carry clear
        ret

; Save a successful underlying read when it is one of the three hot records.
HDSAVE:
        call    HDSELECT
        rc
        lda     SEKDSK
        mov     b,a
        lda     HOTDRIVE
        cmp     b
        jz      HDSAME
        mov     a,b
        sta     HOTDRIVE
        xra     a
        sta     HOTVALID
HDSAME:
        xchg                           ; DE = cache destination
        lhld    MEMADR                 ; HL = DMA source
        mvi     b,128
HDSAVE1:
        mov     a,m
        stax    d
        inx     h
        inx     d
        dcr     b
        jnz     HDSAVE1
        lda     HOTVALID
        ora     c
        sta     HOTVALID
        xra     a
        ret

; Invalidate before any write to the cached drive. Failed writes leave the
; cache invalid, which is conservative and prevents stale directory data.
HDINVAL:
        lda     HOTVALID
        ora     a
        rz
        lda     SEKDSK
        mov     b,a
        lda     HOTDRIVE
        cmp     b
        rnz
        xra     a
        sta     HOTVALID
        ret

; Select one of track 2's translated hot sectors. Return its cache
; pointer in HL and validity mask in C, or carry set when the key is not hot.
HDSELECT:
        lda     SEKDSK
        cpi     2
        jnc     HDMISS
        lda     SEKTRK+1
        ora     a
        jnz     HDMISS
        lda     SEKTRK
        cpi     2
        jnz     HDMISS
        lda     SEKSEC
        cpi     1
        jz      HDSEL1
        cpi     2
        jz      HDSEL2
.ifdef SESSION_STATE
        jmp     HDMISS
.else
        cpi     3
        jnz     HDMISS
        mvi     c,4
        lxi     h,HOTDATA3
        ora     a
        ret
.endif
HDSEL2:
.ifdef SESSION_STATE
        lda     SESSLEN
        ora     a
        jnz     HDMISS
.endif
        mvi     c,2
        lxi     h,HOTDATA2
.ifndef SESSION_STATE
        ora     a
.endif
        ret
HDSEL1:
        mvi     c,1
        lxi     h,HOTDATA1
        ora     a
        ret
HDMISS:
        stc
        ret

        end
