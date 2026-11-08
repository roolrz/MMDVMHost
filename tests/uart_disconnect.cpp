#include "UARTController.h"
#include <cstdio>
#include <cstdarg>
#include <unistd.h>
#include <cstdlib>

void Log(unsigned int, const char* format, ...)
{
    va_list args;
    va_start(args, format);
    vfprintf(stderr, format, args);
    fputc('\n', stderr);
    va_end(args);
}

int main(int argc, char** argv)
{
    if (argc != 3) return 2;
    CUARTController uart(argv[1], 115200U);
    if (!uart.open()) return 3;
    puts("ready");
    fflush(stdout);
    unsigned char bytes[16];
    const unsigned int length = std::strtoul(argv[2], nullptr, 10);
    if (length == 0 || length > sizeof(bytes)) return 2;
    for (;;) {
        const int result = uart.read(bytes, length);
        if (result < 0) { uart.close(); return 4; }
        if (result > 0) {
            for (int i = 0; i < result; ++i) printf("%02x", bytes[i]);
            puts("");
            uart.close();
            return 0;
        }
        usleep(1000);
    }
}
