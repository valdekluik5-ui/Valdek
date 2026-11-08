/* JNI bridge to RNNoise (48 kHz, 480-sample frames, samples scaled like 16-bit PCM). */
#include <jni.h>
#include <stdint.h>
#include <stdlib.h>
#include "rnnoise.h"

JNIEXPORT jlong JNICALL Java_com_valdek_voiceclean_Rnnoise_create(JNIEnv *env, jclass cls) {
    (void) env; (void) cls;
    return (jlong) (intptr_t) rnnoise_create(NULL);
}

JNIEXPORT void JNICALL Java_com_valdek_voiceclean_Rnnoise_destroy(JNIEnv *env, jclass cls, jlong h) {
    (void) env; (void) cls;
    if (h) rnnoise_destroy((DenoiseState *) (intptr_t) h);
}

/* Cleans `frames` frames of 480 samples from buf in place; writes each frame's voice probability to vad. */
JNIEXPORT void JNICALL Java_com_valdek_voiceclean_Rnnoise_process(JNIEnv *env, jclass cls, jlong h,
                                                                   jfloatArray buf, jint frames, jfloatArray vad) {
    (void) cls;
    DenoiseState *st = (DenoiseState *) (intptr_t) h;
    jfloat *b = (*env)->GetFloatArrayElements(env, buf, NULL);
    jfloat *v = (*env)->GetFloatArrayElements(env, vad, NULL);
    for (int i = 0; i < frames; i++) v[i] = rnnoise_process_frame(st, b + 480 * i, b + 480 * i);
    (*env)->ReleaseFloatArrayElements(env, vad, v, 0);
    (*env)->ReleaseFloatArrayElements(env, buf, b, 0);
}
