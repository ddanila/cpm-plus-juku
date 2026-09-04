; C12 runtime console configuration utility.
; Copyright (c) 2026 Danila Sukharev
; BSD-2-Clause; see ../LICENSE.

        include "rom-abi.inc"

BDOS            equ     0005h
CONOUT          equ     2
PRINT           equ     9
COMMAND_LENGTH  equ     080h
COMMAND_TEXT    equ     081h

        org     0100h

start:
        call    require_c12
        jc      unavailable
        lxi     h,COMMAND_TEXT
        shld    parse_pointer
        lda     COMMAND_LENGTH
        sta     parse_left
        call    next_token
        jc      show_status
        lxi     d,word_status
        call    token_equal
        jz      require_end_status
        lxi     d,word_default
        call    token_equal
        jz      do_default
        lxi     d,word_mode
        call    token_equal
        jz      select_mode
        lxi     d,word_charset
        call    token_equal
        jz      select_charset
        jmp     usage

require_end_status:
        call    require_end
        jnc     usage
        jmp     show_status

do_default:
        call    require_end
        jnc     usage
        mvi     a,JROMCONCONFIGDEFAULT
        call    JCGCONCONFIGADDR
        jc      failed
        jmp     show_status

select_mode:
        call    next_token
        jc      usage
        lxi     d,word_40
        call    token_equal
        mvi     a,0
        jz      set_mode
        lxi     d,word_53
        call    token_equal
        mvi     a,1
        jz      set_mode
        lxi     d,word_64
        call    token_equal
        mvi     a,2
        jz      set_mode
        lxi     d,word_80
        call    token_equal
        mvi     a,3
        jnz     usage
set_mode:
        sta     requested
        call    require_end
        jnc     usage
        call    query
        jc      failed
        lda     requested
        mov     b,a
        lda     active_bank
        mov     c,a
        mvi     a,JROMCONCONFIGSET
        call    JCGCONCONFIGADDR
        jc      failed
        jmp     show_status

select_charset:
        call    next_token
        jc      usage
        lxi     d,word_english
        call    token_equal
        mvi     a,0
        jz      set_charset
        lxi     d,word_estonian
        call    token_equal
        mvi     a,1
        jz      set_charset
        lxi     d,word_russian
        call    token_equal
        mvi     a,2
        jz      set_charset
        lxi     d,word_user
        call    token_equal
        mvi     a,3
        jnz     usage
set_charset:
        sta     requested
        call    require_end
        jnc     usage
        call    query
        jc      failed
        lda     active_mode
        mov     b,a
        lda     requested
        mov     c,a
        mvi     a,JROMCONCONFIGSET
        call    JCGCONCONFIGADDR
        jc      failed

show_status:
        call    query
        jc      failed
        lxi     d,title
        call    puts
        lxi     d,default_message
        call    puts
        lda     default_raw
        rrc
        ani     3
        call    print_mode
        lxi     d,separator
        call    puts
        lda     default_raw
        rrc
        rrc
        rrc
        ani     3
        call    print_bank
        lxi     d,raw_message
        call    puts
        lda     default_raw
        call    print_hex
        lxi     d,close_line
        call    puts
        lxi     d,active_message
        call    puts
        lda     active_mode
        call    print_mode
        lxi     d,separator
        call    puts
        lda     active_bank
        call    print_bank
        lxi     d,newline
        call    puts
        lxi     d,override_message
        call    puts
        lda     override_flags
        ani     JROMCONOVERRIDEVIDEO
        call    print_yes_no
        lxi     d,charset_override_message
        call    puts
        lda     override_flags
        ani     JROMCONOVERRIDELOCALE
        jmp     print_yes_no

query:
        mvi     a,JROMCONCONFIGQUERY
        call    JCGCONCONFIGADDR
        rc
        sta     default_raw
        mov     a,b
        sta     active_mode
        mov     a,c
        sta     active_bank
        mov     a,d
        sta     override_flags
        ora     a                       ; clear carry
        ret

require_c12:
        call    JCGGETINFOADDR
        mov     a,h
        cpi     0ffh
        jnz     require_c12_bad
        mov     a,l
        ora     a
        jnz     require_c12_bad
        mov     a,d
        ani     010h
        jz      require_c12_bad
        ora     a
        ret
require_c12_bad:
        stc
        ret

; Return carry set only when no non-space token remains.
require_end:
        jmp     next_token

; Copy one upper-case token to token_buffer and retain parser position.
next_token:
        lhld    parse_pointer
        lda     parse_left
        mov     b,a
