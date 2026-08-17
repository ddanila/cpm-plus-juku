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
        lda     0c642h                 ; native adapter marker, avoids C4 USERF
        cpi     04eh
        jnz     unavailable
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
        lxi     d,rommsg
        call    puts
        lhld    infobase
        lxi     d,26
        dad     d
        mov     a,m
        call    printhex
        push    h
        lxi     d,dotmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        lxi     d,romsuffix
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

        push    h
        lxi     d,videomsg
        call    puts
        pop     h
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

        lxi     d,localemsg
        call    puts
        lhld    infobase
        lxi     d,8
        dad     d
        mov     a,m
        rrc
        rrc
        rrc
        ani     3
        add     a
        mov     e,a
        mvi     d,0
        lxi     h,localetable
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

        push    h
        lxi     d,clockmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,clockokmsg
        call    puts
        pop     h
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
        lxi     d,bootmsg
        call    puts
        lhld    infobase
        lxi     d,16
        dad     d
        mov     a,m
        call    printhex
        push    h
        lxi     d,postmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,abimsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,diskmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,triesmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,consolemsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,reconnectmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        lxi     d,newline
        call    puts

        lxi     d,bootstrapmsg
        call    puts
        lhld    infobase
        lxi     d,23
        dad     d
        mov     a,m
        call    printhex
        push    h
        lxi     d,bootstrapretrymsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,bootstrapprotomsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        lxi     d,newline
        call    puts

        mvi     a,30
        call    setvector
        mvi     c,4                    ; publish retained bootstrap tuple
        call    bioscall

        mvi     a,30
        call    setvector
        mvi     c,3                    ; explicit host capability query
        call    bioscall
        ora     a
        jnz     caps_unavailable
        shld    capsbase
        lxi     d,capsmsg
        call    puts
        lhld    capsbase
        mov     a,m
        call    printhex
        push    h
        lxi     d,aheadmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,hostfeaturesmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        push    h
        lxi     d,drivesmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        lxi     d,newline
        jmp     puts

caps_unavailable:
        lxi     d,capsunavailablemsg
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

title:  db      13,10,'Juku Status 1.3',13,10,'$'
identity:
        db      'System: CP/M Plus 3.1, native profile 1',13,10
        db      'Transport: NetDisk v3, 19200 baud, N4 services',13,10,'$'
rommsg: db      'ROM: Juku ABI $'
dotmsg: db      '.$'
romsuffix:
        db      ' network-first',13,10,'$'
mapmsg:
        db      'Map: TPA 0100-9CFF, BDOS 9D00-BB9B, SCB BB9C-BBFF',13,10
        db      '     Core C000-C52A, state C640-C95F, native CA00-CB80 max',13,10
        db      '     ROM gate/work D600-D7FF, framebuffer D800-FFFF',13,10,'$'
s21msg: db      'S21 raw: $'
videomsg:
        db      '  video: $'
localemsg:
        db      'Locale: $'
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
bootmsg:
        db      13,10,'Boot marker (00 cold/01 warm): $'
postmsg:
        db      '  POST: $'
abimsg:
        db      '  ROM ABI: $'
diskmsg:
        db      13,10,'Disk status: $'
triesmsg:
        db      '  tries left: $'
consolemsg:
        db      13,10,'N4 last failure: $'
reconnectmsg:
        db      '  reconnects: $'
bootstrapmsg:
        db      'Bootstrap stage: $'
bootstrapretrymsg:
        db      '  CRC retries: $'
bootstrapprotomsg:
        db      '  protocol: $'
capsmsg:
        db      'Host caps: NetDisk v$'
aheadmsg:
        db      '  read-ahead: $'
hostfeaturesmsg:
        db      '  features: $'
drivesmsg:
        db      '  drives: $'
capsunavailablemsg:
        db      'Host capability query unavailable.',13,10,'$'
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
locale0: db     'English',13,10,'$'
locale1: db     'Estonian',13,10,'$'
locale2: db     'Russian CP866',13,10,'$'
locale3: db     'English/user remap',13,10,'$'
localetable:
        dw      locale0,locale1,locale2,locale3
infobase:
        dw      0
capsbase:
        dw      0
        end
