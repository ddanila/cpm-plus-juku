; CP/M front end for the shared, non-destructive Juku diagnostics.
; Copyright (c) 2026 Danila Sukharev
; BSD-2-Clause; see ../LICENSE.

BDOS            equ     5
CONOUT          equ     2
PRINT           equ     9
COMMAND_LENGTH  equ     080h
COMMAND_TEXT    equ     081h
DIAG_PIT_COUNT0 equ    018h
DIAG_PIT_CONTROL equ   01bh
DIAG_USART_CONTROL equ 009h
DIAG_KEYCOL_PORT equ   004h
DIAG_KEYROW_PORT equ   005h
DIAG_MODE_PORT  equ     006h
NATIVE_MARKER   equ     0c642h
.ifdef ROM_ABI_C12
        include "rom-abi.inc"
.endif

        org     0100h

start:
        xra     a
        sta     report_pass
        sta     report_fail
        sta     report_flags
        inr     a
        sta     report_suite
        lxi     d,banner
        call    print_string
        call    identify_rom
        call    print_rom_identity

        lda     COMMAND_LENGTH
        ora     a
        jz      show_usage
        mov     b,a
        lxi     h,COMMAND_TEXT
skip_space:
        mov     a,m
        cpi     ' '
        jz      skip_one
        cpi     9
        jnz     select_test
skip_one:
        inx     h
        dcr     b
        jnz     skip_space
        jmp     show_usage

select_test:
        ani     05fh            ; accept upper/lower-case selector names
        cpi     'C'
        jz      run_cpu
        cpi     'M'
        jz      run_memory
        cpi     'R'
        jz      select_ram_test
        cpi     'A'
        jz      select_a_test
        cpi     'S'
        jz      run_checksum
        cpi     'P'
        jz      run_pit
        cpi     'U'
        jz      run_usart
        cpi     'O'
        jz      run_rom
        cpi     'V'
        jz      run_video
        cpi     'K'
        jz      run_keyboard
        cpi     'I'
        jz      run_io
        cpi     'D'
        jz      run_destructive
        cpi     'H'
        jz      show_usage
        cpi     '?'
        jz      show_usage
        lxi     d,unknown_selector
        call    print_string
show_usage:
        lxi     d,usage
        jmp     print_string

select_ram_test:
        inx     h
        mov     a,m
        ani     05fh
        cpi     'E'             ; RET; bare R or RAM selects the suite
        jz      run_retention
        cpi     'O'             ; ROM
        jz      run_rom
        jmp     run_ram_suite

select_a_test:
        inx     h
        mov     a,m
        ani     05fh
        cpi     'D'             ; ADDR rather than ALL
        jz      run_address
        jmp     run_all

run_all:
        call    run_cpu_sub
        call    run_ram_suite_sub
        call    run_checksum_sub
        call    run_io_sub
        jmp     publish_report

run_cpu:
        call    run_cpu_sub
        jmp     publish_report

run_cpu_sub:
        mvi     a,001h
        sta     report_bit
        lxi     d,cpu_label
        call    print_string
        call    diag_cpu_test
        jmp     print_result

run_ram_suite:
        call    run_ram_suite_sub
        jmp     publish_report

run_ram_suite_sub:
        call    run_memory_sub
        call    run_address_sub
        jmp     run_retention_sub

run_memory:
        call    run_memory_sub
        jmp     publish_report

run_memory_sub:
        mvi     a,002h
        sta     report_bit
        lxi     d,memory_label
        call    print_string
        lxi     h,test_buffer
        lxi     d,test_buffer_end
        call    diag_memory_test
        jmp     print_result

run_address:
        call    run_address_sub
        jmp     publish_report

run_address_sub:
        mvi     a,002h
        sta     report_bit
        lxi     d,address_label
        call    print_string
        lxi     h,test_buffer
        mvi     a,8             ; A0..A7 within the private 256-byte page
        call    diag_memory_address_test
        jmp     print_result

run_retention:
        call    run_retention_sub
        jmp     publish_report

run_retention_sub:
        mvi     a,080h
        sta     report_bit
        lxi     d,retention_label
        call    print_string
        lxi     h,test_buffer
        lxi     b,0ffffh        ; caller-owned hold, twice, while raster runs
        call    diag_memory_retention_test
        jmp     print_result

