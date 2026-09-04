; Juku CP/M Plus configuration and resident-system report.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
PRINT           equ     9
PPI0_PORT_C     equ     006h
.ifdef ROM_ABI_C12
        include "rom-abi.inc"
.endif

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
        lhld    infobase
        lxi     d,27
        dad     d
        mov     a,m
        cpi     3
        lxi     d,mapmsg
        jc      printmap
        lxi     d,mapmsgc8
printmap:
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

.ifdef ROM_ABI_C12
        mvi     a,JROMCONCONFIGQUERY
        call    JCGCONCONFIGADDR
        jc      console_state_unavailable
        sta     console_default
        mov     a,b
        sta     console_active_mode
        mov     a,c
        sta     console_active_bank
        mov     a,d
        sta     console_override_flags

        lxi     d,activevideomsg
        call    puts
        lda     console_active_mode
        push    psw
        call    printhex
        pop     psw
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

        lxi     d,activecharsetmsg
        call    puts
        lda     console_active_bank
        push    psw
        call    printhex
        pop     psw
        push    psw
        lxi     d,valuespace
        call    puts
        pop     psw
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

        lxi     d,videooverridemsg
        call    puts
        lda     console_override_flags
        ani     JROMCONOVERRIDEVIDEO
        call    printyesno
        lxi     d,charsetoverridemsg
        call    puts
        lda     console_override_flags
        ani     JROMCONOVERRIDELOCALE
        call    printyesno
        jmp     console_state_done
console_state_unavailable:
        lxi     d,consolestateunavailablemsg
        call    puts
console_state_done:
.endif

.ifdef ROM_ABI_C10
        ; C9 could publish a valid geometry while PC7/POF still suppressed
        ; every physical pixel. Report the complete latch and its picture
        ; state directly; this is digital state, not an analog X7 self-test.
        lxi     d,pofportmsg
        call    puts
        in      PPI0_PORT_C
        sta     pofportc
        call    printhex
        lxi     d,pofstatemsg
        call    puts
        lda     pofportc
        ani     080h
        lxi     d,pofreleasedmsg
        jz      status_pof_print
        lxi     d,pofsuppressedmsg
status_pof_print:
        call    puts
.endif

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

.ifdef ROM_ABI_C9
        ; JNS1 v1.2 appends the ABI 1.4 host flags and retained failure
        ; operation without moving any field consumed by Status 1.3.
        lhld    infobase
        lxi     d,5
        dad     d
        mov     a,m                     ; JNS1 schema minor
        cpi     2
        jc      status_host14_done
        inx     h
        mov     a,m                     ; record length
        cpi     30
        jc      status_host14_done
        lxi     d,hostflagsmsg
        call    puts
        lhld    infobase
        lxi     d,28
        dad     d
        mov     a,m
        call    printhex
        push    h
        lxi     d,hostlastopmsg
        call    puts
        pop     h
        inx     h
        mov     a,m
        call    printhex
        lxi     d,newline
        call    puts
        lxi     d,hostreasonmsg
        call    puts
        lhld    infobase
        lxi     d,21
        dad     d
        mov     a,m
        cpi     7
        jnc     status_host_reason_unknown
        add     a
        mov     e,a
        mvi     d,0
        lxi     h,hostreasontable
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        call    puts
        jmp     status_host14_done
status_host_reason_unknown:
        lxi     d,hostreasonunknown
        call    puts
status_host14_done:
.endif

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

.ifdef ROM_ABI_C12
printyesno:
        ora     a
        lxi     d,nomsg
        jz      puts
        lxi     d,yesmsg
        jmp     puts
.endif

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

.ifdef ROM_ABI_C12
title:  db      13,10,'Juku Status 1.6',13,10,'$'
.else
.ifdef ROM_ABI_C10
title:  db      13,10,'Juku Status 1.5',13,10,'$'
.else
.ifdef ROM_ABI_C9
title:  db      13,10,'Juku Status 1.4',13,10,'$'
.else
title:  db      13,10,'Juku Status 1.3',13,10,'$'
.endif
.endif
.endif
identity:
        db      'System: CP/M Plus 3.1, native profile 1',13,10
        db      'Transport: NetDisk v3, 19200 baud, N4 services',13,10,'$'
rommsg: db      'ROM: Juku ABI $'
dotmsg: db      '.$'
romsuffix:
        db      ' network-first',13,10,'$'
mapmsg:
        db      'Map: TPA 0100-99FF, loader 9A00-9CFF',13,10
        db      '     BDOS 9D00-BB9B, SCB BB9C-BBFF, BIOS BC00-BFFF',13,10
        db      '     adapter/state C000-D5FF, ROM gate/work D600-D7FF',13,10
        db      '     framebuffer D800-FD7F (mode 3 RAM)',13,10,'$'
mapmsgc8:
        db      'Map: TPA 0100-9BFF, loader 9C00-9EFF',13,10
        db      '     BDOS 9F00-BD9B, SCB BD9C-BDFF, BIOS BE00-C1FF',13,10
        db      '     adapter/state C200-D5FF, ROM gate/work D600-D7FF',13,10
        db      '     framebuffer D800-FD7F (mode 3 RAM)',13,10,'$'
s21msg: db      'S21 raw: $'
.ifdef ROM_ABI_C12
videomsg:
        db      '  default video: $'
localemsg:
        db      'Default charset: $'
activevideomsg:
        db      'Active video: $'
activecharsetmsg:
        db      'Active charset: $'
videooverridemsg:
        db      'Video override: $'
charsetoverridemsg:
        db      'Charset override: $'
valuespace:
        db      ' $'
yesmsg: db      'yes',13,10,'$'
nomsg:  db      'no',13,10,'$'
consolestateunavailablemsg:
        db      'Runtime console state unavailable.',13,10,'$'
.else
videomsg:
        db      '  video: $'
localemsg:
        db      'Locale: $'
.endif
.ifdef ROM_ABI_C10
pofportmsg:
        db      'PPI0 Port C: $'
pofstatemsg:
        db      '  POF: $'
pofreleasedmsg:
        db      'released (picture enabled)',13,10,'$'
pofsuppressedmsg:
        db      'asserted (pixels suppressed)',13,10,'$'
.endif
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
.ifdef ROM_ABI_C9
hostflagsmsg:
        db      'N4 state flags: $'
hostlastopmsg:
        db      '  last operation: $'
hostreasonmsg:
        db      'N4 failure reason: $'
hostreason0: db 'none',13,10,'$'
hostreason1: db 'transmitter timeout',13,10,'$'
hostreason2: db 'receive timeout',13,10,'$'
hostreason3: db 'synchronization budget exhausted',13,10,'$'
hostreason4: db 'sequence mismatch',13,10,'$'
hostreason5: db 'reply integrity mismatch',13,10,'$'
hostreason6: db 'host status rejected/unsupported',13,10,'$'
hostreasonunknown: db 'unknown nonzero reason',13,10,'$'
hostreasontable:
        dw      hostreason0,hostreason1,hostreason2,hostreason3
        dw      hostreason4,hostreason5,hostreason6
.endif
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
.ifdef ROM_ABI_C10
pofportc:
        db      0
.endif
.ifdef ROM_ABI_C12
console_default:
        db      0
console_active_mode:
        db      0
console_active_bank:
        db      0
console_override_flags:
        db      0
.endif
        end
