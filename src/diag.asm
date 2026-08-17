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
NATIVE_MARKER   equ     0c642h
ROM_DIAG_GATE   equ     0d644h
ROM_INFO_GATE   equ     0d647h

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

        lda     COMMAND_LENGTH
        ora     a
        jz      run_memory      ; preserve the original no-argument baseline
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
        jmp     run_memory

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
        lxi     h,0ff00h
        lxi     d,rom_signature
        mvi     b,8
        call    diag_signature_test
        ora     a
        jnz     run_rom_result
        lda     0ff08h
        cpi     1
        jnz     run_rom_fail
        lda     0ff0ch
        ani     020h
        jz      run_rom_fail
        call    ROM_INFO_GATE
        mov     a,h
        cpi     0ffh
        jnz     run_rom_fail
        mov     a,l
        ora     a
        jnz     run_rom_fail
        lxi     h,0
        xra     a
        call    ROM_DIAG_GATE
        cpi     0a5h
        jnz     run_rom_fail
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
        call    native_info
        jc      run_video_fail
        lxi     d,9
        dad     d
        mov     a,m
        cpi     4
        jnc     run_video_fail
        mvi     a,17                   ; CP/M 3 CONOST
        call    setvector
        call    bioscall
        inr     a                       ; FFh is ready
        jnz     run_video_fail
        xra     a
        jmp     run_video_result
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
        call    native_info
        jc      run_keyboard_fail
        lxi     d,8
        dad     d
        mov     a,m                     ; raw S21
        rrc
        ani     3
        mov     b,a
        inx     h
        mov     a,m
        cmp     b
        jnz     run_keyboard_fail
        xra     a
        jmp     run_keyboard_result
run_keyboard_fail:
        mvi     a,1
run_keyboard_result:
        jmp     print_result

; Return native JNS1 status in HL with carry clear. The fixed marker prevents
; a compatibility BIOS entry 30 (WBOOT) from being called accidentally.
native_info:
        lda     NATIVE_MARKER
        cpi     04eh
        stc
        rnz
        mvi     a,30
        call    setvector
        mvi     c,0
        call    bioscall
        ora     a
        stc
        rnz
        mov     a,m
        cpi     'J'
        stc
        rnz
        inx     h
        mov     a,m
        cpi     'N'
        stc
        rnz
        inx     h
        mov     a,m
        cpi     'S'
        stc
        rnz
        inx     h
        mov     a,m
        cpi     '1'
        stc
        rnz
        dcx     h
        dcx     h
        dcx     h
        ora     a                       ; clear carry
        ret

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

banner:
        db      13,10,'Juku Diag 0.5',13,10
        db      'Shared non-destructive 8080 diagnostics.',13,10
        db      'Usage: DIAG [CPU|MEM|ADDR|RET|RAM|SUM|PIT|USART|ROM',13,10
        db      '             |VIDEO|KEY|IO|ALL|DESTRUCT]',13,10
        db      'No argument keeps the private RAM test.',13,10,'$'
usage:
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
        db      'ROM ABI: $'
video_label:
        db      'Video/console: $'
keyboard_label:
        db      'Keyboard/S21: $'
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
