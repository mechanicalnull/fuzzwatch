#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

void fuzz_test(char *buf, int len) {

    if (buf[0] == 'F')
    if (buf[1] == 'u')
    if (buf[2] == 'z')
    if (buf[3] == 'z')
    if (buf[4] == 't')
    if (buf[5] == 'e')
    if (buf[6] == 's')
    if (buf[7] == 't') {
        *(volatile char *)NULL = 77;
    }
}

int main(int argc, char **argv) {

    char buf[9] = {0};

    if (argc != 2) {
        printf("USAGE: %s <input_file>\n", argv[0]);
        return 1;
    }

    int fd = open(argv[1], 0);
    if (fd == -1) {
      printf("USAGE: %s INPUT_FILE\n", argv[0]);
      return -1;
    }

    ssize_t bytes_read = read(fd, buf, sizeof(buf)-1);
    close(fd);

    if (bytes_read >= 0) {
      fuzz_test(buf, strlen(buf));
    }

    return 0;
}