run_checksum:
        call    run_checksum_sub
        jmp     publish_report
run_checksum_sub:
        mvi     a,010h
        sta     report_bit
        lxi     d,checksum_label
        call    print_string
        lxi     h,checksum_fixture
        lxi     d,checksum_fixture_end
        call    diag_checksum8
        xri     078h            ; sum(00h..0Fh)
        jmp     print_result

run_io:
        mvi     a,2
        sta     report_suite
        call    run_io_sub
        jmp     publish_report
run_io_sub:
        call    run_pit_sub
        call    run_usart_sub
        call    run_rom_sub
        call    run_video_sub
        jmp     run_keyboard_sub

run_pit:
        call    run_pit_sub
        jmp     publish_report
run_pit_sub:
        mvi     a,004h
        sta     report_bit
        lxi     d,pit_label
        call    print_string
        call    diag_pit_d57_test
        jmp     print_result

run_usart:
        call    run_usart_sub
        jmp     publish_report
run_usart_sub:
        mvi     a,008h
        sta     report_bit
        lxi     d,usart_label
        call    print_string
        call    diag_usart_status_test
        jmp     print_result

run_rom:
        call    run_rom_sub
        jmp     publish_report
run_rom_sub:
        mvi     a,010h
        sta     report_bit
        lxi     d,rom_label
        call    print_string
        lda     rom_class
        ora     a
        jz      run_rom_fail
        cpi     4                       ; identified damaged archive
        jz      run_rom_fail
        cpi     3                       ; future manifest-only JukuNet image
        jnz     run_rom_pass            ; every table fingerprint is exact

        ; Current/future JukuNet images can carry a zero-sum integrity byte
        ; across the complete ROM-visible D800h..FFFFh window. Use it only for
        ; a compatible manifest not already covered by an exact table entry.
        call    select_rom_reads
        lxi     h,0d800h
        lxi     d,00000h
        call    diag_checksum8
        push    psw
        call    restore_memory_mode
        pop     psw
        ora     a
        jnz     run_rom_fail
run_rom_pass:
        xra     a
        jmp     run_rom_result
run_rom_fail:
        mvi     a,1
run_rom_result:
        jmp     print_result

run_video:
        call    run_video_sub
        jmp     publish_report
run_video_sub:
        mvi     a,020h
        sta     report_bit
        lxi     d,video_label
        call    print_string
        ; CP/M BIOS CONOST is the portable live-system readiness boundary.
        ; It exists on the stock RomBios path and on the RAM-owned JukuNet
        ; path, and avoids calling any ROM-private diagnostic procedure.
        mvi     a,17                   ; CP/M 3 CONOST
        call    setvector
        call    bioscall
        inr     a                       ; FFh is ready
        jnz     run_video_fail
.ifdef ROM_ABI_C12
        ; Runtime overrides are valid. Verify the published active tuple and
        ; flags, never equality with the reset-latched S21 defaults.
        mvi     a,JROMCONCONFIGQUERY
        call    JCGCONCONFIGADDR
        jc      run_video_fail
        mov     a,b
        cpi     4
        jnc     run_video_fail
        mov     a,c
        cpi     4
        jnc     run_video_fail
        mov     a,d
        ani     0fch
        jnz     run_video_fail
.endif
.ifdef ROM_ABI_C10
        ; C10's physical acceptance discriminator: mode/renderer readiness is
        ; insufficient while PPI0 PC7/POF is high. An output-port read returns
        ; the 8255 latch; bit 7 set is the exact C9 sync-without-pixels fault.
        in      DIAG_MODE_PORT
        ani     080h
        jmp     run_video_result
.else
        xra     a
        jmp     run_video_result
.endif
run_video_fail:
        mvi     a,1
run_video_result:
        jmp     print_result

run_keyboard:
        call    run_keyboard_sub
        jmp     publish_report
