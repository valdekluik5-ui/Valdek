/* Minimal libc declarations for building against Android's libc.so without the NDK. */
#pragma once
#include <stddef.h>
void *malloc(size_t n);
void *calloc(size_t n, size_t m);
void *realloc(void *p, size_t n);
void free(void *p);
void abort(void) __attribute__((noreturn));
int abs(int x);
