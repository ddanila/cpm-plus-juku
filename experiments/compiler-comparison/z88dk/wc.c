/* Copyright (c) 2026 Danila Sukharev. BSD-2-Clause. */
#include <cpm.h>

static void put_nibble(unsigned char value)
{
    value &= 0x0f;
    bdos(2, value < 10 ? value + '0' : value - 10 + 'A');
}

static void put_word(unsigned int value)
{
    put_nibble(value >> 12);
    put_nibble(value >> 8);
    put_nibble(value >> 4);
    put_nibble(value);
}

static void put_string(char *value)
{
    while (*value)
        bdos(2, *value++);
}

int main(void)
{
    unsigned char *dma = (unsigned char *)0x0080;
    unsigned int lines = 0;
    unsigned int words = 0;
    unsigned int bytes = 0;
    unsigned int i;
    unsigned char c;
    unsigned char in_word = 0;

    if ((unsigned char)bdos(15, 0x005c) == 0xff) {
        put_string("WC: not found\r\n");
        return 1;
    }
    while ((unsigned char)bdos(20, 0x005c) == 0) {
        for (i = 0; i != 128; ++i) {
            c = dma[i];
            if (c == 0x1a) {
                put_string("lines=");
                put_word(lines);
                put_string(" words=");
                put_word(words);
                put_string(" bytes=");
                put_word(bytes);
                put_string("\r\n");
                return 0;
            }
            ++bytes;
            if (c == '\n')
                ++lines;
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
                in_word = 0;
            } else {
                if (!in_word)
                    ++words;
                in_word = 1;
            }
        }
    }
    return 0;
}
