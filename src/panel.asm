; Compact pseudographic status panel for Juku CP/M Plus.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
CONOUT          equ     2
DIRECTIO        equ     6
DIRECTBIOS      equ     50

        org     0100h

start:
        call    read_info
        jc      unavailable
        lda     video_mode
        cpi     3
        jnz     wrong_mode
        call    fill_values
        call    select_locale
        call    select_borders

        mvi     a,01bh
        call    putc
        mvi     a,'L'
        call    putc
        call    top_row
        lxi     d,title
        call    interior_row
        call    separator_row
        lxi     d,system_heading
        call    interior_row
        lxi     d,system_line
        call    interior_row
        lxi     d,tpa_line
        call    interior_row
        lxi     d,rom_line
        call    interior_row
        call    separator_row
        lxi     d,console_heading
        call    interior_row
        lxi     d,s21_line
        call    interior_row
        lhld    locale_line
        xchg
        call    interior_row
        lxi     d,empty
        call    interior_row
        call    separator_row
        lxi     d,network_heading
        call    interior_row
        lxi     d,netdisk_line
        call    interior_row
        lxi     d,boot_line
        call    interior_row
        lxi     d,reconnect_line
        call    interior_row
        lxi     d,empty
        call    interior_row
        call    separator_row
        lxi     d,safety_heading
        call    interior_row
        lxi     d,writes_line
        call    interior_row
        lxi     d,press_line
        call    interior_row
        lxi     d,empty
        call    interior_row
        call    bottom_row

wait_key:
        mvi     c,DIRECTIO
        mvi     e,0ffh
        call    BDOS
        ora     a
        jz      wait_key

        mvi     a,01bh
        call    putc
        mvi     a,'L'
        call    putc
        lxi     d,done
        call    puts0
        ret

unavailable:
        lxi     d,unavailable_text
        call    puts0
        ret
wrong_mode:
        lxi     d,wrong_mode_text
        call    puts0
        ret

; CP/M 3 BDOS function 50 calls BIOS USERF (vector 30). The returned JNS1
; block is the shared status ABI; PANEL never reads Juku hardware directly.
read_info:
        mvi     a,30
        sta     bios_function
        xra     a
        sta     bios_a
        lxi     h,0
        shld    bios_bc
        shld    bios_de
        shld    bios_hl
        lxi     d,bios_function
        mvi     c,DIRECTBIOS
        call    BDOS
        ora     a
        jnz     info_bad
        mov     a,m
        cpi     'J'
        jnz     info_bad
        inx     h
        mov     a,m
        cpi     'N'
        jnz     info_bad
        inx     h
        mov     a,m
        cpi     'S'
        jnz     info_bad
        inx     h
        mov     a,m
        cpi     '1'
        jnz     info_bad
        dcx     h
        dcx     h
        dcx     h
        shld    infobase
        lxi     d,8
        dad     d
        mov     a,m
        sta     raw_s21
        inx     h
        mov     a,m
        ani     3
        sta     video_mode
        ora     a                       ; clear carry
        ret
info_bad:
        stc
        ret

fill_values:
        lda     raw_s21
        lxi     h,s21_value
        call    hex_into
        lhld    infobase
        lxi     d,26
        dad     d
        mov     a,m
        lxi     h,abi_major
        call    hex_into
        lhld    infobase
        lxi     d,27
        dad     d
        mov     a,m
        lxi     h,abi_minor
        call    hex_into
        lhld    infobase
        lxi     d,23
        dad     d
        mov     a,m
        lxi     h,boot_stage
        call    hex_into
        lhld    infobase
        lxi     d,24
        dad     d
        mov     a,m
        lxi     h,boot_retries
        call    hex_into
        lhld    infobase
        lxi     d,22
        dad     d
        mov     a,m
        lxi     h,reconnects
        call    hex_into
        lhld    infobase
        lxi     d,19
        dad     d
        mov     a,m
        lxi     h,disk_status
        call    hex_into
        ret

select_locale:
        lda     raw_s21
        rrc
        rrc
        rrc
        ani     3
        add     a
        mov     e,a
        mvi     d,0
        lxi     h,locale_lines
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        xchg
        shld    locale_line
        ret

; The exact C6 font supplies the connected single-line CP437 cells.  C4h is
; also Estonian A-diaeresis, however, so locale 1 deliberately uses an ASCII
; frame instead of corrupting either the letter or the border.
select_borders:
        lda     raw_s21
        rrc
        rrc
        rrc
        ani     3
        cpi     1
        rnz
        mvi     a,'+'
        sta     border_top_left
        sta     border_top_right
        sta     border_bottom_left
        mvi     a,'-'
        sta     border_horizontal
        mvi     a,'|'
        sta     border_vertical
        ret

