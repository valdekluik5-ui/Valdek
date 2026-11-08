/* ARM EABI helpers that 32-bit builds get from the NDK's static runtime (we build without the NDK). */
#include <stddef.h>
#include <string.h>

#define VIS __attribute__((visibility("hidden")))
VIS void __aeabi_memcpy(void *d, const void *s, size_t n) { memcpy(d, s, n); }
VIS void __aeabi_memcpy4(void *d, const void *s, size_t n) { memcpy(d, s, n); }
VIS void __aeabi_memcpy8(void *d, const void *s, size_t n) { memcpy(d, s, n); }
VIS void __aeabi_memmove(void *d, const void *s, size_t n) { memmove(d, s, n); }
VIS void __aeabi_memmove4(void *d, const void *s, size_t n) { memmove(d, s, n); }
VIS void __aeabi_memmove8(void *d, const void *s, size_t n) { memmove(d, s, n); }
VIS void __aeabi_memset(void *d, size_t n, int c) { memset(d, c, n); }
VIS void __aeabi_memset4(void *d, size_t n, int c) { memset(d, c, n); }
VIS void __aeabi_memset8(void *d, size_t n, int c) { memset(d, c, n); }
VIS void __aeabi_memclr(void *d, size_t n) { memset(d, 0, n); }
VIS void __aeabi_memclr4(void *d, size_t n) { memset(d, 0, n); }
VIS void __aeabi_memclr8(void *d, size_t n) { memset(d, 0, n); }

/* shift-and-subtract division, so it never calls itself */
static unsigned udiv32(unsigned n, unsigned d) {
    if (d == 0) return 0;
    unsigned q = 0, r = 0;
    for (int i = 31; i >= 0; i--) {
        r = (r << 1) | ((n >> i) & 1u);
        if (r >= d) { r -= d; q |= 1u << i; }
    }
    return q;
}
VIS unsigned __aeabi_uidiv(unsigned n, unsigned d) { return udiv32(n, d); }
VIS int __aeabi_idiv(int n, int d) {
    unsigned un = n < 0 ? 0u - (unsigned) n : (unsigned) n, ud = d < 0 ? 0u - (unsigned) d : (unsigned) d;
    unsigned q = udiv32(un, ud);
    return ((n < 0) != (d < 0)) ? -(int) q : (int) q;
}
/* quotient in r0, remainder in r1: a 64-bit return value is passed back in exactly that register pair */
VIS unsigned long long __aeabi_uidivmod(unsigned n, unsigned d) {
    unsigned q = udiv32(n, d);
    return ((unsigned long long) (n - q * d) << 32) | q;
}
VIS unsigned long long __aeabi_idivmod(int n, int d) {
    int q = __aeabi_idiv(n, d);
    return ((unsigned long long) (unsigned) (n - q * d) << 32) | (unsigned) q;
}
