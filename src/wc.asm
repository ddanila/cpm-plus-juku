; Text line, word, and byte counts for CP/M files.
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
        sta     inword
        lxi     h,lines
        mvi     b,9
clearcounts:
        mov     m,a
        inx     h
        dcr     b
        jnz     clearcounts

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
        cpi     01ah
        jz      finished
        push    h
        lxi     h,bytes
        call    increment24
        pop     h
        mov     a,m
        cpi     10
        jnz     notline
        push    h
        lxi     h,lines
        call    increment24
        pop     h
notline:
        mov     a,m
        cpi     ' '+1
        jc      whitespace
        lda     inword
        ora     a
        jnz     nextbyte
        mvi     a,1
        sta     inword
        push    h
        lxi     h,words
        call    increment24
        pop     h
        jmp     nextbyte
whitespace:
        xra     a
        sta     inword
nextbyte:
        inx     h
        dcr     b
        jnz     byteloop
        jmp     readnext

finished:
        lxi     d,result
        call    puts
        lxi     h,lines
        call    print24
        lxi     d,wordmsg
        call    puts
        lxi     h,words
        call    print24
        lxi     d,bytemsg
        call    puts
        lxi     h,bytes
        call    print24
        lxi     d,newline
        jmp     puts

increment24:
        inr     m
        rnz
        inx     h
        inr     m
        rnz
        inx     h
        inr     m
        ret

; HL points to little-endian 24-bit value; display six hexadecimal digits.
print24:
        push    h
        inx     h
        inx     h
        mov     a,m
        call    printbyte
        pop     h
        push    h
        inx     h
        mov     a,m
        call    printbyte
        pop     h
        mov     a,m
        jmp     printbyte

usage:
        lxi     d,usagemsg
        jmp     puts
nofile:
        lxi     d,nofilemsg
        jmp     puts
puts:
        mvi     c,PRINT
        jmp     BDOS
printbyte:
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
        jc      printchar
        adi     'A'-'9'-1
printchar:
        mov     e,a
        mvi     c,CONOUT
        jmp     BDOS

title:
        db      'Juku WC 1.0',13,10,'$'
result:
        db      'WC (hex): lines $'
wordmsg:
        db      '  words $'
bytemsg:
        db      '  bytes $'
usagemsg:
        db      'Usage: WC textfile',13,10,'$'
nofilemsg:
        db      'WC: file not found',13,10,'$'
newline:
        db      13,10,'$'

lines:  ds      3
words:  ds      3
bytes:  ds      3
inword: db      0
dma:    ds      128

        end