; A = byte, HL = first of two writable hexadecimal characters.
hex_into:
        mov     b,a
        rrc
        rrc
        rrc
        rrc
        ani     0fh
        call    hex_digit
        mov     m,a
        inx     h
        mov     a,b
        ani     0fh
        call    hex_digit
        mov     m,a
        ret
hex_digit:
        adi     '0'
        cpi     '9'+1
        rc
        adi     'A'-'9'-1
        ret

top_row:
        lda     border_top_left
        call    putc
        mvi     b,78
top_fill:
        lda     border_horizontal
        call    putc
        dcr     b
        jnz     top_fill
        lda     border_top_right
        jmp     putc

separator_row:
        lxi     d,empty
        jmp     interior_row

; DE -> zero-terminated content; emit one complete 80-column bordered row.
interior_row:
        lda     border_vertical
        call    putc
        mvi     b,78
interior_text:
        ldax    d
        ora     a
        jz      interior_spaces
        call    putc
        inx     d
        dcr     b
        jnz     interior_text
        jmp     interior_edge
interior_spaces:
        mvi     a,' '
        call    putc
        dcr     b
        jnz     interior_spaces
interior_edge:
        lda     border_vertical
        jmp     putc

; Leave the last cell for the blinking cursor, matching VIDTEST's stable
; non-scrolling full-screen convention.
bottom_row:
        lda     border_bottom_left
        call    putc
        mvi     b,67
bottom_fill:
        lda     border_horizontal
        call    putc
        dcr     b
        jnz     bottom_fill
        lxi     d,ready
        jmp     puts0

puts0:
        ldax    d
        ora     a
        rz
        call    putc
        inx     d
        jmp     puts0

; A = byte. Preserve the row/string loop registers around BDOS.
putc:
        push    b
        push    d
        push    h
        mov     e,a
        mvi     c,CONOUT
        call    BDOS
        pop     h
        pop     d
        pop     b
        ret

title:  db      ' Juku Control Panel 1.0',0
system_heading:
        db      ' System',0
system_line:
        db      ' CP/M Plus 3.1          CPU: strict Intel 8080',0
tpa_line:
        db      ' TPA: 0100h-99FFh       39168 bytes',0
rom_line:
        db      ' ROM ABI: '
abi_major:
        db      '00'
        db      '.'
abi_minor:
        db      '00'
        db      '             network-first C6',0
console_heading:
        db      ' Console',0
s21_line:
        db      ' S21: '
s21_value:
        db      '00'
        db      'h               mode: 80x24',0
locale0:
        db      ' Locale: English        local I/O authoritative',0
locale1:
        db      ' Locale: Estonian       local I/O authoritative',0
locale2:
        db      ' Locale: Russian CP866  local I/O authoritative',0
locale3:
        db      ' Locale: English/remap  local I/O authoritative',0
locale_lines:
        dw      locale0,locale1,locale2,locale3
network_heading:
        db      ' Network',0
netdisk_line:
        db      ' NetDisk v3             serial: 19200 8N1',0
boot_line:
        db      ' Boot stage: '
boot_stage:
        db      '00'
        db      'h        retries: '
boot_retries:
        db      '00'
        db      'h',0
reconnect_line:
        db      ' Reconnects: '
reconnects:
        db      '00'
        db      'h         disk status: '
disk_status:
        db      '00'
        db      'h',0
safety_heading:
        db      ' Safety',0
writes_line:
        db      ' Writes: synchronous    recovery: C4/C5 retained',0
press_line:
        db      ' Press any key to return to CP/M',0
empty:  db      0
ready:  db      'PANEL READY',0
done:   db      13,10,'Juku Panel 1.0 DONE',13,10,0
unavailable_text:
        db      13,10,'PANEL requires the native JNS1 BIOS.',13,10,0
wrong_mode_text:
        db      13,10,'PANEL requires S21 video mode 3 (80x24).',13,10,0

bios_function: db      30
bios_a:        db      0
bios_bc:       dw      0
bios_de:       dw      0
bios_hl:       dw      0
infobase:      dw      0
raw_s21:       db      0
video_mode:    db      0
locale_line:   dw      locale0
border_top_left:
                db      0dah
border_top_right:
                db      0bfh
border_bottom_left:
                db      0c0h
border_horizontal:
                db      0c4h
border_vertical:
                db      0b3h

        end
