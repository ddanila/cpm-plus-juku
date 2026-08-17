; Blind local-keyboard reporter for the Juku CP/M Plus bench.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
CONOUT          equ     2
DIRECT_IO       equ     6
PRINT           equ     9
KEY_LIMIT       equ     128

        org     0100h

start:
        lxi     d,banner
        call    puts
        mvi     a,KEY_LIMIT
        sta     remaining

wait_key:
        mvi     c,DIRECT_IO
        mvi     e,0ffh                 ; nonblocking input, no BDOS echo
        call    BDOS
        ora     a
        jz      wait_key
        sta     key_value

        lxi     d,key_prefix
        call    puts
        lda     key_value
        call    print_hex
        lda     key_value
        cpi     020h
        jc      key_line_done
        cpi     07fh
        jnc     key_line_done
        lxi     d,quote_open
        call    puts
        lda     key_value
        mov     e,a
        mvi     c,CONOUT
        call    BDOS
        lxi     d,quote_close
        call    puts

key_line_done:
        lxi     d,newline
        call    puts
        lda     key_value
        cpi     01bh                    ; ESC
        jz      done
        cpi     003h                    ; Ctrl-C under direct input
        jz      done
        lda     remaining
        dcr     a
        sta     remaining
        jnz     wait_key

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
        db      13,10,'Juku Keytest 1.0',13,10
        db      'Each local key is reported as KEY hh. '
        db      'ESC or Ctrl-C exits.',13,10
        db      'Juku Keytest 1.0 READY',13,10,'$'
key_prefix:
        db      'KEY ','$'
quote_open:
        db      ' ''','$'
quote_close:
        db      '''','$'
newline:
        db      13,10,'$'
finished:
        db      'Juku Keytest 1.0 DONE',13,10,'$'
remaining:
        db      0
key_value:
        db      0

        end
