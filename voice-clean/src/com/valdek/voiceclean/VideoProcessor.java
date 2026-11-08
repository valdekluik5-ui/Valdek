package com.valdek.voiceclean;

import android.content.Context;
import android.media.MediaCodec;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.media.MediaMetadataRetriever;
import android.media.MediaMuxer;
import android.net.Uri;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.ShortBuffer;
import java.util.ArrayList;
import java.util.List;

/**
 * Removes background noise from a video's sound track. The picture is copied as it is (no re-encoding, no quality
 * loss); only the sound is decoded, cleaned by {@link Denoiser}, levelled and encoded again as AAC.
 */
public final class VideoProcessor {
    public interface Progress { void update(String stage, int percent); boolean cancelled(); }

    public static final class Options {
        public float strength = 0.6f;
        public boolean voiceBand = true;
        public boolean louder = true;
    }

    private static final long TIMEOUT = 10000;

    private final Context ctx;
    private final Progress progress;
    private long durationUs;

    public VideoProcessor(Context ctx, Progress progress) { this.ctx = ctx; this.progress = progress; }

    /** Writes the cleaned video (or .m4a for a sound-only file) to out. */
    public void run(Uri src, File out, Options opt) throws Exception {
        File pcm = new File(ctx.getCacheDir(), "decoded.pcm");
        File cleaned = new File(ctx.getCacheDir(), "cleaned.pcm");
        try {
            MediaExtractor probe = open(src);
            int audioTrack = -1, videoTrack = -1;
            for (int i = 0; i < probe.getTrackCount(); i++) {
                String mime = probe.getTrackFormat(i).getString(MediaFormat.KEY_MIME);
                if (mime == null) continue;
                if (mime.startsWith("audio/") && audioTrack < 0) audioTrack = i;
                if (mime.startsWith("video/") && videoTrack < 0) videoTrack = i;
                MediaFormat f = probe.getTrackFormat(i);
                if (f.containsKey(MediaFormat.KEY_DURATION)) durationUs = Math.max(durationUs, f.getLong(MediaFormat.KEY_DURATION));
            }
            probe.release();
            if (audioTrack < 0) throw new IOException("This video has no sound track.");

            // 1. decode the sound to mono 16-bit PCM in a temporary file
            long[] startUs = new long[1];
            int fs = decode(src, audioTrack, pcm, startUs);
            long samples = pcm.length() / 2;
            if (samples < fs / 10) throw new IOException("The sound track is too short or could not be read.");

            // 2. learn the background noise
            Denoiser d = new Denoiser(fs, opt.strength, opt.voiceBand);
            float[] buf = new float[8192];
            short[] sbuf = new short[8192];
            long done = 0;
            try (DataInputStream in = pcmIn(pcm)) {
                int got;
                while ((got = readShorts(in, sbuf)) > 0) {
                    check();
                    for (int i = 0; i < got; i++) buf[i] = sbuf[i] / 32768f;
                    d.analyze(buf, 0, got);
                    done += got;
                    progress.update("Listening for background noise", (int) (done * 100 / samples));
                }
            }
            d.finishAnalysis();

            // 3. clean it, and measure the speech level for the volume step
            float[] outBuf = new float[8192 + d.frameSize() * 2];
            Level level = new Level(fs);
            done = 0;
            try (DataInputStream in = pcmIn(pcm); OutputStream os = new BufferedOutputStream(new FileOutputStream(cleaned), 1 << 16)) {
                int got;
                while ((got = readShorts(in, sbuf)) > 0) {
                    check();
                    for (int i = 0; i < got; i++) buf[i] = sbuf[i] / 32768f;
                    int w = d.process(buf, 0, got, outBuf, 0);
                    writeFloats(os, outBuf, w, level);
                    done += got;
                    progress.update("Removing background noise", (int) (done * 100 / samples));
                }
                writeFloats(os, outBuf, d.flush(outBuf, 0), level);
            }
            pcm.delete();
            float gain = opt.louder ? level.gain() : 1f;

            // 4. encode the cleaned sound as AAC and put it back next to the original picture
            progress.update("Saving the new video", 0);
            mux(src, videoTrack, cleaned, fs, startUs[0], gain, out);
        } finally {
            pcm.delete();
            cleaned.delete();
        }
    }

    private void check() throws InterruptedException { if (progress.cancelled()) throw new InterruptedException("cancelled"); }