run_keyboard_sub:
        mvi     a,040h
        sta     report_bit
        lxi     d,keyboard_label
        call    print_string
        call    diag_s21_config_read
        sta     s21_raw
        mov     b,a
        call    diag_s21_config_read
        xra     b                       ; a stable direct path returns twice
        call    print_result
        lxi     d,s21_label
        call    print_string
        lda     s21_raw
        call    print_hex
        lxi     d,newline
        jmp     print_string

; Compute a four-block additive fingerprint over every byte visible in the
; D800h..FFFFh ROM window.  Exact archived images use this as an integrity and
; version key; JukuNet images are additionally recognized by their manifest.
identify_rom:
        call    select_rom_reads
        lxi     h,0d800h
        lxi     d,0e200h
        call    diag_checksum8
        sta     rom_fingerprint
        lxi     h,0e200h
        lxi     d,0ec00h
        call    diag_checksum8
        sta     rom_fingerprint+1
        lxi     h,0ec00h
        lxi     d,0f600h
        call    diag_checksum8
        sta     rom_fingerprint+2
        lxi     h,0f600h
        lxi     d,00000h
        call    diag_checksum8
        sta     rom_fingerprint+3

        lxi     h,rom_identity_table
identify_rom_next:
        push    h
        lxi     d,4
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        mov     a,d
        ora     e
        pop     h
        jz      identify_rom_manifest
        push    h
        lxi     d,rom_fingerprint
        mvi     b,4
        call    diag_signature_test
        pop     h
        ora     a
        jz      identify_rom_known
        lxi     d,7
        dad     d
        jmp     identify_rom_next

identify_rom_known:
        lxi     d,4
        dad     d
        mov     e,m
        inx     h
        mov     d,m
        xchg
        shld    rom_identity
        xchg
        inx     h
        mov     a,m
        sta     rom_class
        jmp     restore_memory_mode

identify_rom_manifest:
        lxi     h,0ff00h
        lxi     d,rom_signature
        mvi     b,8
        call    diag_signature_test
        ora     a
        jnz     restore_memory_mode
        mvi     a,3                     ; compatible, not exact-table JukuNet
        sta     rom_class
        jmp     restore_memory_mode

; Mode 3 exposes the framebuffer RAM and is used by the RomBios-compatible
; CP/M baseline.  Mode 1 maps D800h..FFFFh ROM reads.  DIAG executes and keeps
; its stack below D800h, so it can select mode 1 for a bounded read-only pass
; and then restore the exact previous port-C value.  Interrupt policy is left
; untouched: stock RomBios handlers are valid in mode 1 and JukuNet normally
; owns mode 1 already.
select_rom_reads:
        in      DIAG_MODE_PORT
        sta     previous_memory_mode
        ani     0fch
        ori     1
        out     DIAG_MODE_PORT
        ret

restore_memory_mode:
        lda     previous_memory_mode
        out     DIAG_MODE_PORT
        ret

print_rom_identity:
        lxi     d,rom_identity_prefix
        call    print_string
        lhld    rom_identity
        mov     a,h
        ora     l
        jz      print_rom_dynamic
        xchg
        jmp     print_string

print_rom_dynamic:
        lda     rom_class
        ora     a
        jz      print_rom_unknown
        lxi     d,jukunet_dynamic
        call    print_string
        lda     0ff08h
        call    print_hex
        mvi     e,'.'
        mvi     c,CONOUT
        call    BDOS
        lda     0ff09h
        call    print_hex
        lxi     d,identity_separator
        call    print_string
        lhld    0ff0eh
        call    print_zstring
        lxi     d,newline
        jmp     print_string

print_rom_unknown:
        lxi     d,unknown_rom
        call    print_string
        lxi     h,rom_fingerprint
        mvi     b,4
print_rom_fingerprint:
        mov     a,m
        push    b
        push    h
        call    print_hex
        pop     h
        pop     b
        inx     h
        dcr     b
        jnz     print_rom_fingerprint
        lxi     d,newline
        jmp     print_string

; Print a ROM-owned NUL-terminated build identity through BDOS.
print_zstring:
        mov     a,m
        ora     a
        rz
        push    h
        mov     e,a
        mvi     c,CONOUT
        call    BDOS
        pop     h
        inx     h
        jmp     print_zstring

