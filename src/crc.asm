; CRC-16/CCITT checksum for a CP/M file.
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
        lxi     h,0ffffh
        shld    crc
        lxi     h,0
        shld    records

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
        push    h
        call    crcbyte
        pop     h
        inx     h
        dcr     b
        jnz     byteloop
        lhld    records
        inx     h
        shld    records
        jmp     readnext

finished:
        lxi     d,result
        call    puts
        lhld    crc
        call    printword
        lxi     d,recordmsg
        call    puts
        lhld    records
        call    printword
        lxi     d,newline
        jmp     puts

; A=byte, update the big-endian CRC state with polynomial 1021h.
crcbyte:
        mov     e,a
        lda     crchi
        xra     e
        sta     crchi
        mvi     c,8
crcbit:
        lda     crclo
        add     a
        sta     crclo
        lda     crchi
        ral
        sta     crchi
        jnc     crcnoxor
        lda     crclo
        xri     021h
        sta     crclo
        lda     crchi
        xri     010h
        sta     crchi
crcnoxor:
        dcr     c
        jnz     crcbit
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

printword:
        push    h
        mov     a,h
        call    printbyte
        pop     h
        mov     a,l
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
        db      'Juku CRC 1.0',13,10,'$'
result:
        db      'CRC16-CCITT: $'
recordmsg:
        db      '  records: $'
usagemsg:
        db      'Usage: CRC filename',13,10,'$'
nofilemsg:
        db      'CRC: file not found',13,10,'$'
newline:
        db      13,10,'$'

crc:
crclo:  db      0
crchi:  db      0
records:
        dw      0
dma:
        ds      128

        end