    private MediaExtractor open(Uri src) throws IOException {
        MediaExtractor ex = new MediaExtractor();
        ex.setDataSource(ctx, src, null);
        return ex;
    }

    // ---------------------------------------------------------------- decode

    private int decode(Uri src, int track, File pcm, long[] startUs) throws Exception {
        MediaExtractor ex = open(src);
        ex.selectTrack(track);
        MediaFormat fmt = ex.getTrackFormat(track);
        int fs = fmt.getInteger(MediaFormat.KEY_SAMPLE_RATE);
        int ch = fmt.getInteger(MediaFormat.KEY_CHANNEL_COUNT);
        boolean isFloat = false;
        MediaCodec dec = MediaCodec.createDecoderByType(fmt.getString(MediaFormat.KEY_MIME));
        dec.configure(fmt, null, null, 0);
        dec.start();
        MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
        boolean inDone = false, outDone = false, first = true;
        int decim = 1;
        long written = 0;
        float acc = 0; int accN = 0;
        startUs[0] = -1;
        try (OutputStream os = new BufferedOutputStream(new FileOutputStream(pcm), 1 << 16)) {
            byte[] ob = new byte[16384];
            while (!outDone) {
                check();
                if (!inDone) {
                    int ii = dec.dequeueInputBuffer(TIMEOUT);
                    if (ii >= 0) {
                        ByteBuffer ib = dec.getInputBuffer(ii);
                        int size = ex.readSampleData(ib, 0);
                        if (size < 0) {
                            dec.queueInputBuffer(ii, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM);
                            inDone = true;
                        } else {
                            long t = ex.getSampleTime();
                            dec.queueInputBuffer(ii, 0, size, t, 0);
                            if (durationUs > 0) progress.update("Reading the sound", (int) Math.min(99, t * 100 / durationUs));
                            ex.advance();
                        }
                    }
                }
                int oi = dec.dequeueOutputBuffer(info, TIMEOUT);
                if (oi == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    MediaFormat of = dec.getOutputFormat();
                    fs = of.getInteger(MediaFormat.KEY_SAMPLE_RATE);
                    ch = of.getInteger(MediaFormat.KEY_CHANNEL_COUNT);
                    isFloat = of.containsKey("pcm-encoding") && of.getInteger("pcm-encoding") == 4;
                } else if (oi >= 0) {
                    if (info.size > 0) {
                        if (first) {
                            first = false;
                            startUs[0] = info.presentationTimeUs;
                            decim = fs > 48000 ? (fs + 47999) / 48000 : 1;  // AAC encoders stop at 48 kHz
                        }
                        ByteBuffer bb = dec.getOutputBuffer(oi);
                        bb.position(info.offset).limit(info.offset + info.size);
                        bb = bb.slice().order(ByteOrder.nativeOrder());
                        int frames = info.size / ((isFloat ? 4 : 2) * ch);
                        int p = 0;
                        for (int f = 0; f < frames; f++) {
                            float m = 0;
                            for (int c = 0; c < ch; c++) {
                                m += isFloat ? bb.getFloat((f * ch + c) * 4) : bb.getShort((f * ch + c) * 2) / 32768f;
                            }
                            acc += m / ch; accN++;
                            if (accN == decim) {
                                int s = Math.round(acc / decim * 32767);
                                s = Math.max(-32768, Math.min(32767, s));
                                if (p + 2 > ob.length) { os.write(ob, 0, p); p = 0; }
                                ob[p++] = (byte) s; ob[p++] = (byte) (s >> 8);
                                acc = 0; accN = 0; written++;
                            }
                        }
                        os.write(ob, 0, p);
                    }
                    dec.releaseOutputBuffer(oi, false);
                    if ((info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outDone = true;
                }
            }
        } finally {
            try { dec.stop(); } catch (Exception ignored) { }
            dec.release();
            ex.release();
        }
        if (startUs[0] < 0) startUs[0] = 0;   // the muxer refuses negative times
        return fs / decim;
    }

    // ---------------------------------------------------------------- level

    /** Measures how loud the speech is, so quiet voices can be brought up to a normal level. */
    static final class Level {
        private final int block;
        private double blockSum; private int blockN;
        private final List<Float> blocks = new ArrayList<>();
        private float peak;
        Level(int fs) { block = fs / 20; }
        void add(float v) {
            blockSum += v * v; blockN++;
            float a = Math.abs(v); if (a > peak) peak = a;
            if (blockN == block) { blocks.add((float) Math.sqrt(blockSum / blockN)); blockSum = 0; blockN = 0; }
        }
        float gain() {
            if (blocks.isEmpty() || peak <= 0) return 1f;
            float[] b = new float[blocks.size()];
            for (int i = 0; i < b.length; i++) b[i] = blocks.get(i);
            java.util.Arrays.sort(b);
            float loud = b[(int) (b.length * 0.9)];   // typical level while someone talks
            if (loud <= 1e-5f) return 1f;
            float g = 0.18f / loud;                    // about -15 dBFS for speech
            return Math.max(1f, Math.min(g, 12f));     // only ever louder, at most +21 dB
        }
    }

    private static void writeFloats(OutputStream os, float[] y, int n, Level level) throws IOException {
        byte[] b = new byte[n * 4];
        ByteBuffer bb = ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN);
        for (int i = 0; i < n; i++) { bb.putFloat(y[i]); level.add(y[i]); }
        os.write(b);
    }

    /** Soft limiter so the louder voice never clips. */
    private static float limit(float v) {
        float a = Math.abs(v);
        if (a <= 0.8f) return v;
        float over = (a - 0.8f) / 0.2f;
        float l = 0.8f + 0.2f * (float) Math.tanh(over);
        return v < 0 ? -l : l;
    }

    // ---------------------------------------------------------------- encode + mux

    private static final class Sample { ByteBuffer data; long timeUs; int flags; }

    private void mux(Uri src, int videoTrack, File cleaned, int fs, long startUs, float gain, File out) throws Exception {
        // encode audio into memory (AAC at 128 kbit/s is about 1 MB per minute)
        MediaFormat af = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, fs, 1);
        af.setInteger(MediaFormat.KEY_AAC_PROFILE, 2); // AAC-LC
        af.setInteger(MediaFormat.KEY_BIT_RATE, 128000);
        af.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16384);
        MediaCodec enc = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC);
        enc.configure(af, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
        enc.start();
        List<Sample> audio = new ArrayList<>();
        MediaFormat encFormat = null;
        long total = cleaned.length() / 4, fed = 0;
        MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(cleaned), 1 << 16))) {
            boolean inDone = false, outDone = false;
            byte[] fb = new byte[4096 * 4];
            ByteBuffer fbb = ByteBuffer.wrap(fb).order(ByteOrder.LITTLE_ENDIAN);
            while (!outDone) {
                check();
                if (!inDone) {
                    int ii = enc.dequeueInputBuffer(TIMEOUT);
                    if (ii >= 0) {
                        ByteBuffer ib = enc.getInputBuffer(ii);
                        int frames = Math.min(ib.capacity() / 2, 4096);
                        int bytes = 0;
                        while (bytes < frames * 4) {
                            int r = in.read(fb, bytes, frames * 4 - bytes);
                            if (r < 0) break;
                            bytes += r;
                        }
                        int got = bytes / 4;
                        long t = startUs + fed * 1000000L / fs;
                        if (got == 0) {
                            enc.queueInputBuffer(ii, 0, 0, t, MediaCodec.BUFFER_FLAG_END_OF_STREAM);
                            inDone = true;
                        } else {
                            ib.clear();
                            ShortBuffer sb = ib.order(ByteOrder.nativeOrder()).asShortBuffer();
                            for (int i = 0; i < got; i++) {
                                float v = limit(fbb.getFloat(i * 4) * gain);
                                sb.put((short) Math.max(-32768, Math.min(32767, Math.round(v * 32767))));
                            }
                            enc.queueInputBuffer(ii, 0, got * 2, t, 0);
                            fed += got;
                            progress.update("Saving the new video", (int) (fed * 90 / Math.max(1, total)));
                        }
                    }
                }
                int oi = enc.dequeueOutputBuffer(info, TIMEOUT);
                if (oi == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    encFormat = enc.getOutputFormat();
                } else if (oi >= 0) {
                    ByteBuffer ob = enc.getOutputBuffer(oi);
                    if ((info.flags & MediaCodec.BUFFER_FLAG_CODEC_CONFIG) == 0 && info.size > 0) {
                        Sample s = new Sample();
                        s.data = ByteBuffer.allocate(info.size);
                        ob.position(info.offset).limit(info.offset + info.size);
                        s.data.put(ob); s.data.flip();
                        s.timeUs = info.presentationTimeUs; s.flags = 0;
                        audio.add(s);
                    }
                    enc.releaseOutputBuffer(oi, false);
                    if ((info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outDone = true;
                }
            }
        } finally {
            try { enc.stop(); } catch (Exception ignored) { }
            enc.release();
        }
        if (encFormat == null) throw new IOException("The phone's sound encoder did not start.");

        out.delete();
        MediaMuxer mx = new MediaMuxer(out.getAbsolutePath(), MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
        MediaExtractor ex = null;
        boolean started = false;
        try {
            int vOut = -1;
            if (videoTrack >= 0) {
                ex = open(src);
                ex.selectTrack(videoTrack);
                MediaFormat vf = ex.getTrackFormat(videoTrack);
                try {
                    vOut = mx.addTrack(vf);
                } catch (Exception e) {
                    throw new IOException("This video's picture format cannot be saved as MP4 on this phone ("
                            + vf.getString(MediaFormat.KEY_MIME) + ").");
                }
                mx.setOrientationHint(rotation(src));
            }
            int aOut = mx.addTrack(encFormat);
            mx.start();
            started = true;

            int maxSize = 8 << 20;
            if (ex != null) {
                MediaFormat vf = ex.getTrackFormat(videoTrack);
                if (vf.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) maxSize = Math.max(maxSize, vf.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE));
            }
            ByteBuffer vb = ex != null ? ByteBuffer.allocateDirect(maxSize) : null;
            MediaCodec.BufferInfo vi = new MediaCodec.BufferInfo();
            int ai = 0;
            ByteBuffer ab = ByteBuffer.allocateDirect(64 * 1024);
            boolean vDone = ex == null;
            long vTime = 0;
            if (!vDone) vTime = ex.getSampleTime();
            while (ai < audio.size() || !vDone) {
                check();
                boolean writeAudio = ai < audio.size() && (vDone || audio.get(ai).timeUs <= vTime);
                if (writeAudio) {
                    Sample s = audio.get(ai);
                    audio.set(ai++, null);   // free memory as we go
                    if (s.data.remaining() > ab.capacity()) ab = ByteBuffer.allocateDirect(s.data.remaining());
                    ab.clear();
                    ab.put(s.data);
                    ab.flip();
                    MediaCodec.BufferInfo bi = new MediaCodec.BufferInfo();
                    bi.set(0, ab.remaining(), s.timeUs, 0);
                    mx.writeSampleData(aOut, ab, bi);
                    progress.update("Saving the new video", 90 + ai * 10 / Math.max(1, audio.size()));
                } else {
                    vb.clear();
                    int size = ex.readSampleData(vb, 0);
                    if (size < 0) { vDone = true; continue; }
                    int fl = (ex.getSampleFlags() & MediaExtractor.SAMPLE_FLAG_SYNC) != 0 ? MediaCodec.BUFFER_FLAG_KEY_FRAME : 0;
                    vi.set(0, size, ex.getSampleTime(), fl);
                    mx.writeSampleData(vOut, vb, vi);
                    if (!ex.advance()) vDone = true; else vTime = ex.getSampleTime();
                }
            }
        } finally {
            if (started) { try { mx.stop(); } catch (Exception ignored) { } }
            mx.release();
            if (ex != null) ex.release();
        }
    }

    private int rotation(Uri src) {
        MediaMetadataRetriever r = new MediaMetadataRetriever();
        try {
            r.setDataSource(ctx, src);
            String s = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION);
            return s == null ? 0 : Integer.parseInt(s);
        } catch (Exception e) {
            return 0;
        } finally {
            try { r.release(); } catch (Exception ignored) { }
        }
    }

    // ---------------------------------------------------------------- pcm files

    private static DataInputStream pcmIn(File f) throws IOException {
        return new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 16));
    }

    private static final byte[] RB = new byte[16384];

    private static int readShorts(InputStream in, short[] dst) throws IOException {
        int want = Math.min(dst.length * 2, RB.length), got = 0;
        while (got < want) {
            int r = in.read(RB, got, want - got);
            if (r < 0) break;
            got += r;
        }
        int n = got / 2;
        for (int i = 0; i < n; i++) dst[i] = (short) ((RB[2 * i] & 0xff) | (RB[2 * i + 1] << 8));
        return n;
    }

    public static void copy(InputStream in, OutputStream out) throws IOException {
        byte[] b = new byte[1 << 16];
        int r;
        while ((r = in.read(b)) > 0) out.write(b, 0, r);
    }
}
