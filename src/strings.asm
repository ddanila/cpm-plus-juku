; Extract printable ASCII runs of at least four bytes from a CP/M file.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
FCB             equ     005ch
OPEN            equ     15
READSEQ         equ     20
SETDMA          equ     26
PRINT           equ     9
CONOUT          equ     2

        org     0100h

start:
        lxi     d,title
        call    puts
        lda     FCB+1
        cpi     ' '
        jz      usage
        lxi     d,FCB
        mvi     c,OPEN
        call    BDOS
        inr     a
        jz      nofile
        xra     a
        sta     runstate

readnext:
        lxi     d,dma
        mvi     c,SETDMA
        call    BDOS
        lxi     d,FCB
        mvi     c,READSEQ
        call    BDOS
        ora     a
        jnz     finished
        lxi     h,dma
        mvi     b,128
byteloop:
        mov     a,m
        push    b
        push    h
        call    consume
        pop     h
        pop     b
        inx     h
        dcr     b
        jnz     byteloop
        jmp     readnext

finished:
        xra     a
        call    consume
        ret

; States 0..3 buffer a short run; state 4 streams an accepted run.
consume:
        cpi     020h
        jc      delimiter
        cpi     07fh
        jnc     delimiter
        sta     current
        lda     runstate
        cpi     4
        jz      streamchar
        cpi     3
        jz      acceptrun
        mov     e,a
        mvi     d,0
        lxi     h,prefix
        dad     d
        lda     current
        mov     m,a
        lda     runstate
        inr     a
        sta     runstate
        ret
acceptrun:
        lda     prefix
        call    printchar
        lda     prefix+1
        call    printchar
        lda     prefix+2
        call    printchar
        mvi     a,4
        sta     runstate
streamchar:
        lda     current
        jmp     printchar
delimiter:
        lda     runstate
        cpi     4
        jnz     reset
        lxi     d,newline
        call    puts
reset:
        xra     a
        sta     runstate
        ret

usage:
        lxi     d,usagemsg
        jmp     puts
nofile:
        lxi     d,nofilemsg
        jmp     puts
puts:
        mvi     c,PRINT
        jmp     BDOS
printchar:
        mov     e,a
        mvi     c,CONOUT
        jmp     BDOS

title:
        db      'Juku STRINGS 1.0 (ASCII, minimum 4)',13,10,'$'
usagemsg:
        db      'Usage: STRINGS filename',13,10,'$'
nofilemsg:
        db      'STRINGS: file not found',13,10,'$'
newline:
        db      13,10,'$'

runstate:
        db      0
current:
        db      0
prefix:
        ds      3
dma:
        ds      128

        end
