; Minimal strict-8080 CP/M development-profile example.
; Copyright (c) 2026 Danila Sukharev
; BSD-2-Clause; see ../LICENSE.

        org     0100h

        lxi     d,message
        mvi     c,9
        call    0005h
        ret

message:
        db      'Juku dev profile$'

        end
