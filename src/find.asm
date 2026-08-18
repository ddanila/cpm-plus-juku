; Case-insensitive, token-based line search for CP/M text files.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
FCB             equ     005ch
TAIL            equ     0080h
OPEN            equ     15
READSEQ         equ     20
SETDMA          equ     26
PRINT           equ     9
CONOUT          equ     2
MAXPATTERN      equ     31
MAXLINE         equ     120

        org     0100h

start:
        lxi     d,title
        call    puts
        call    getpattern
        jc      usage
        lxi     d,FCB
        mvi     c,OPEN
        call    BDOS
        inr     a
        jz      nofile
        xra     a
        sta     linelen
        sta     matches

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
        cpi     13
        jz      nextbyte
        cpi     10
        jz      endline
        push    b
        push    h
        mov     e,a
        lda     linelen
        cpi     MAXLINE
        jnc     restored
        mov     c,a
        mvi     b,0
        lxi     h,line
        dad     b
        mov     m,e
        lda     linelen
        inr     a
        sta     linelen
restored:
        pop     h
        pop     b
        jmp     nextbyte
endline:
        push    b
        push    h
        call    checkline
        xra     a
        sta     linelen
        pop     h
        pop     b
nextbyte:
        inx     h
        dcr     b
        jnz     byteloop
        jmp     readnext

finished:
        call    checkline
        lxi     d,result
        call    puts
        lda     matches
        call    printbyte
        lxi     d,newline
        jmp     puts

; Parse FIND filename token from the command tail. The CCP has already made
; the filename FCB; only the second whitespace-delimited token is needed.
getpattern:
        lda     TAIL
        mov     b,a
        lxi     h,TAIL+1
        call    skipspaces
skipfile:
        mov     a,b
        ora     a
        jz      parsebad
        mov     a,m
        cpi     ' '
        jz      afterfile
        cpi     13
        jz      parsebad
        inx     h
        dcr     b
        jmp     skipfile
afterfile:
        call    skipspaces
        mov     a,b
        ora     a
        jz      parsebad
        mvi     c,0
patternloop:
        mov     a,b
        ora     a
        jz      patternend
        mov     a,m
        cpi     ' '
        jz      patternend
        cpi     13
        jz      patternend
        mov     a,c
        cpi     MAXPATTERN
        jnc     parsebad
        mov     a,m
        call    uppercase
        push    h
        mov     e,c
        mvi     d,0
        lxi     h,pattern
        dad     d
        mov     m,a
        pop     h
        inx     h
        dcr     b
        inr     c
        jmp     patternloop
patternend:
        mov     a,c
        ora     a
        jz      parsebad
        sta     patternlen
        ora     a
        ret
parsebad:
        stc
        ret
skipspaces:
        mov     a,b
        ora     a
        rz
        mov     a,m
        cpi     ' '
        rnz
        inx     h
        dcr     b
        jmp     skipspaces

checkline:
        lda     linelen
        mov     b,a
        lda     patternlen
        mov     c,a
        mov     a,b
        sub     c
        rc
        inr     a
        sta     searchleft
        lxi     h,line
        shld    searchptr
searchnext:
        lhld    searchptr
        lxi     d,pattern
        lda     patternlen
        mov     c,a
searchchars:
        ldax    d
        sta     expected
        mov     a,m
        call    uppercase
        push    h
        lxi     h,expected
        cmp     m
        pop     h
        jnz     nomatch
        inx     h
        inx     d
        dcr     c
        jnz     searchchars
        call    printline
        lda     matches
        inr     a
        sta     matches
        ret
nomatch:
        lhld    searchptr
        inx     h
        shld    searchptr
        lda     searchleft
        dcr     a
        sta     searchleft
        jnz     searchnext
        ret

printline:
        lxi     h,line
        lda     linelen
        mov     b,a
printlineloop:
        mov     a,b
        ora     a
        jz      printlinedone
        mov     a,m
        push    b
        push    h
        call    printchar
        pop     h
        pop     b
        inx     h
        dcr     b
        jmp     printlineloop
printlinedone:
        lxi     d,newline
        jmp     puts

uppercase:
        cpi     'a'
        rc
        cpi     'z'+1
        rnc
        ani     05fh
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
        db      'Juku FIND 1.0 (case-insensitive)',13,10,'$'
result:
        db      'FIND: $'
usagemsg:
        db      'Usage: FIND textfile token',13,10,'$'
nofilemsg:
        db      'FIND: file not found',13,10,'$'
newline:
        db      13,10,'$'

patternlen:
        db      0
pattern:
        ds      MAXPATTERN
linelen:
        db      0
line:
        ds      MAXLINE
matches:
        db      0
searchleft:
        db      0
searchptr:
        dw      0
expected:
        db      0
dma:
        ds      128

        end
