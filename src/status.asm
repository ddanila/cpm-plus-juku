; Juku CP/M Plus configuration and resident-system report.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
PRINT           equ     9

        org     0100h

start:
        lxi     d,title
        call    puts
        mvi     a,30                   ; versioned Juku USERF
        call    setvector
        mvi     c,1                    ; sample S21 and publish to N4 host
        call    bioscall
        ora     a
        jnz     unavailable
        mov     a,m
        cpi     'J'
        jnz     unavailable
        inx     h
        mov     a,m
        cpi     'N'
        jnz     unavailable
        inx     h
        mov     a,m
        cpi     'S'
        jnz     unavailable
        inx     h
        mov     a,m
        cpi     '1'
        jnz     unavailable
        dcx     h
        dcx     h
        dcx     h
        shld    infobase

        lxi     d,identity
        call    puts
        lxi     d,mapmsg
        call    puts

        lxi     d,s21msg
        call    puts
        lhld    infobase
        lxi     d,8
        dad     d
        mov     a,m
        call    printhex

        lxi     d,videomsg
        call    puts
        inx     h
        mov     a,m
        push    h
        call    printhex
        pop     h
        mov     a,m
        ani     3
        add     a
        mov     e,a
        mvi     d,0
        lxi     h,modetable
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        call    puts

        lxi     d,featuresmsg
        call    puts
        lhld    infobase
        lxi     d,7
        dad     d
        mov     a,m
        call    printhex
        lxi     d,multiomsg
        call    puts
        lhld    infobase
        lxi     d,10
        dad     d
        mov     a,m
        call    printhex

        lxi     d,clockmsg
        call    puts
        inx     h
        mov     a,m
        call    printhex
        lxi     d,clockokmsg
        call    puts
        inx     h
        mov     e,m
        inx     h
        mov     d,m
        xchg
        call    printword
        lxi     d,clockfailmsg
        call    puts
        lhld    infobase
        lxi     d,14
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        xchg
        call    printword
        lxi     d,newline
        jmp     puts

unavailable:
        lxi     d,unavailablemsg
        jmp     puts

puts:
        mvi     c,PRINT
        jmp     BDOS

printword:
        mov     a,h
        call    printhex
        mov     a,l
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
        push    h
        push    d
        mov     e,a
        mvi     c,2
        call    BDOS
        pop     d
        pop     h
        ret

; Patch a call to BIOS base + A*3. Address 0001h holds WBOOT (base+3).
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

title:  db      13,10,'Juku Status 1.0',13,10,'$'
identity:
        db      'System: CP/M Plus 3.1, native profile 1',13,10
        db      'Transport: NetDisk v3, 19200 baud, N4 services',13,10
        db      'ROM: Juku ABI 1.0 network-first baseline',13,10,'$'
mapmsg:
        db      'Map: TPA 0100-9CFF, BDOS 9D00-BB9B, SCB BB9C-BBFF',13,10
        db      '     BIOS BC00-BFFF, adapter C000-C5EB, state C5EC-C909',13,10
        db      '     ROM gate/work D600-D7FF, framebuffer D800-FFFF',13,10,'$'
s21msg: db      'S21 raw: $'
videomsg:
        db      '  video: $'
featuresmsg:
        db      13,10,'Features: $'
multiomsg:
        db      '  last MULTIO: $'
clockmsg:
        db      13,10,'Clock status: $'
clockokmsg:
        db      '  good: $'
clockfailmsg:
        db      '  failed: $'
newline:
        db      13,10,'$'
unavailablemsg:
        db      'Native JNS1 status service unavailable.',13,10,'$'
mode0:  db      ' (40x24)',13,10,'$'
mode1:  db      ' (53x24)',13,10,'$'
mode2:  db      ' (64x20)',13,10,'$'
mode3:  db      ' (80x24)',13,10,'$'
modetable:
        dw      mode0,mode1,mode2,mode3
infobase:
        dw      0
        end