run_destructive:
        mvi     a,0ffh
        sta     report_suite
        mvi     a,1
        sta     report_flags            ; destructive request refused in CP/M
        lxi     d,destructive_msg
        call    print_string
        jmp     publish_report

; Publish one bounded machine result when the native N4 service is present.
publish_report:
        lda     NATIVE_MARKER
        cpi     04eh
        rnz
        mvi     a,30
        call    setvector
        lda     report_suite
        mov     b,a
        lda     report_pass
        mov     d,a
        lda     report_fail
        mov     e,a
        lda     report_flags
        mov     l,a
        mvi     c,2
        call    bioscall
        ret

; A is zero for PASS or a structured failure-bit mask.
print_result:
        push    psw
        lda     report_bit
        mov     b,a
        pop     psw
        ora     a
        jnz     record_failure
        lda     report_fail
        ana     b
        jnz     print_passed             ; a sibling RAM test already failed
        lda     report_pass
        ora     b
        sta     report_pass
print_passed:
        lxi     d,passed
        jmp     print_string
record_failure:
        push    psw
        lda     report_fail
        ora     b
        sta     report_fail
        mov     a,b
        cma
        mov     b,a
        lda     report_pass
        ana     b
        sta     report_pass
        pop     psw
print_failure:
        push    psw
        lxi     d,failed
        call    print_string
        pop     psw
        call    print_hex
        lxi     d,newline
        jmp     print_string

print_string:
        mvi     c,PRINT
        call    BDOS
        ret

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
        call    BDOS
        ret

; Patch a call to BIOS base + A*3. Address 0001h holds WBOOT (base+3).
setvector:
        mov     l,a
        mvi     h,0
        mov     d,h
        mov     e,l
        dad     h
        dad     d
        xchg
        lhld    0001h
        dcx     h
        dcx     h
        dcx     h
        dad     d
        shld    bioscall+1
        ret
bioscall:
        call    0000h
        ret

.ifdef ROM_ABI_C12
banner:
        db      13,10,'Juku Diag 0.8',13,10
        db      'Self-contained non-destructive 8080 diagnostics.',13,10,'$'
.else
.ifdef ROM_ABI_C10
banner:
        db      13,10,'Juku Diag 0.7',13,10
        db      'Self-contained non-destructive 8080 diagnostics.',13,10,'$'
.else
banner:
        db      13,10,'Juku Diag 0.6',13,10
        db      'Self-contained non-destructive 8080 diagnostics.',13,10,'$'
.endif
.endif
usage:
        db      'Usage: DIAG [CPU|MEM|ADDR|RET|RAM|SUM|PIT|USART|ROM',13,10
        db      '             |VIDEO|KEY|IO|ALL|DESTRUCT|HELP]',13,10,'$'
unknown_selector:
        db      'Unknown diagnostic selector.',13,10,'$'
cpu_label:
        db      'CPU: $'
memory_label:
        db      'RAM data: $'
address_label:
        db      'RAM address: $'
retention_label:
        db      'RAM retention: $'
checksum_label:
        db      'Checksum: $'
pit_label:
        db      'D57 PIT clock: $'
usart_label:
        db      'D11 USART status: $'
rom_label:
        db      'ROM image: $'
.ifdef ROM_ABI_C10
video_label:
        db      'Video enable/console state: $'
.else
video_label:
        db      'Video/console: $'
.endif
keyboard_label:
        db      'Keyboard/S21: $'
s21_label:
        db      '  S21 raw: $'
destructive_msg:
        db      'Destructive tests: NOT RUN under live CP/M; use reset ROM.',13,10,'$'
passed:
        db      'PASS',13,10,'$'
failed:
        db      'FAIL mask $'
newline:
        db      13,10,'$'
rom_signature:
        db      'J','U','K','U','A','B','I',0
rom_identity_prefix:
        db      'ROM: $'
jukunet_dynamic:
        db      'JukuNet ROM ABI $'
identity_separator:
        db      ' - $'
unknown_rom:
        db      'unknown; fingerprint $'

