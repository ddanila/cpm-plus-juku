; Blind local-keyboard reporter for the Juku CP/M Plus bench.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
CONOUT          equ     2
DIRECT_IO       equ     6
PRINT           equ     9
KEY_LIMIT       equ     128
LINE_LIMIT      equ     64
COMMAND_TAIL    equ     0080h

        org     0100h

start:
        call    select_mode
        lxi     d,banner
        call    puts
        lda     buffered_mode
        ora     a
        jnz     buffered_start
        mvi     a,KEY_LIMIT
        sta     remaining

wait_key:
        mvi     c,DIRECT_IO
        mvi     e,0ffh                 ; nonblocking input, no BDOS echo
        call    BDOS
        ora     a
        jz      wait_key
        sta     key_value
        call    report_key
        lda     key_value
        cpi     01bh                    ; ESC
        jz      done
        cpi     003h                    ; Ctrl-C under direct input
        jz      done
        lda     remaining
        dcr     a
        sta     remaining
        jnz     wait_key
        jmp     done

report_key:
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
        jmp     puts

; Buffered mode is selected by KEYTEST B. It polls without producing output,
; stores a complete line, and reports only after Enter. This avoids making the
; observer itself stall the polled local keyboard between consecutive keys.
buffered_start:
        xra     a
        sta     line_count

buffered_wait:
        mvi     c,DIRECT_IO
        mvi     e,0ffh
        call    BDOS
        ora     a
        jz      buffered_wait
        sta     key_value
        mov     b,a
        lda     line_count
        mov     e,a
        mvi     d,0
        lxi     h,line_buffer
        dad     d
        mov     m,b
        lda     line_count
        inr     a
        sta     line_count
        mov     a,b
        cpi     01bh
        jz      buffered_finish
        cpi     003h
        jz      buffered_finish
        cpi     00dh
        jz      buffered_report
        lda     line_count
        cpi     LINE_LIMIT
        jc      buffered_wait

buffered_report:
        lxi     d,batch_prefix
        call    puts
        lda     line_count
        call    print_hex
        lxi     d,newline
        call    puts
        xra     a
        sta     line_index

buffered_report_next:
        lda     line_index
        mov     e,a
        mvi     d,0
        lxi     h,line_buffer
        dad     d
        mov     a,m
        sta     key_value
        call    report_key
        lda     line_index
        inr     a
        sta     line_index
        mov     b,a
        lda     line_count
        cmp     b
        jnz     buffered_report_next
        lda     key_value
        cpi     01bh
        jz      done
        cpi     003h
        jz      done
        lxi     d,batch_ready
        call    puts
        jmp     buffered_start

buffered_finish:
        jmp     buffered_report

done:
        lxi     d,finished
        call    puts
        ret

select_mode:
        xra     a
        sta     buffered_mode
        lda     COMMAND_TAIL
        ora     a
        rz
        lxi     h,COMMAND_TAIL+1
select_skip_space:
        mov     a,m
        inx     h
        cpi     ' '
        jz      select_skip_space
        ani     0dfh
        cpi     'B'
        rnz
        mvi     a,1
        sta     buffered_mode
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
        db      13,10,'Juku Keytest 1.1',13,10
        db      'KEYTEST reports each key; KEYTEST B buffers a line.',13,10
        db      'ESC or Ctrl-C exits.',13,10
        db      'Juku Keytest 1.1 READY',13,10,'$'
batch_prefix:
        db      'BATCH ','$'
batch_ready:
        db      'Juku Keytest 1.1 BUFFER READY',13,10,'$'
key_prefix:
        db      'KEY ','$'
quote_open:
        db      ' ''','$'
quote_close:
        db      '''','$'
newline:
        db      13,10,'$'
finished:
        db      'Juku Keytest 1.1 DONE',13,10,'$'
remaining:
        db      0
key_value:
        db      0
buffered_mode:
        db      0
line_count:
        db      0
line_index:
        db      0
line_buffer:
        ds      LINE_LIMIT

        end
