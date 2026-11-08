package com.valdek.voiceclean;

import java.io.IOException;

/**
 * Neural voice cleaning: input at any rate -> 48 kHz -> RNNoise -> a voice gate driven by RNNoise's speech
 * detector that turns down what is left between words.
 * Output is 48 kHz, aligned with the input.
 */
public final class NeuralCleaner {
    public interface Sink { void write(float[] buf, int n) throws IOException; }

    private static final int F = Rnnoise.FRAME, BATCH = 32, LOOK = 3, HOLD = 25;
    private final Resampler rs;
    private final Rnnoise net;
    private final float floor;
    private final float[] rsOut = new float[F * BATCH * 4 + 64];
    private final float[] batch = new float[F * BATCH];
    private final float[] vad = new float[BATCH];
    private int fill;
    private long dropLeft;

    // gate: frames wait here until LOOK frames of look-ahead are known
    private final int ring = 64;
    private final float[][] frames = new float[ring][F];
    private final float[] frameVad = new float[ring];
    private long inFrames, outFrames;
    private int sinceSpeech = 1 << 20;
    private float gain = 1f;
    private final float[] outBuf = new float[F];

    /** strength 0..1 */
    public NeuralCleaner(int inRate, float strength) {
        rs = new Resampler(inRate, Rnnoise.RATE);
        float s = Math.max(0, Math.min(1, strength));
        net = new Rnnoise();
        floor = (float) Math.pow(10, -(30 * s) / 20.0);
        dropLeft = 2L * F;     // RNNoise delays the sound by two frames (20 ms)
    }

    /** Frees the native state (also done by finish). */
    public void close() { net.close(); }

    public void process(float[] in, int off, int len, Sink sink) throws IOException {
        while (len > 0) {
            int chunk = Math.min(len, F * BATCH);
            int n = rs.push(in, off, chunk, rsOut, 0);
            feed(rsOut, n, sink);
            off += chunk; len -= chunk;
        }
    }

    public void finish(Sink sink) throws IOException {
        int n = rs.flush(rsOut, 0);
        feed(rsOut, n, sink);
        float[] z = new float[F];
        for (int i = 0; i < 3; i++) feed(z, F, sink); // push the delayed tail out
        if (fill > 0) { java.util.Arrays.fill(batch, fill, F * BATCH, 0); runBatch((fill + F - 1) / F, sink); fill = 0; }
        while (outFrames < inFrames) emitFrame(sink, true);
        net.close();
    }

    private void feed(float[] x, int n, Sink sink) throws IOException {
        int i = 0;
        while (i < n) {
            int c = Math.min(n - i, batch.length - fill);
            for (int k = 0; k < c; k++) batch[fill + k] = x[i + k] * 32768f;
            fill += c; i += c;
            if (fill == batch.length) { runBatch(BATCH, sink); fill = 0; }
        }
    }

    private void runBatch(int count, Sink sink) throws IOException {
        net.run(batch, count, vad);
        int start = 0;
        int total = count * F;
        if (dropLeft > 0) { int d = (int) Math.min(dropLeft, total); start = d; dropLeft -= d; }
        // re-cut into 480-sample frames after the delay drop
        for (int k = start; k < total; k++) {
            int slot = (int) (inFrames % ring);
            frames[slot][pending++] = batch[k] / 32768f;
            if (pending == F) {
                frameVad[slot] = vad[Math.min(count - 1, k / F)];
                inFrames++;
                pending = 0;
                if (inFrames - outFrames > LOOK) emitFrame(sink, false);
            }
        }
    }
    private int pending;

    private void emitFrame(Sink sink, boolean tail) throws IOException {
        int slot = (int) (outFrames % ring);
        boolean speech = false;
        for (long j = outFrames; j <= Math.min(inFrames - 1, outFrames + LOOK); j++)
            if (frameVad[(int) (j % ring)] > 0.35f) speech = true;
        if (speech) sinceSpeech = 0; else sinceSpeech++;
        float target = sinceSpeech <= HOLD ? 1f : floor;
        float g0 = gain;
        // fast open (one frame), slower close (about 100 ms)
        float g1 = target > gain ? target : gain + (target - gain) * 0.25f;
        float[] f = frames[slot];
        for (int i = 0; i < F; i++) outBuf[i] = f[i] * (g0 + (g1 - g0) * i / F);
        gain = g1;
        outFrames++;
        sink.write(outBuf, F);
    }
}
