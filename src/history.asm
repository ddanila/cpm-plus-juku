; One-entry command-history inspector for the Juku CP/M 3 CCP extension.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
PRINT           equ     9
CONOUT          equ     2
TAIL            equ     0080h

HISTMAGIC0      equ     0d571h
HISTMAGIC1      equ     0d572h
HISTLEN         equ     0d573h
HISTDATA        equ     0d574h
HISTMAX         equ     76

        org     0100h

start:
        lxi     d,title
        call    puts
        lda     TAIL
        ora     a
        jz      show
        mov     b,a
        lxi     h,TAIL+1
skipspace:
        mov     a,b
        ora     a
        jz      show
        mov     a,m
        cpi     ' '
        jnz     option
        inx     h
        dcr     b
        jmp     skipspace

option:
        mov     a,m
        ani     05fh
        cpi     'C'
        jnz     usage
        dcr     b
        jz      clear
        inx     h
        mov     a,b
        cpi     4
        jnz     usage
        mov     a,m
        ani     05fh
        cpi     'L'
        jnz     usage
        inx     h
        mov     a,m
        ani     05fh
        cpi     'E'
        jnz     usage
        inx     h
        mov     a,m
        ani     05fh
        cpi     'A'
        jnz     usage
        inx     h
        mov     a,m
        ani     05fh
        cpi     'R'
        jnz     usage

clear:
        xra     a
        sta     HISTMAGIC0
        sta     HISTMAGIC1
        sta     HISTLEN
        lxi     d,cleared
        jmp     puts

show:
        lda     HISTMAGIC0
        cpi     'J'
        jnz     empty
        lda     HISTMAGIC1
        cpi     'H'
        jnz     empty
        lda     HISTLEN
        ora     a
        jz      empty
        cpi     HISTMAX+1
        jnc     empty
        lxi     d,last
        call    puts
        lda     HISTLEN
        mov     b,a
        lxi     h,HISTDATA
printloop:
        mov     e,m
        push    b
        push    h
        mvi     c,CONOUT
        call    BDOS
        pop     h
        pop     b
        inx     h
        dcr     b
        jnz     printloop
        lxi     d,repeat
        jmp     puts

empty:
        lxi     d,emptymsg
        jmp     puts
usage:
        lxi     d,usagemsg
        jmp     puts

puts:
        mvi     c,PRINT
        jmp     BDOS

title:
        db      'Juku History 1.0',13,10,'$'
last:
        db      'Last: $'
repeat:
        db      13,10,'Repeat with !!',13,10,'$'
emptymsg:
        db      'History is empty',13,10,'$'
cleared:
        db      'History cleared',13,10,'$'
usagemsg:
        db      'Usage: HIST [CLEAR]',13,10,'$'

        end
