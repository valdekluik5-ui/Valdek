package com.valdek.voiceclean;

/** RNNoise neural noise suppression (native code in jni/, model weights from RNNoise 0.2). */
public final class Rnnoise {
    public static final int RATE = 48000, FRAME = 480;
    public static final boolean AVAILABLE;
    static {
        boolean ok;
        try { System.loadLibrary("voiceclean"); ok = true; } catch (Throwable t) { ok = false; }
        AVAILABLE = ok;
    }

    static native long create();
    static native void destroy(long h);
    /** In place on frames*480 samples scaled like 16-bit PCM; vad[i] = voice probability of frame i. */
    static native void process(long h, float[] buf, int frames, float[] vad);

    private long h;
    public Rnnoise() { h = create(); if (h == 0) throw new IllegalStateException("rnnoise"); }
    public void run(float[] buf, int frames, float[] vad) { process(h, buf, frames, vad); }
    public void close() { if (h != 0) { destroy(h); h = 0; } }
}
