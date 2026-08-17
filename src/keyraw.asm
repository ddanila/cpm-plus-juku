; Raw Juku keyboard matrix reporter for ROM ABI 1.2.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

        include "rom-abi.inc"

BDOS            equ     0005h
CONOUT          equ     2
PRINT           equ     9
EVENT_LIMIT     equ     128

        org     0100h

start:
        call    JCGGETINFOADDR
        mov     a,d
        ani     008h                    ; JROMFKEYRAW high byte
        jz      unavailable
        lxi     d,banner
        call    puts
        mvi     a,0ffh
        sta     last_column
        mvi     a,EVENT_LIMIT
        sta     remaining

scan:
        call    JCGKEYRAWADDR
        jc      released
        sta     column
        mov     a,b
        sta     row_sample
        lda     last_column
        mov     c,a
        lda     column
        cmp     c
        jnz     changed
        lda     last_sample
        mov     c,a
        lda     row_sample
        cmp     c
        jz      scan
changed:
        lda     column
        sta     last_column
        lda     row_sample
        sta     last_sample
        lxi     d,column_text
        call    puts
        lda     column
        call    print_hex
        lxi     d,row_text
        call    puts
        lda     row_sample
        call    print_hex
        lxi     d,newline
        call    puts

        ; ESC is column 3, encoder input 4 (raw low nibble 06h).
        lda     column
        cpi     3
        jnz     count_event
        lda     row_sample
        ani     00fh
        cpi     006h
        jz      done
count_event:
        lda     remaining
        dcr     a
        sta     remaining
        jnz     scan
        jmp     done

released:
        mvi     a,0ffh
        sta     last_column
        jmp     scan

unavailable:
        lxi     d,no_service
        call    puts
        ret
done:
        lxi     d,finished
        call    puts
        ret

puts:
        mvi     c,PRINT
        jmp     BDOS

print_hex:
        push    psw
        rrc
        rrc
        rrc
        rrc
        call    print_nibble
        pop     psw
print_nibble:
        ani     00fh
        adi     '0'
        cpi     '9'+1
        jc      print_character
        adi     'A'-'9'-1
print_character:
        mov     e,a
        mvi     c,CONOUT
        jmp     BDOS

banner:
        db      13,10,'Juku Keyraw 1.0 - ROM ABI 1.2 matrix events',13,10
        db      'ESC exits. PB bits include CTRL/SHIFT and encoder row.',13,10,'$'
column_text:
        db      'RAW COL=','$'
row_text:
        db      ' PB=','$'
newline:
        db      13,10,'$'
no_service:
        db      'KEYRAW requires Juku ROM ABI 1.2 raw-keyboard service.',13,10,'$'
finished:
        db      'Juku Keyraw 1.0 DONE',13,10,'$'
column:
        db      0
row_sample:
        db      0
last_column:
        db      0ffh
last_sample:
        db      0ffh
remaining:
        db      0

        end
