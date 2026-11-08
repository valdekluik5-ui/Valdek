package com.valdek.voiceclean;

/**
 * Speech enhancement for a mono signal (pure Java, no Android classes, so it can be tested on a desktop).
 *
 * How it works (STFT, 75% overlap, Hann analysis + synthesis):
 *  1. analyze(): a first pass over the whole recording builds, for every frequency bin, a histogram of the
 *     smoothed power. A low percentile of that histogram is the steady background (hum, fan, traffic, hiss, wind
 *     rumble) — it is what is left in the pauses between words.
 *  2. process(): a second pass. A minimum-statistics tracker follows noise that changes over time; the noise used is
 *     the larger of the two estimates. Each bin then gets an Ephraim–Malah log-spectral-amplitude gain with
 *     decision-directed a-priori SNR (low "musical noise"), smoothed over frequency, plus a voice-activity gate that
 *     pulls the whole frame down when nobody is speaking, and an optional voice-band shape (cuts rumble below 80 Hz
 *     and hiss above 10 kHz).
 * The output is aligned with the input (the STFT delay is removed).
 */
public final class Denoiser {
    private final int fs, n, hop, bins;
    private final float[] win;
    private final float winNorm;
    private final float[] re, im;
    private final int[] bitrev;
    private final float[] cosT, sinT;

    // settings
    private final float gMin, overSub, gateFloor;
    private final boolean voiceBand;

    // pass 1: histogram of smoothed log power per bin
    private static final float H_LO = -200f, H_STEP = 0.5f;
    private static final int H_BINS = 600;
    private final int[][] hist;
    private final float[] smooth1;
    private int histFrames;
    private float[] noiseGlobal;

    // pass 2 state
    private final float[] smooth2, minCur, minAll, gPrev, gammaPrev, noise;
    private float[][] subMins;
    private int subIdx, subCount, frameIdx;
    private static final int SUB_WINDOWS = 8;
    private final int subLen;
    private float gate = 1f;
    private int hold;

    // streaming buffers
    private final float[] inBuf, outAcc;
    private int inFill;
    private long consumed, produced, dropped;
    private final int latency;

    /** strength 0..1: how hard to push the background down. voiceBand: also cut rumble and hiss. */
    public Denoiser(int sampleRate, float strength, boolean voiceBand) {
        fs = sampleRate;
        int size = 256;
        while (size * 2 <= 0.032 * fs) size *= 2;   // ~21–32 ms frames
        n = size; hop = n / 4; bins = n / 2 + 1;
        win = new float[n];
        for (int i = 0; i < n; i++) win[i] = (float) (0.5 - 0.5 * Math.cos(2 * Math.PI * i / n));
        // overlap-added w^2 is constant for periodic Hann at 75% overlap: sum(w^2) / hop
        float tot = 0; for (int i = 0; i < n; i++) tot += win[i] * win[i];
        winNorm = tot / hop;
        re = new float[n]; im = new float[n];
        bitrev = new int[n];
        int bitsN = Integer.numberOfTrailingZeros(n);
        for (int i = 0; i < n; i++) bitrev[i] = Integer.reverse(i) >>> (32 - bitsN);
        cosT = new float[n / 2]; sinT = new float[n / 2];
        for (int i = 0; i < n / 2; i++) { cosT[i] = (float) Math.cos(-2 * Math.PI * i / n); sinT[i] = (float) Math.sin(-2 * Math.PI * i / n); }

        float s = Math.max(0f, Math.min(1f, strength));
        gMin = (float) Math.pow(10, -(8 + 27 * s) / 20.0);
        overSub = 1f + 1.5f * s;
        gateFloor = (float) Math.pow(10, -(12 * s) / 20.0);
        this.voiceBand = voiceBand;

        hist = new int[bins][H_BINS];
        smooth1 = new float[bins];
        smooth2 = new float[bins]; minCur = new float[bins]; minAll = new float[bins];
        gPrev = new float[bins]; gammaPrev = new float[bins]; noise = new float[bins];
        subLen = Math.max(1, (int) Math.round(1.6 * fs / hop / SUB_WINDOWS)); // ~1.6 s search window
        subMins = new float[SUB_WINDOWS][bins];

        inBuf = new float[n];
        outAcc = new float[n];
        latency = n - hop;
        inFill = n - hop;   // start on zeros so the first samples get full overlap; the delay is dropped in emit()
    }

    public int frameSize() { return n; }

    // ---------------------------------------------------------------- pass 1

    private final float[] aBuf = new float[0x10000];
    private int aFill;

