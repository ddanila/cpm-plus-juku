; Explicit nonzero-user CP/M warm-boot exerciser.
; Copyright (c) 2026 Danila Sukharev
; BSD-2-Clause; see ../LICENSE.

        org     0100h
        mvi     e,1
        mvi     c,32
        call    0005h
        jmp     0000h
        end
