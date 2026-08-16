; Target-side regression for the Juku native CP/M Plus BIOS services.
; Copyright (c) 2026 Danila Sukharev
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
PRINT           equ     9
SCBDATE         equ     0bbf4h

        org     0100h

start:
        mvi     a,1
        sta     stage
        mvi     a,20                   ; DEVTBL
        call    setvector
        call    bioscall
        mov     a,m
        cpi     'J'
        jnz     failed
        inx     h
        mov     a,m
        cpi     'U'
        jnz     failed

        mvi     a,2
        sta     stage
        mvi     a,24                   ; explicit successful FLUSH
        call    setvector
        mvi     a,0ffh
        call    bioscall
        ora     a
        jnz     failed

        mvi     a,3
        sta     stage
        mvi     a,23                   ; MULTIO count arrives in A
        call    setvector
        mvi     c,05ah                 ; prove C is not mistaken for count
        mvi     a,3
        call    bioscall

        mvi     a,30                   ; Juku USERF status block
        call    setvector
        mvi     c,0
        call    bioscall
        ora     a
        jnz     failed
        mov     a,m
        cpi     'J'
        jnz     failed
        lxi     d,10
        dad     d
        mov     a,m
        cpi     3
        jnz     failed

        mvi     a,4
        sta     stage
        call    initbuf
        mvi     a,25                   ; overlapping destination > source
        call    setvector
        lxi     d,buffer
        lxi     h,buffer+4
        lxi     b,16
        call    bioscall
        mov     a,b
        ora     c
        jnz     failed
        lxi     b,buffer+20
        mov     a,h
        cmp     b
        jnz     failed
        mov     a,l
        cmp     c
        jnz     failed
        lxi     b,buffer+16
        mov     a,d
        cmp     b
        jnz     failed
        mov     a,e
        cmp     c
        jnz     failed
        lxi     h,buffer+4
        mvi     b,16
        xra     a
checkback:
        cmp     m
        jnz     failed
        inr     a
        inx     h
        dcr     b
        jnz     checkback

        mvi     a,5
        sta     stage
        call    initbuf
        mvi     a,25                   ; overlapping destination < source
        call    setvector
        lxi     d,buffer+4
        lxi     h,buffer
        lxi     b,16
        call    bioscall
        lxi     h,buffer
        mvi     b,16
        mvi     a,4
checkforward:
        cmp     m
        jnz     failed
        inr     a
        inx     h
        dcr     b
        jnz     checkforward

        mvi     a,6
        sta     stage
        mvi     a,25                   ; zero count leaves pointers unchanged
        call    setvector
        lxi     d,buffer+7
        lxi     h,buffer+9
        lxi     b,0
        call    bioscall
        lxi     b,buffer+9
        mov     a,h
        cmp     b
        jnz     failed
        mov     a,l
        cmp     c
        jnz     failed
        lxi     b,buffer+7
        mov     a,d
        cmp     b
        jnz     failed
        mov     a,e
        cmp     c
        jnz     failed

        mvi     a,070h                 ; SET then GET optional host clock
        sta     stage
        lxi     h,04561h               ; 2026-08-17 in CP/M day format
        shld    SCBDATE
        mvi     a,012h
        sta     SCBDATE+2
        mvi     a,034h
        sta     SCBDATE+3
        xra     a
        sta     SCBDATE+4
        mvi     a,26
        call    setvector
        lxi     h,01357h
        lxi     d,02468h
        mvi     c,0ffh
        call    bioscall
        mvi     a,071h
        sta     stage
        mov     a,h
        cpi     013h
        jnz     failed
        mov     a,l
        cpi     057h
        jnz     failed
        mov     a,d
        cpi     024h
        jnz     failed
        mov     a,e
        cpi     068h
        jnz     failed
        xra     a
        sta     SCBDATE
        sta     SCBDATE+1
        sta     SCBDATE+2
        sta     SCBDATE+3
        sta     SCBDATE+4
        mvi     a,072h
        sta     stage
        mvi     c,0
        call    bioscall
        mvi     a,073h
        sta     stage
        lhld    SCBDATE
        mov     a,h
        cpi     045h
        jnz     failed
        mov     a,l
        cpi     061h
        jnz     failed
        lda     SCBDATE+2
        cpi     012h
        jnz     failed
        lda     SCBDATE+3
        cpi     034h
        jnz     failed
        lda     SCBDATE+4
        ora     a
        jnz     failed
        mvi     a,074h
        sta     stage
        mvi     a,30
        call    setvector
        mvi     c,0
        call    bioscall
        lxi     d,11
        dad     d
        mov     a,m                     ; last clock status
        ora     a
        jnz     failed
        inx     h
        mov     a,m                     ; successful clock calls, low byte
        cpi     2
        jnz     failed
        inx     h
        mov     a,m
        ora     a
        jnz     failed
        inx     h
        mov     a,m                     ; failed clock calls, low byte
        ora     a
        jnz     failed

        lxi     d,passed
        jmp     emit
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

initbuf:
        lxi     h,buffer
        mvi     b,32
        xra     a
initbuf1:
        mov     m,a
        inr     a
        inx     h
        dcr     b
        jnz     initbuf1
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

passed: db      'NATIVE: PASS',13,10,'$'
failedmsg:
        db      'NATIVE: FAIL stage $'
newline:db      13,10,'$'
stage:  db      0
buffer: ds      32

        end     start
