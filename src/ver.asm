BDOS            equ     0005h
PRINT           equ     9
VERSION         equ     12

        org     0100h

        mvi     c,VERSION
        call    BDOS
        mov     a,l
        rrc
        rrc
        rrc
        rrc
        ani     0fh
        adi     '0'
        sta     major
        mov     a,l
        ani     0fh
        adi     '0'
        sta     minor
        lxi     d,message
        mvi     c,PRINT
        jmp     BDOS

message:
        db      'CP/M Plus '
major:  db      '0'
        db      '.'
minor:  db      '0'
        db      ' for Juku',13,10,'$'
