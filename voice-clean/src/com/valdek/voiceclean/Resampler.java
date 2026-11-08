package com.valdek.voiceclean;

/** Streaming windowed-sinc resampler (any ratio, ~90 dB stop band). */
public final class Resampler {
    private static final int TAPS = 32, PHASES = 256;
    private final double step;        // input samples per output sample
    private final float[] table;      // (PHASES+1) x TAPS
    private float[] hist = new float[4096];
    private int histLen = TAPS / 2;   // zeros in front, so output 0 lines up with input 0
    private double pos = 0;           // position of the next output sample, relative to hist[0] - TAPS/2 + ...
    private final boolean same;

    public Resampler(int inRate, int outRate) {
        same = inRate == outRate;
        step = (double) inRate / outRate;
        double cutoff = Math.min(1.0, (double) outRate / inRate) * 0.94;
        table = new float[(PHASES + 1) * TAPS];
        for (int p = 0; p <= PHASES; p++) {
            double frac = (double) p / PHASES;
            double sum = 0;
            for (int t = 0; t < TAPS; t++) {
                double x = t - (TAPS / 2 - 1) - frac;           // distance from tap to the output point
                double s = x == 0 ? cutoff : Math.sin(Math.PI * cutoff * x) / (Math.PI * x);
                double wx = (x + TAPS / 2.0) / TAPS;            // Blackman window over [0,1]
                double w = wx <= 0 || wx >= 1 ? 0 : 0.42 - 0.5 * Math.cos(2 * Math.PI * wx) + 0.08 * Math.cos(4 * Math.PI * wx);
                table[p * TAPS + t] = (float) (s * w);
                sum += s * w;
            }
            for (int t = 0; t < TAPS; t++) table[p * TAPS + t] /= sum;
        }
        pos = TAPS / 2;                   // input sample 0 sits at hist[TAPS/2]
    }

    /** Converts len input samples; returns the number written to out (size out >= len/step + 2). */
    public int push(float[] in, int off, int len, float[] out, int outOff) {
        if (same) { System.arraycopy(in, off, out, outOff, len); return len; }
        if (histLen + len > hist.length) {
            float[] h = new float[Math.max(hist.length * 2, histLen + len)];
            System.arraycopy(hist, 0, h, 0, histLen);
            hist = h;
        }
        System.arraycopy(in, off, hist, histLen, len);
        histLen += len;
        int w = 0;
        while (true) {
            int base = (int) Math.floor(pos);
            if (base + TAPS / 2 + 1 > histLen) break;
            double frac = pos - base;
            int start = base - (TAPS / 2 - 1);
            double pf = frac * PHASES;
            int p0 = (int) pf;
            float a = (float) (pf - p0);
            float acc0 = 0, acc1 = 0;
            int t0 = p0 * TAPS, t1 = t0 + TAPS;
            for (int t = 0; t < TAPS; t++) {
                int i = start + t;
                float x = hist[i];
                acc0 += table[t0 + t] * x;
                acc1 += table[t1 + t] * x;
            }
            out[outOff + w++] = acc0 + (acc1 - acc0) * a;
            pos += step;
        }
        // drop history we no longer need
        int keep = (int) Math.floor(pos) - (TAPS / 2 - 1);
        if (keep > 0) {
            System.arraycopy(hist, keep, hist, 0, histLen - keep);
            histLen -= keep;
            pos -= keep;
        }
        return w;
    }

    /** Feeds trailing zeros so the last input samples come out. */
    public int flush(float[] out, int outOff) {
        if (same) return 0;
        return push(new float[TAPS], 0, TAPS, out, outOff);
    }
}
