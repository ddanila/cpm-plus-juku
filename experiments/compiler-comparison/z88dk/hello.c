/* Copyright (c) 2026 Danila Sukharev. BSD-2-Clause. */
#include <cpm.h>

int main(void)
{
    static char message[] = "Hello from z88dk\r\n$";
    bdos(9, message);
    return 0;
}
