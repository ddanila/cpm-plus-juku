; Target-side regression for the generic volatile-session USERF service.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
PRINT           equ     9

        org     0100h

start:
        lda     0080h
        ora     a
        jz      fullcheck
        lxi     h,0081h
argskip:
        mov     a,m
        cpi     ' '
        jnz     argready
        inx     h
        jmp     argskip
argready:
        ani     05fh
        cpi     'R'
        jz      readcheck
        cpi     'C'
        jz      clearcheck
        mvi     a,0f0h
        jmp     faila

fullcheck:
        mvi     a,1
        sta     stage
        lxi     d,owner1
        lxi     h,buffer
        mvi     b,127
        mvi     c,6
        call    session_call
        cpi     1                      ; cold image begins unclaimed
        jnz     failed

        mvi     a,2
        sta     stage
        lxi     d,owner1
        lxi     h,payload
        mvi     b,payload_end-payload
        mvi     c,7
        call    session_call
        ora     a
        jnz     failed
        mov     a,b
        cpi     payload_end-payload
        jnz     failed

        mvi     a,3
        sta     stage
        call    readowner1
        call    checkpayload
        jnz     failed

        mvi     a,4
        sta     stage
        lxi     d,owner1
        lxi     h,buffer
        mvi     b,payload_end-payload-1
        mvi     c,6
        call    session_call
        cpi     2                      ; caller buffer is too small
        jnz     failed

        mvi     a,5
        sta     stage
        lxi     d,owner2
        lxi     h,buffer
        mvi     b,127
        mvi     c,6
        call    session_call
        cpi     1                      ; owner keys isolate readers
        jnz     failed

        mvi     a,6
        sta     stage
        lxi     d,owner2
        lxi     h,payload
        mvi     b,128
        mvi     c,7
        call    session_call
        cpi     2                      ; oversized write is rejected
        jnz     failed
        call    readowner1
        call    checkpayload           ; rejection preserved the old owner/blob
        jnz     failed

        mvi     a,7
        sta     stage
        lxi     d,owner2
        lxi     h,buffer
        mvi     b,0
        mvi     c,7
        call    session_call
        cpi     1                      ; foreign owner cannot release the slot
        jnz     failed
        call    readowner1
        call    checkpayload
        jnz     failed

        lxi     d,passed
        jmp     emit

readcheck:
        mvi     a,020h
        sta     stage
        call    readowner1
        call    checkpayload
        jnz     failed
        lxi     d,readpassed
        jmp     emit

clearcheck:
        mvi     a,030h
        sta     stage
        lxi     d,owner1
        lxi     h,buffer
        mvi     b,0
        mvi     c,7
        call    session_call
        ora     a
        jnz     failed
        lxi     d,owner1
        lxi     h,buffer
        mvi     b,127
        mvi     c,6
        call    session_call
        cpi     1
        jnz     failed
        lxi     d,clearpassed
        jmp     emit

readowner1:
        lxi     d,owner1
        lxi     h,buffer
        mvi     b,127
        mvi     c,6
        call    session_call
        ora     a
        rnz
        mov     a,b
        cpi     payload_end-payload
        ret

checkpayload:
        lxi     h,buffer
        lxi     d,payload
        mvi     b,payload_end-payload
checkpayload1:
        ldax    d
        cmp     m
        rnz
        inx     d
        inx     h
        dcr     b
        jnz     checkpayload1
        xra     a
        ret

faila:
        sta     stage
failed:
        lxi     d,failedmsg
        mvi     c,PRINT
        call    BDOS
        lda     stage
        call    printhex
        lxi     d,newline
emit:
        mvi     c,PRINT
        call    BDOS
        ret

printhex:
        push    psw
        rrc
        rrc
        rrc
        rrc
        ani     00fh
        call    printnibble
        pop     psw
        ani     00fh
printnibble:
        adi     '0'
        cpi     '9'+1
        jc      printdigit
        adi     'A'-'9'-1
printdigit:
        mov     e,a
        mvi     c,2
        call    BDOS
        ret

; Call BIOS USERF through public CP/M 3 BDOS Function 50. Inputs and returned
; registers retain the service ABI: C selector, B length/capacity, DE owner,
; and HL payload buffer.
session_call:
        mov     a,c
        sta     bios_bc
        mov     a,b
        sta     bios_bc+1
        xchg
        shld    bios_de
        xchg
        shld    bios_hl
        lxi     d,bios_function
        mvi     c,50
        jmp     BDOS

passed: db      'SESSION: PASS',13,10,'$'
readpassed:
        db      'SESSION READ: PASS',13,10,'$'
clearpassed:
        db      'SESSION CLEAR: PASS',13,10,'$'
failedmsg:
        db      'SESSION: FAIL stage $'
newline:db      13,10,'$'
owner1: db      'TST1'
owner2: db      'TST2'
payload:db      'HELLO'
payload_end:
stage:  db      0
buffer: ds      127
bios_function: db      30
bios_a:        db      0
bios_bc:       dw      0
bios_de:       dw      0
bios_hl:       dw      0

        end     start
