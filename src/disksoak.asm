; One bounded CP/M filesystem write-through cycle for NetDisk soak tests.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
PRINT           equ     9
CLOSE_FILE      equ     16
DELETE_FILE     equ     19
WRITE_SEQ       equ     21
MAKE_FILE       equ     22
SET_DMA         equ     26
DMA             equ     0200h

        org     0100h

start:
        lxi     d,fcb
        mvi     c,DELETE_FILE          ; remove stale file after interrupted run
        call    BDOS
        lxi     d,fcb
        mvi     c,MAKE_FILE
        call    BDOS
        cpi     0ffh
        jz      failed
        lxi     h,DMA
        mvi     b,128
        mvi     a,05ah
fill:
        mov     m,a
        inx     h
        xri     0ffh
        dcr     b
        jnz     fill
        lxi     d,DMA
        mvi     c,SET_DMA
        call    BDOS
        lxi     d,fcb
        mvi     c,WRITE_SEQ
        call    BDOS
        ora     a
        jnz     failed
        lxi     d,fcb
        mvi     c,CLOSE_FILE
        call    BDOS
        cpi     0ffh
        jz      failed
        lxi     d,fcb
        mvi     c,DELETE_FILE
        call    BDOS
        cpi     0ffh
        jz      failed
        lxi     d,passed
        mvi     c,PRINT
        call    BDOS
        ret
failed:
        lxi     d,failure
        mvi     c,PRINT
        call    BDOS
        ret

fcb:
        db      0,'SOAK    ','TMP'
        ds      24
passed:
        db      'SOAK: PASS',13,10,'$'
failure:
        db      'SOAK: FAIL',13,10,'$'

        end