; Four additive sums cover D800h..FFFFh in 0A00h blocks.  The identity strings
; describe the exact archived/reference images in 8080-cosim.  Class 1 is an
; exact stock/remix/monitor image; class 2 is an exact known JukuNet image;
; class 4 is identified but intentionally fails the integrity result.
rom_identity_table:
        db      0f9h,0d7h,0beh,05fh
        dw      rom_ekta24
        db      1
        db      00eh,0e5h,072h,034h
        dw      rom_ekta31
        db      1
        db      0ach,0f0h,00fh,0a0h
        dw      rom_ekta32
        db      1
        db      0f8h,01eh,02ah,0efh
        dw      rom_ekta35
        db      1
        db      075h,09fh,07ah,0e1h
        dw      rom_ekta37
        db      1
        db      0a5h,0f9h,098h,0b1h
        dw      rom_ekta43
        db      1
        db      075h,081h,0c9h,0f6h
        dw      rom_jmon33
        db      1
        db      024h,04ah,09fh,08bh
        dw      rom_jmon22
        db      4                       ; identify it, but its integrity fails
        db      01eh,032h,07ah,0a5h
        dw      rom_ekta4401
        db      1
        db      051h,032h,07ah,0d8h
        dw      rom_ekta4402
        db      1
        db      031h,051h,000h,0bfh
        dw      rom_jukunet_c4
        db      2
        db      075h,0dbh,0c8h,07fh
        dw      rom_jukunet_c5
        db      2
        db      046h,0a8h,0c8h,046h
        dw      rom_jukunet_c6
        db      2
        db      012h,09ch,04bh,046h
        dw      rom_jukunet_c7
        db      2
        db      012h,01ah,09dh,037h
        dw      rom_jukunet_c8
        db      2
        db      0,0,0,0
        dw      0
        db      0

rom_ekta24:    db 'EktaSoft #0024 / RomBios 3.42',13,10,'$'
rom_ekta31:    db 'EktaSoft #0031 / RomBios 3.43',13,10,'$'
rom_ekta32:    db 'EktaSoft #0032 / RomBios 2.43',13,10,'$'
rom_ekta35:    db 'EktaSoft #0035 / RomBios 3.43',13,10,'$'
rom_ekta37:    db 'EktaSoft #0037 / RomBios 3.43m',13,10,'$'
rom_ekta43:    db 'EktaSoft #0043 / RomBios 2.43m',13,10,'$'
rom_jmon33:    db 'Juku monitor 3.3',13,10,'$'
rom_jmon22:    db 'Juku monitor 2.2 (known damaged archive)',13,10,'$'
rom_ekta4401: db 'EktaSoft 4.4 #01 / RomBios 3.43m',13,10,'$'
rom_ekta4402: db 'EktaSoft 4.4 #02 / RomBios 3.43m',13,10,'$'
rom_jukunet_c4: db 'JukuNet C4 / ROM ABI 1.0',13,10,'$'
rom_jukunet_c5: db 'JukuNet C5 / ROM ABI 1.1',13,10,'$'
rom_jukunet_c6: db 'JukuNet C6 / ROM ABI 1.2',13,10,'$'
rom_jukunet_c7: db 'JukuNet C7 / ROM ABI 1.2',13,10,'$'
rom_jukunet_c8: db 'JukuNet C8 / ROM ABI 1.3',13,10,'$'

rom_identity:
        dw      0
rom_class:
        db      0
rom_fingerprint:
        ds      4
s21_raw:
        db      0
previous_memory_mode:
        db      0
report_suite:
        db      1
report_pass:
        db      0
report_fail:
        db      0
report_flags:
        db      0
report_bit:
        db      0

        include "cpu.asm"
        include "memory.asm"
        include "memory-address.asm"
        include "memory-retention.asm"
        include "checksum.asm"
        include "pit-d57.asm"
        include "usart-status.asm"
        include "signature.asm"
        include "s21-config.asm"

checksum_fixture:
        db      00h,01h,02h,03h,04h,05h,06h,07h
        db      08h,09h,0ah,0bh,0ch,0dh,0eh,0fh
checksum_fixture_end:

; Deliberately private storage: testing it cannot overwrite CP/M, this program,
; its stack, or the transient program command tail. The returned A byte is the
; accumulated stuck/mismatching data-bit mask.
test_buffer:
        ds      256
test_buffer_end:

        end     start
