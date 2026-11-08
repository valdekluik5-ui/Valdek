/* Stand-in for Opus's os_support.h, which RNNoise 0.2's NEON code includes but does not ship. */
#ifndef OS_SUPPORT_H
#define OS_SUPPORT_H
#include <string.h>
#ifndef OPUS_INLINE
#define OPUS_INLINE inline
#endif
#define OPUS_CLEAR(dst, n) (memset((dst), 0, (n)*sizeof(*(dst))))
#define OPUS_COPY(dst, src, n) (memcpy((dst), (src), (n)*sizeof(*(dst))))
#define OPUS_MOVE(dst, src, n) (memmove((dst), (src), (n)*sizeof(*(dst))))
#endif