    /** First pass: feed the whole recording once. */
    public void analyze(float[] x, int off, int len) {
        for (int i = 0; i < len; i++) {
            aBuf[aFill++] = x[off + i];
            if (aFill == n) {
                spectrum(aBuf, 0);
                float total = 0;
                for (int k = 0; k < bins; k++) total += re[k] * re[k] + im[k] * im[k];
                boolean silent = total < 1e-9f * n; // digital silence would drag the estimate to zero
                for (int k = 0; k < bins; k++) {
                    float p = re[k] * re[k] + im[k] * im[k];
                    smooth1[k] = histFrames == 0 ? p : 0.6f * smooth1[k] + 0.4f * p;
                    if (!silent) {
                        int h = (int) ((10 * Math.log10(smooth1[k] + 1e-20) - H_LO) / H_STEP);
                        hist[k][Math.max(0, Math.min(H_BINS - 1, h))]++;
                    }
                }
                if (!silent) histFrames++;
                System.arraycopy(aBuf, hop, aBuf, 0, n - hop);
                aFill = n - hop;
            }
        }
    }

    /** Ends the first pass; returns false when the recording held no sound at all. */
    public boolean finishAnalysis() {
        noiseGlobal = new float[bins];
        if (histFrames < 4) return false;
        int target = Math.max(1, (int) (histFrames * 0.12));
        for (int k = 0; k < bins; k++) {
            int c = 0, h = 0;
            for (; h < H_BINS; h++) { c += hist[k][h]; if (c >= target) break; }
            double db = H_LO + (h + 0.5) * H_STEP;
            noiseGlobal[k] = (float) (Math.pow(10, db / 10) * 1.9); // low percentile -> mean noise power
        }
        // smooth across frequency so single tonal bins do not stand out
        float[] t = noiseGlobal.clone();
        for (int k = 1; k < bins - 1; k++) noiseGlobal[k] = 0.25f * t[k - 1] + 0.5f * t[k] + 0.25f * t[k + 1];
        return true;
    }

    // ---------------------------------------------------------------- pass 2

    /** Second pass: returns the cleaned samples available so far (output length tracks input length). */
    public int process(float[] x, int off, int len, float[] out, int outOff) {
        int w = 0;
        for (int i = 0; i < len; i++) {
            inBuf[inFill++] = x[off + i];
            consumed++;
            if (inFill == n) {
                frame();
                w += emit(out, outOff + w, hop);
                System.arraycopy(inBuf, hop, inBuf, 0, n - hop);
                inFill = n - hop;
            }
        }
        return w;
    }

    /** Flushes the tail; out must hold at least frameSize() samples. */
    public int flush(float[] out, int outOff) {
        int w = 0;
        while (produced < consumed) {
            while (inFill < n) inBuf[inFill++] = 0;
            frame();
            w += emit(out, outOff + w, hop);
            System.arraycopy(inBuf, hop, inBuf, 0, n - hop);
            inFill = n - hop;
        }
        return w;
    }

    private int emit(float[] out, int off, int count) {
        int w = 0;
        for (int i = 0; i < count; i++) {
            float v = outAcc[i];
            if (dropped < latency) { dropped++; continue; }
            if (produced >= consumed) continue;
            out[off + w++] = v;
            produced++;
        }
        System.arraycopy(outAcc, count, outAcc, 0, n - count);
        for (int i = n - count; i < n; i++) outAcc[i] = 0;
        return w;
    }

    private static final float BIAS = 1.9f;

