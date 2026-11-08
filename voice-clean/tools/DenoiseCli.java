import com.valdek.voiceclean.Denoiser;
import java.io.*;
import java.nio.*;
import java.nio.file.*;

/** Desktop check of the engine: DenoiseCli <rate> <strength 0..1> <in.s16le mono> <out.s16le> */
public class DenoiseCli {
    public static void main(String[] a) throws Exception {
        int fs = Integer.parseInt(a[0]);
        float strength = Float.parseFloat(a[1]);
        byte[] raw = Files.readAllBytes(Paths.get(a[2]));
        ShortBuffer sb = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer();
        float[] x = new float[sb.remaining()];
        for (int i = 0; i < x.length; i++) x[i] = sb.get(i) / 32768f;
        long t0 = System.nanoTime();
        Denoiser d = new Denoiser(fs, strength, true);
        for (int i = 0; i < x.length; i += 4096) d.analyze(x, i, Math.min(4096, x.length - i));
        d.finishAnalysis();
        float[] y = new float[x.length + d.frameSize() * 2];
        int w = 0;
        for (int i = 0; i < x.length; i += 4096) w += d.process(x, i, Math.min(4096, x.length - i), y, w);
        w += d.flush(y, w);
        System.err.printf("in %d out %d samples, %.2fx realtime%n", x.length, w, (x.length / (double) fs) / ((System.nanoTime() - t0) / 1e9));
        ByteBuffer ob = ByteBuffer.allocate(w * 2).order(ByteOrder.LITTLE_ENDIAN);
        for (int i = 0; i < w; i++) ob.putShort((short) Math.max(-32768, Math.min(32767, Math.round(y[i] * 32768))));
        Files.write(Paths.get(a[3]), ob.array());
    }
}
