import com.valdek.voiceclean.NeuralCleaner;
import java.io.*;
import java.nio.*;
import java.nio.file.*;

/** Desktop check: NeuralCli <rate> <strength> <in.s16le mono> <out.s16le, 48 kHz> */
public class NeuralCli {
    public static void main(String[] a) throws Exception {
        int fs = Integer.parseInt(a[0]);
        byte[] raw = Files.readAllBytes(Paths.get(a[2]));
        ShortBuffer sb = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer();
        float[] x = new float[sb.remaining()];
        for (int i = 0; i < x.length; i++) x[i] = sb.get(i) / 32768f;
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        long t0 = System.nanoTime();
        NeuralCleaner c = new NeuralCleaner(fs, Float.parseFloat(a[1]));
        NeuralCleaner.Sink sink = (buf, n) -> {
            ByteBuffer ob = ByteBuffer.allocate(n * 2).order(ByteOrder.LITTLE_ENDIAN);
            for (int i = 0; i < n; i++) ob.putShort((short) Math.max(-32768, Math.min(32767, Math.round(buf[i] * 32768))));
            bo.write(ob.array(), 0, n * 2);
        };
        for (int i = 0; i < x.length; i += 4096) c.process(x, i, Math.min(4096, x.length - i), sink);
        c.finish(sink);
        System.err.printf("%.1fx realtime%n", (x.length / (double) fs) / ((System.nanoTime() - t0) / 1e9));
        Files.write(Paths.get(a[3]), bo.toByteArray());
    }
}