    private void frame() {
        spectrum(inBuf, 0);
        if (noiseGlobal == null) noiseGlobal = new float[bins];

        // minimum statistics tracker
        for (int k = 0; k < bins; k++) {
            float p = re[k] * re[k] + im[k] * im[k];
            smooth2[k] = frameIdx == 0 ? p : 0.85f * smooth2[k] + 0.15f * p;
            if (subCount == 0 || smooth2[k] < minCur[k]) minCur[k] = smooth2[k];
        }
        if (frameIdx == 0) for (float[] m : subMins) System.arraycopy(smooth2, 0, m, 0, bins);
        if (++subCount >= subLen) {
            System.arraycopy(minCur, 0, subMins[subIdx], 0, bins);
            subIdx = (subIdx + 1) % SUB_WINDOWS;
            subCount = 0;
        }
        for (int k = 0; k < bins; k++) {
            float m = minCur[k];
            for (float[] sm : subMins) if (sm[k] < m) m = sm[k];
            float local = m * BIAS;
            noise[k] = Math.max(noiseGlobal[k], local) * overSub;
        }

        // voice-activity: speech band energy against noise
        int lo = Math.max(1, (int) (250.0 * n / fs)), hi = Math.min(bins - 1, (int) (4000.0 * n / fs));
        double sp = 0, nz = 0;
        for (int k = lo; k <= hi; k++) { sp += re[k] * re[k] + im[k] * im[k]; nz += noise[k] / overSub; }
        double snrBand = sp / (nz + 1e-20);
        boolean speech = snrBand > 2.5;   // ~4 dB above the background
        if (speech) hold = (int) (0.25 * fs / hop); else if (hold > 0) hold--;
        float gateTarget = (speech || hold > 0) ? 1f : gateFloor;
        gate += (gateTarget - gate) * (gateTarget > gate ? 0.6f : 0.08f);

        // LSA gain per bin
        float[] g = new float[bins];
        for (int k = 0; k < bins; k++) {
            float p = re[k] * re[k] + im[k] * im[k];
            float lam = noise[k] + 1e-20f;
            float gamma = Math.min(p / lam, 1e4f);
            float xi = frameIdx == 0 ? Math.max(gamma - 1, 0)
                    : 0.98f * gPrev[k] * gPrev[k] * gammaPrev[k] + 0.02f * Math.max(gamma - 1, 0);
            xi = Math.max(xi, 0.003f);
            float v = xi * gamma / (1 + xi);
            float gain = (float) (xi / (1 + xi) * Math.exp(0.5 * e1(v)));
            if (gain > 1) gain = 1;
            gPrev[k] = gain;
            gammaPrev[k] = gamma;
            g[k] = gain;
        }
        // smooth gains across frequency (less musical noise), then apply floor, gate and voice band
        float binHz = (float) fs / n;
        for (int k = 0; k < bins; k++) {
            float a = g[Math.max(0, k - 1)], b = g[k], c = g[Math.min(bins - 1, k + 1)];
            float gk = Math.max(0.25f * a + 0.5f * b + 0.25f * c, gMin) * gate;
            if (voiceBand) {
                float f = k * binHz;
                if (f < 70) gk *= gMin;
                else if (f < 110) gk *= 0.35f;
                else if (f > 10000) gk *= 0.25f;
            }
            re[k] *= gk; im[k] *= gk;
            if (k > 0 && k < n / 2) { re[n - k] = re[k]; im[n - k] = -im[k]; }
        }
        im[0] = 0; im[n / 2] = 0;
        // inverse FFT (conjugate trick)
        for (int i = 0; i < n; i++) im[i] = -im[i];
        fft(re, im);
        float sc = 1f / (n * winNorm);
        for (int i = 0; i < n; i++) outAcc[i] += re[i] * win[i] * sc;
        frameIdx++;
    }

    /** Windowed forward FFT of src[off..off+n) into re/im. */
    private void spectrum(float[] src, int off) {
        for (int i = 0; i < n; i++) { re[i] = src[off + i] * win[i]; im[i] = 0; }
        fft(re, im);
    }

    private void fft(float[] r, float[] m) {
        for (int i = 0; i < n; i++) {
            int j = bitrev[i];
            if (j > i) { float t = r[i]; r[i] = r[j]; r[j] = t; t = m[i]; m[i] = m[j]; m[j] = t; }
        }
        for (int len = 2; len <= n; len <<= 1) {
            int half = len >> 1, step = n / len;
            for (int i = 0; i < n; i += len) {
                for (int j = 0; j < half; j++) {
                    float wr = cosT[j * step], wi = sinT[j * step];
                    int a = i + j, b = a + half;
                    float xr = r[b] * wr - m[b] * wi, xi = r[b] * wi + m[b] * wr;
                    r[b] = r[a] - xr; m[b] = m[a] - xi;
                    r[a] += xr; m[a] += xi;
                }
            }
        }
    }

    /** Exponential integral E1(x), x > 0. */
    static double e1(double x) {
        if (x < 1e-8) x = 1e-8;
        if (x <= 1) {
            double sum = 0, term = 1;
            for (int k = 1; k < 30; k++) {
                term *= -x / k;
                sum -= term / k;
            }
            return -0.5772156649015329 - Math.log(x) + sum;
        }
        // continued fraction
        double b = x + 1, c = 1e30, d = 1 / b, h = d;
        for (int i = 1; i < 60; i++) {
            double an = -(double) i * i;
            b += 2;
            d = 1 / (an * d + b);
            c = b + an / c;
            double del = c * d;
            h *= del;
            if (Math.abs(del - 1) < 1e-10) break;
        }
        return h * Math.exp(-x);
    }
}
