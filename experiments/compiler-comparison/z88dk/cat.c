/* Copyright (c) 2026 Danila Sukharev. BSD-2-Clause. */
#include <cpm.h>

int main(void)
{
    unsigned char *dma = (unsigned char *)0x0080;
    unsigned int i;
    unsigned char c;

    if ((unsigned char)bdos(15, 0x005c) == 0xff) {
        static char error[] = "CAT: not found\r\n$";
        bdos(9, error);
        return 1;
    }
    while ((unsigned char)bdos(20, 0x005c) == 0) {
        for (i = 0; i != 128; ++i) {
            c = dma[i];
            if (c == 0x1a)
                return 0;
            bdos(2, c);
        }
    }
    return 0;
}
