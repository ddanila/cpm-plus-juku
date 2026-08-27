; Live discriminator for the C9 PC7/POF video-initialization fault.
; This matches EktaSoft 3.7's BSR reset of PPI0 Port C bit 7.

        org     0100h
        mvi     a,00eh
        out     007h
        ret
        end
