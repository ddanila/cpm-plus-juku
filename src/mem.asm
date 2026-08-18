; Bounded, read-only CP/M memory viewer.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
PRINT           equ     9
CONOUT          equ     2
TAIL            equ     0080h
MAXLEN          equ     040h

        org     0100h

start:
        lxi     d,title
        call    puts
        lda     TAIL
        mov     b,a
        lxi     h,TAIL+1
        call    skipspaces
        mov     a,b
        cpi     4
        jc      usage
        call    parsebyte
        jc      usage
        sta     address+1
        call    parsebyte
        jc      usage
        sta     address
        call    skipspaces
        mov     a,b
        ora     a
        jnz     parselen
        mvi     a,16
        jmp     lengthready
parselen:
        cpi     2
        jc      usage
        call    parsebyte
        jc      usage
        push    psw
        call    skipspaces
        mov     a,b
        ora     a
        jnz     badpop
        pop     psw
lengthready:
        ora     a
        jz      usage
        cpi     MAXLEN+1
        jnc     usage
        sta     remaining

nextrow:
        lda     remaining
        ora     a
        rz
        cpi     16
        jc      shortrow
        mvi     a,16
shortrow:
        sta     rowlen
        lhld    address
        shld    rowstart
        call    printword
        mvi     a,':'
        call    printchar
        mvi     a,' '
        call    printchar

        lhld    rowstart
        lda     rowlen
        mov     b,a
hexloop:
        mov     a,m
        push    b
        push    h
        call    printbyte
        mvi     a,' '
        call    printchar
        pop     h
        pop     b
        inx     h
        dcr     b
        jnz     hexloop
        lda     rowlen
        mov     b,a
padloop:
        mov     a,b
        cpi     16
        jz      asciistart
        push    b
        mvi     a,' '
        call    printchar
        call    printchar
        call    printchar
        pop     b
        inr     b
        jmp     padloop

asciistart:
        mvi     a,'|'
        call    printchar
        lhld    rowstart
        lda     rowlen
        mov     b,a
asciiloop:
        mov     a,m
        cpi     020h
        jc      dot
        cpi     07fh
        jc      asciiout
dot:
        mvi     a,'.'
asciiout:
        push    b
        push    h
        call    printchar
        pop     h
        pop     b
        inx     h
        dcr     b
        jnz     asciiloop
        mvi     a,'|'
        call    printchar
        lxi     d,newline
        call    puts
        lda     rowlen
        mov     e,a
        mvi     d,0
        lhld    address
        dad     d
        shld    address
        lda     rowlen
        mov     b,a
        lda     remaining
        sub     b
        sta     remaining
        jmp     nextrow

badpop:
        pop     psw
usage:
        lxi     d,usagemsg
        jmp     puts

; Skip spaces. HL is the command pointer and B is the remaining length.
skipspaces:
        mov     a,b
        ora     a
        rz
        mov     a,m
        cpi     13
        jz      tailend
        cpi     ' '
        rnz
        inx     h
        dcr     b
        jmp     skipspaces
tailend:
        mvi     b,0
        ret

; Parse exactly two hexadecimal characters. Returns A=byte, carry on error.
parsebyte:
        mov     a,b
        cpi     2
        jc      parsebad
        mov     a,m
        call    hexnibble
        jc      parsebad
        rlc
        rlc
        rlc
        rlc
        sta     highnibble
        inx     h
        dcr     b
        mov     a,m
        call    hexnibble
        jc      parsebad
        mov     e,a
        lda     highnibble
        ora     e
        inx     h
        dcr     b
        ora     a
        ret
parsebad:
        stc
        ret

hexnibble:
        cpi     '0'
        jc      nibblebad
        cpi     '9'+1
        jc      isdigit
        ani     05fh
        cpi     'A'
        jc      nibblebad
        cpi     'F'+1
        jnc     nibblebad
        sui     'A'-10
        ora     a
        ret
isdigit:
        sui     '0'
        ora     a
        ret
nibblebad:
        stc
        ret

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
        db      'Juku MEM 1.0 (read-only, max 40h bytes)',13,10,'$'
usagemsg:
        db      'Usage: MEM address [length], four/two hex digits',13,10,'$'
newline:
        db      13,10,'$'

address:
        dw      0
rowstart:
        dw      0
remaining:
        db      0
rowlen:
        db      0
highnibble:
        db      0

        end