next_skip:
        mov     a,b
        ora     a
        jz      next_none
        mov     a,m
        cpi     ' '
        jz      next_skip_one
        cpi     9
        jnz     next_copy_begin
next_skip_one:
        inx     h
        dcr     b
        jmp     next_skip
next_copy_begin:
        lxi     d,token_buffer
        mvi     c,11
next_copy:
        mov     a,b
        ora     a
        jz      next_done
        mov     a,m
        cpi     ' '
        jz      next_done
        cpi     9
        jz      next_done
        mov     a,c
        ora     a
        jz      next_too_long
        mov     a,m
        cpi     'a'
        jc      next_store
        cpi     'z'+1
        jnc     next_store
        sui     020h
next_store:
        stax    d
        inx     d
        inx     h
        dcr     b
        dcr     c
        jmp     next_copy
next_done:
        xra     a
        stax    d
        shld    parse_pointer
        mov     a,b
        sta     parse_left
        ora     a                       ; carry clear
        ret
next_too_long:
        ; Consume the remainder so it is a normal unknown token.
        inx     h
        dcr     b
        jmp     next_copy
next_none:
        shld    parse_pointer
        mov     a,b
        sta     parse_left
        stc
        ret

; Z means token_buffer exactly equals the zero-terminated DE string.
token_equal:
        lxi     h,token_buffer
token_equal_loop:
        ldax    d
        cmp     m
        rnz
        ora     a
        rz
        inx     d
        inx     h
        jmp     token_equal_loop

print_mode:
        add     a
        mov     e,a
        mvi     d,0
        lxi     h,mode_table
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        jmp     puts

print_bank:
        add     a
        mov     e,a
        mvi     d,0
        lxi     h,bank_table
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        jmp     puts

print_yes_no:
        ora     a
        lxi     d,no_message
        jz      puts
        lxi     d,yes_message
        jmp     puts

print_hex:
        push    psw
        rrc
        rrc
        rrc
        rrc
        ani     00fh
        call    print_nibble
        pop     psw
        ani     00fh
print_nibble:
        adi     '0'
        cpi     '9'+1
        jc      print_digit
        adi     'A'-'9'-1
print_digit:
        mov     e,a
        mvi     c,CONOUT
        jmp     BDOS

puts:
        mvi     c,PRINT
        jmp     BDOS

usage:
        lxi     d,usage_message
        jmp     puts
unavailable:
        lxi     d,unavailable_message
        jmp     puts
failed:
        lxi     d,failed_message
        jmp     puts

title:  db      13,10,'Juku Console 1.0',13,10,'$'
default_message: db 'S21 default: $'
active_message: db  'Active: $'
raw_message: db     ' (raw $'
close_line: db      ')',13,10,'$'
separator: db       ' / $'
override_message: db 'Override: video=$'
charset_override_message: db '  charset=$'
yes_message: db     'yes',13,10,'$'
no_message: db      'no',13,10,'$'
newline: db         13,10,'$'
usage_message:
        db      'Usage: CONSOLE STATUS',13,10
        db      '       CONSOLE MODE 40|53|64|80',13,10
        db      '       CONSOLE CHARSET ENGLISH|ESTONIAN|RUSSIAN|USER',13,10
        db      '       CONSOLE DEFAULT',13,10,'$'
unavailable_message:
        db      'C12 ROM ABI 1.5 runtime console service unavailable.',13,10,'$'
failed_message:
        db      'Runtime console request failed; state unchanged.',13,10,'$'

mode_40: db     '40x24','$'
mode_53: db     '53x24','$'
mode_64: db     '64x20','$'
mode_80: db     '80x24','$'
mode_table: dw  mode_40,mode_53,mode_64,mode_80
bank_english: db 'English','$'
bank_estonian: db 'Estonian','$'
bank_russian: db 'Russian CP866','$'
bank_user: db  'English/user remap','$'
bank_table: dw  bank_english,bank_estonian,bank_russian,bank_user

word_status: db    'STATUS',0
word_default: db   'DEFAULT',0
word_mode: db      'MODE',0
word_charset: db   'CHARSET',0
word_40: db        '40',0
word_53: db        '53',0
word_64: db        '64',0
word_80: db        '80',0
word_english: db   'ENGLISH',0
word_estonian: db  'ESTONIAN',0
word_russian: db   'RUSSIAN',0
word_user: db      'USER',0

parse_pointer: dw  0
parse_left: db     0
token_buffer: ds   12
requested: db      0
default_raw: db    0
active_mode: db    0
active_bank: db    0
override_flags: db 0

        end
