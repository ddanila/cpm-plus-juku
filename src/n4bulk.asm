; Target-side proof for the bounded N4 output operation.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
PRINT           equ     9

        org     0100h

start:
        mvi     a,30                   ; CP/M Plus USERF vector
        call    setvector
        lxi     d,message
        mvi     b,message_end-message
        mvi     c,5                    ; ABI 1.2 bounded N4 span
        call    bioscall
        ora     a
        rz
        lxi     d,failed
        mvi     c,PRINT
        call    BDOS
        ret

; Patch a call to BIOS base + A*3. Address 0001h holds BIOS WBOOT (base+3).
setvector:
        mov     l,a
        mvi     h,0
        mov     d,h
        mov     e,l
        dad     h
        dad     d
        xchg
        lhld    0001h
        dcx     h
        dcx     h
        dcx     h
        dad     d
        shld    bioscall+1
        ret
bioscall:
        call    0000h
        ret

message:
        db      'N4 BULK PASS',13,10
message_end:
failed:
        db      'N4 BULK FAIL',13,10,'$'

        end     start
