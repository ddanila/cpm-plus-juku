; Physical qualification caller for the resident ROM sound service.
; Copyright (c) 2026 Danila Sukharev

BDOS            equ     0005h
PRINT           equ     9
; JROMGATEBASE D620h + JCGSOUND offset 21h, from rom-abi.inc.
JCGSOUND        equ     0d641h

        org     0100h

start:
        lxi     d,starting
        mvi     c,PRINT
        call    BDOS
        mvi     a,1
        call    JCGSOUND
        ora     a
        jnz     failed
        lxi     d,passed
        mvi     c,PRINT
        call    BDOS
        ret

failed:
        lxi     d,failure
        mvi     c,PRINT
        call    BDOS
        ret

starting:
        db      13,10,'SOUND: playing ROM diagnostic tune',13,10,'$'
passed:
        db      'SOUND: service returned PASS',13,10,'$'
failure:
        db      'SOUND: service returned FAIL',13,10,'$'

        end     start
