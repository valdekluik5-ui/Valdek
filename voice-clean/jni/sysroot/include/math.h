#pragma once
double sqrt(double); float sqrtf(float);
double exp(double); float expf(float);
double log(double); float logf(float);
double log10(double); float log10f(float);
double pow(double, double); float powf(float, float);
double sin(double); float sinf(float);
double cos(double); float cosf(float);
double tanh(double); float tanhf(float);
double atan(double); float atanf(float);
double floor(double); float floorf(float);
double ceil(double); float ceilf(float);
double fabs(double); float fabsf(float);
long lrint(double); long lrintf(float);
double fmax(double, double); float fmaxf(float, float);
double fmin(double, double); float fminf(float, float);
#define M_PI 3.14159265358979323846
#define INFINITY __builtin_inff()
#define NAN __builtin_nanf("")
#define isnan(x) __builtin_isnan(x)
#define HUGE_VAL __builtin_huge_val()
