; Physical video-path probe for Juku CP/M Plus.
; Copyright (c) 2026 Danila Sukharev
; BSD-2-Clause; see ../LICENSE.
;
; This deliberately bypasses the ROM console. It reapplies the stock 40x24
; raster registers, maps the framebuffer, and fills all 9,600 bytes with an
; alternating pattern. A visible raster proves the timer, memory-map, DRAM,
; and video-data path without relying on character rendering.

BDOS            equ     0005h
PRINT           equ     9
MODEPORT        equ     006h
PIT54CONTROL    equ     013h
PIT55CONTROL    equ     017h
PIT54COUNT0     equ     010h
PIT54COUNT1     equ     011h
PIT54COUNT2     equ     012h
PIT55COUNT0     equ     014h
PIT55COUNT1     equ     015h
PIT55COUNT2     equ     016h
VRAM            equ     0d800h
SCREENBYTES     equ     9600

        org     0100h

start:
        lxi     d,banner
        mvi     c,PRINT
        call    BDOS

        ; Reissue the stock D54/D55 setup without touching D57, whose channel
        ; zero owns the live serial clock. These are the reset ROM's exact
        ; control words followed by its 320x241 raster counts.
        mvi     a,015h
        out     PIT54CONTROL
        mvi     a,053h
        out     PIT54CONTROL
        mvi     a,093h
        out     PIT54CONTROL
        mvi     a,073h
        out     PIT55CONTROL
        mvi     a,093h
        out     PIT55CONTROL
        mvi     a,034h
        out     PIT55CONTROL
        mvi     a,039h
        out     PIT55COUNT0
        mvi     a,001h
        out     PIT55COUNT0
        mvi     a,064h
        out     PIT54COUNT0
        mvi     a,024h
        out     PIT54COUNT1
        mvi     a,008h
        out     PIT54COUNT2
        mvi     a,072h
        out     PIT55COUNT1
        xra     a
        out     PIT55COUNT1
        mvi     a,025h
        out     PIT55COUNT2

        di
        in      MODEPORT
        sta     saved_mode
        ani     0fch
        ori     3
        out     MODEPORT

        lxi     h,VRAM
        lxi     b,SCREENBYTES
        mvi     d,055h
fill:
        mov     m,d
        mov     a,d
        cma
        mov     d,a
        inx     h
        dcx     b
        mov     a,b
        ora     c
        jnz     fill

        xra     a
        sta     readback_failed
        lxi     h,VRAM
        lxi     b,SCREENBYTES
        mvi     d,055h
verify:
        mov     a,m
        cmp     d
        jz      verify_next
        mvi     a,1
        sta     readback_failed
verify_next:
        mov     a,d
        cma
        mov     d,a
        inx     h
        dcx     b
        mov     a,b
        ora     c
        jnz     verify

        lda     saved_mode
        out     MODEPORT
        ei
        lda     readback_failed
        ora     a
        lxi     d,readback_pass
        jz      report
        lxi     d,readback_fail
report:
        mvi     c,PRINT
        call    BDOS
        ret

saved_mode:
        db      0
readback_failed:
        db      0
banner:
        db      'VIDPROBE: stock 40x24 timing, raw 55/AA framebuffer$'
readback_pass:
        db      13,10,'VRAM READBACK PASS$'
readback_fail:
        db      13,10,'VRAM READBACK FAIL$'

        end     start
