; Record-exact comparison of two CP/M files.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
TAIL            equ     0080h
OPEN            equ     15
READSEQ         equ     20
SETDMA          equ     26
PRINT           equ     9
CONOUT          equ     2

        org     0100h

start:
        lxi     d,title
        call    puts
        lda     TAIL
        sta     cmdleft
        lxi     h,TAIL+1
        shld    cmdptr
        lxi     d,fcb1
        call    parsefcb
        jc      usage
        lxi     d,fcb2
        call    parsefcb
        jc      usage
        lxi     d,fcb1
        mvi     c,OPEN
        call    BDOS
        inr     a
        jz      firstmissing
        lxi     d,fcb2
        mvi     c,OPEN
        call    BDOS
        inr     a
        jz      secondmissing
        lxi     h,0
        shld    record

readpair:
        lxi     d,dma1
        mvi     c,SETDMA
        call    BDOS
        lxi     d,fcb1
        mvi     c,READSEQ
        call    BDOS
        sta     eof1
        lxi     d,dma2
        mvi     c,SETDMA
        call    BDOS
        lxi     d,fcb2
        mvi     c,READSEQ
        call    BDOS
        sta     eof2
        lda     eof1
        ora     a
        jnz     firsteof
        lda     eof2
        ora     a
        jnz     secondshort
        lxi     h,dma1
        lxi     d,dma2
        mvi     b,128
comparebyte:
        ldax    d
        cmp     m
        jnz     bytediff
        inx     h
        inx     d
        dcr     b
        jnz     comparebyte
        lhld    record
        inx     h
        shld    record
        jmp     readpair

firsteof:
        lda     eof2
        ora     a
        jnz     same
        lxi     d,firstshortmsg
        jmp     lengthout
secondshort:
        lxi     d,secondshortmsg
lengthout:
        call    puts
        lhld    record
        call    printword
        lxi     d,newline
        jmp     puts

bytediff:
        mov     a,b
        sui     128
        cma
        inr     a
        sta     offset
        lxi     d,diffmsg
        call    puts
        lhld    record
        call    printword
        lxi     d,offsetmsg
        call    puts
        lda     offset
        call    printbyte
        lxi     d,newline
        jmp     puts

same:
        lxi     d,samemsg
        jmp     puts
usage:
        lxi     d,usagemsg
        jmp     puts
firstmissing:
        lxi     d,firstmsg
        jmp     puts
secondmissing:
        lxi     d,secondmsg
        jmp     puts

; Parse one command-tail filename into the 36-byte FCB at DE. This avoids the
; overlapping default FCBs at 005Ch/006Ch and accepts an optional A:..P:.
parsefcb:
        xra     a
        mvi     b,36
        push    d
clearfcb:
        stax    d
        inx     d
        dcr     b
        jnz     clearfcb
        pop     d
        push    d
        inx     d
        mvi     a,' '
        mvi     b,11
fillname:
        stax    d
        inx     d
        dcr     b
        jnz     fillname
        pop     d
        xchg
        shld    fcbbase
        xchg

        lhld    cmdptr
        lda     cmdleft
        mov     b,a
skipblank:
        mov     a,b
        ora     a
        jz      parsefail
        mov     a,m
        cpi     ' '
        jnz     checkdrive
        inx     h
        dcr     b
        jmp     skipblank

checkdrive:
        mov     a,b
        cpi     2
        jc      basename
        inx     h
        dcr     b
        mov     a,m
        cpi     ':'
        jnz     nodrive
        dcx     h
        inr     b
        mov     a,m
        call    uppercase
        cpi     'A'
        jc      parsefail
        cpi     'P'+1
        jnc     parsefail
        sui     'A'-1
        push    h
        lhld    fcbbase
        mov     m,a
        pop     h
        inx     h
        inx     h
        dcr     b
        dcr     b
        jmp     basename
nodrive:
        dcx     h
        inr     b

basename:
        push    h
        lhld    fcbbase
        inx     h
        xchg
        pop     h
        mvi     c,0
baseloop:
        mov     a,b
        ora     a
        jz      basenameend
        mov     a,m
        cpi     ' '
        jz      basenameend
        cpi     13
        jz      basenameend
        cpi     '.'
        jz      extension
        mov     a,c
        cpi     8
        jnc     parsefail
        mov     a,m
        call    filenamechar
        jc      parsefail
        stax    d
        inx     d
        inx     h
        dcr     b
        inr     c
        jmp     baseloop

extension:
        mov     a,c
        ora     a
        jz      parsefail
        inx     h
        dcr     b
        push    h
        lhld    fcbbase
        lxi     d,9
        dad     d
        xchg
        pop     h
        mvi     c,0
extloop:
        mov     a,b
        ora     a
        jz      parsed
        mov     a,m
        cpi     ' '
        jz      parsed
        cpi     13
        jz      parsed
        mov     a,c
        cpi     3
        jnc     parsefail
        mov     a,m
        call    filenamechar
        jc      parsefail
        stax    d
        inx     d
        inx     h
        dcr     b
        inr     c
        jmp     extloop

basenameend:
        mov     a,c
        ora     a
        jz      parsefail
parsed:
        shld    cmdptr
        mov     a,b
        sta     cmdleft
        ora     a
        ret

filenamechar:
        call    uppercase
        cpi     021h
        jc      charbad
        cpi     07fh
        jnc     charbad
        cpi     ':'
        jz      charbad
        cpi     '='
        jz      charbad
        ora     a
        ret
charbad:
        stc
        ret
uppercase:
        cpi     'a'
        rc
        cpi     'z'+1
        rnc
        ani     05fh
        ret
parsefail:
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
        db      'Juku CMP 1.0',13,10,'$'
samemsg:
        db      'CMP: files are identical',13,10,'$'
firstshortmsg:
        db      'CMP: first file is shorter at record $'
secondshortmsg:
        db      'CMP: second file is shorter at record $'
diffmsg:
        db      'CMP: difference at record $'
offsetmsg:
        db      ' offset $'
usagemsg:
        db      'Usage: CMP file1 file2',13,10,'$'
firstmsg:
        db      'CMP: first file not found',13,10,'$'
secondmsg:
        db      'CMP: second file not found',13,10,'$'
newline:
        db      13,10,'$'

record:
        dw      0
eof1:   db      0
eof2:   db      0
offset: db      0
cmdptr: dw      0
cmdleft:
        db      0
fcbbase:
        dw      0
fcb1:   ds      36
fcb2:   ds      36
dma1:   ds      128
dma2:   ds      128

        end
