; Deterministic local-display acceptance page for Juku CP/M Plus.
; Copyright (c) 2026 Danila Sukharev
; Developed with OpenAI GPT-5.6 Sol assistance.
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     0005h
CONOUT          equ     2
DIRECTIO        equ     6
DIRECTBIOS      equ     50

        org     0100h

start:
        call    read_config
        jc      unavailable
        call    select_geometry
        call    select_strings
        call    select_borders

        mvi     a,01bh
        call    putc
        mvi     a,'L'
        call    putc
        call    top_row

        lxi     d,title
        call    interior_row
        lhld    mode_string
        xchg
        call    interior_row
        lhld    locale_string
        xchg
        call    interior_row
        lxi     d,ascii_upper
        call    interior_row
        lxi     d,ascii_lower
        call    interior_row
        lhld    locale_sample
        xchg
        call    interior_row
        lhld    graphic_sample
        xchg
        call    interior_row

fill_rows:
        lda     rows_left
        ora     a
        jz      bottom_row
        lxi     d,empty
        call    interior_row
        jmp     fill_rows

bottom_row:
        lda     border_bottom_left
        call    putc
        lda     columns
        sui     2+READY_LENGTH
        mov     b,a
bottom_fill:
        lda     border_horizontal
        call    putc
        dcr     b
        jnz     bottom_fill
        lxi     d,ready
        call    puts0

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

; CP/M 3 BDOS function 50 calls BIOS USERF (vector 30) without depending on
; the BIOS load address. Return CY set unless its JNS1 record is present.
read_config:
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
        jnz     config_bad
        mov     a,m
        cpi     'J'
        jnz     config_bad
        inx     h
        mov     a,m
        cpi     'N'
        jnz     config_bad
        inx     h
        mov     a,m
        cpi     'S'
        jnz     config_bad
        inx     h
        mov     a,m
        cpi     '1'
        jnz     config_bad
        inx     h
        inx     h
        inx     h
        inx     h
        inx     h                       ; JNS1 + version/length/flags
        mov     a,m                     ; raw S21 at offset 8
        sta     raw_s21
        mov     b,a
        ani     006h
        rrc
        sta     video_mode
        mov     a,b
        rrc
        rrc
        rrc
        ani     3
        sta     locale
        ora     a                       ; clear carry
        ret
config_bad:
        stc
        ret

select_geometry:
        lda     video_mode
        add     a
        mov     e,a
        mvi     d,0
        lxi     h,geometries
        dad     d
        mov     a,m
        sta     columns
        inx     h
        mov     a,m
        sta     rows
        sui     2                       ; every interior row decrements this
        sta     rows_left
        ret

select_strings:
        lda     video_mode
        call    table_pointer
        shld    mode_string
        lda     locale
        call    locale_table_pointer
        shld    locale_string
        lda     locale
        lxi     d,locale_samples
        call    indexed_pointer
        shld    locale_sample
        lda     video_mode
        cpi     3
        lxi     h,graphics_text
        jnz     graphics_selected
        lxi     h,graphics_cp437
graphics_selected:
        shld    graphic_sample
        ret

table_pointer:
        lxi     d,mode_strings
        jmp     indexed_pointer
locale_table_pointer:
        lxi     d,locale_strings
indexed_pointer:
        add     a
        mov     l,a
        mvi     h,0
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        xchg
        ret

select_borders:
        mvi     a,'+'
        sta     border_top_left
        sta     border_top_right
        sta     border_bottom_left
        mvi     a,'-'
        sta     border_horizontal
        mvi     a,'|'
        sta     border_vertical
        lda     video_mode
        cpi     3
        rnz
        mvi     a,0dah
        sta     border_top_left
        mvi     a,0bfh
        sta     border_top_right
        mvi     a,0c0h
        sta     border_bottom_left
        mvi     a,0c4h
        sta     border_horizontal
        mvi     a,0b3h
        sta     border_vertical
        ret

top_row:
        lda     border_top_left
        call    putc
        lda     columns
        sui     2
        mov     b,a
top_fill:
        lda     border_horizontal
        call    putc
        dcr     b
        jnz     top_fill
        lda     border_top_right
        jmp     putc

; DE -> zero-terminated content. Exactly one complete row is emitted, so the
; console's ordinary auto-wrap advances to the next row without CR/LF.
interior_row:
        lda     rows_left
        dcr     a
        sta     rows_left
        lda     border_vertical
        call    putc
        lda     columns
        sui     2
        mov     b,a
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

geometries:
        db      40,24, 53,24, 64,20, 80,24
mode_strings:
        dw      mode0,mode1,mode2,mode3
locale_strings:
        dw      locale0,locale1,locale2,locale3
locale_samples:
        dw      sample0,sample1,sample2,sample3

title:  db      'Juku Vidtest 1.0',0
mode0:  db      'Mode 0: 40x24, 8x10 cells',0
mode1:  db      'Mode 1: 53x24, 6x10 cells',0
mode2:  db      'Mode 2: 64x20, 6x10 cells',0
mode3:  db      'Mode 3: 80x24, 5x8 cells',0
locale0:
        db      'Locale 0: English + CP437 UI',0
locale1:
        db      'Locale 1: Estonian ISO-8859-1',0
locale2:
        db      'Locale 2: Russian CP866',0
locale3:
        db      'Locale 3: English/remap fallback',0
ascii_upper:
        db      'ASCII: ABCDEFGHIJKLMNOPQRSTUVWXYZ',0
ascii_lower:
        db      'Digits: 0123456789  lower: abcxyz',0
sample0:
        db      'Locale sample: Juku 2026',0
sample1:
        db      'Locale: ',0c4h,0d5h,0d6h,0dch,0e4h,0f5h,0f6h,0fch,0
sample2:
        db      'Locale: ',080h,081h,082h,083h,084h,085h,086h,087h,0
sample3:
        db      'Locale sample: Juku 2026',0
graphics_text:
        db      'Boundary: ASCII fallback in wide mode',0
graphics_cp437:
        db      'CP437: ',0dah,0c4h,0c2h,0c4h,0bfh,' '
        db      0b3h,0c5h,0b3h,' ',0c0h,0c4h,0c1h,0c4h,0d9h,0
empty:  db      0
ready:  db      'VIDTEST READY',0
READY_LENGTH    equ     $-ready-1
done:   db      13,10,'Juku Vidtest 1.0 DONE',13,10,0
unavailable_text:
        db      13,10,'Juku Vidtest requires the native JNS1 BIOS.',13,10,0

bios_function: db      30
bios_a:        db      0
bios_bc:       dw      0
bios_de:       dw      0
bios_hl:       dw      0
raw_s21:       db      0
video_mode:    db      0
locale:        db      0
columns:       db      80
rows:          db      24
rows_left:     db      0
mode_string:   dw      mode3
locale_string:dw      locale0
locale_sample:dw      sample0
graphic_sample:dw     graphics_cp437
border_top_left:      db '+'
border_top_right:     db '+'
border_bottom_left:   db '+'
border_horizontal:    db '-'
border_vertical:      db '|'

        end
