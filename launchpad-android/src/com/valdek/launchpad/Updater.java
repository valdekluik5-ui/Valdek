package com.valdek.launchpad;

import android.content.Context;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;

/* Over-the-air updates for the Dragon page. The update channel is the dragon-update folder on the main branch of
   the Dragon repository. A newer index.html is downloaded in the background, checked against its SHA-256 sum in
   version.json and used from the next start. It is served at the same file:///android_asset/ address as the
   bundled page, so the saved data stays where it is. */
final class Updater {
    static final String CHANNEL = "https://raw.githubusercontent.com/valdekluik5-ui/Valdek/main/dragon-update/";
    private final File live, staged;
    private final String installed;

    Updater(Context ctx) {
        live = new File(ctx.getFilesDir(), "update");
        staged = new File(ctx.getFilesDir(), "update.new");
        String v = "0";
        try { v = ctx.getPackageManager().getPackageInfo(ctx.getPackageName(), 0).versionName; } catch (Exception ignored) { }
        installed = v;
    }

    /* switches in an update downloaded last time; returns its version, or null */
    String applyStaged() {
        File v = new File(staged, "version.txt");
        if (!v.exists()) return null;
        deleteAll(live);
        if (!staged.renameTo(live)) return null;
        return read(new File(live, "version.txt"));
    }

    /* the updated page, when it is newer than the page inside the APK */
    File page(String name) {
        String v = read(new File(live, "version.txt"));
        File f = new File(live, name);
        return v != null && newer(v, installed) && f.exists() ? f : null;
    }

    String current() {
        File f = page("index.html");
        return f != null ? read(new File(live, "version.txt")) : installed;
    }

    /* checks the channel; returns the version ready for the next start, or null. Runs off the main thread. */
    String check() {
        try {
            JSONObject m = new JSONObject(new String(get(CHANNEL + "version.json?t=" + System.currentTimeMillis()), "UTF-8"));
            String version = m.getString("version");
            if (!newer(version, current())) return null;
            if (newer(m.optString("minNative", "0"), installed)) return null;   // needs a new APK
            if (version.equals(read(new File(staged, "version.txt")))) return version;
            String sum = m.getJSONObject("files").getString("index.html");
            byte[] page = get(CHANNEL + "index.html?v=" + version);
            if (!hex(MessageDigest.getInstance("SHA-256").digest(page)).equalsIgnoreCase(sum)) return null;
            File tmp = new File(staged.getPath() + ".part");
            deleteAll(tmp);
            if (!tmp.mkdirs()) return null;
            write(new File(tmp, "index.html"), page);
            write(new File(tmp, "version.txt"), version.getBytes("UTF-8"));
            deleteAll(staged);
            return tmp.renameTo(staged) ? version : null;
        } catch (Exception e) {
            return null;
        }
    }

    static boolean newer(String a, String b) {
        String[] x = a.split("\\."), y = b.split("\\.");
        for (int i = 0; i < 3; i++) {
            int p = i < x.length ? num(x[i]) : 0, q = i < y.length ? num(y[i]) : 0;
            if (p != q) return p > q;
        }
        return false;
    }

    private static int num(String s) { try { return Integer.parseInt(s.trim()); } catch (Exception e) { return 0; } }

    private static byte[] get(String url) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(15000);
        c.setReadTimeout(60000);
        c.setUseCaches(false);
        try {
            if (c.getResponseCode() != 200) throw new Exception("HTTP " + c.getResponseCode());
            InputStream in = c.getInputStream();
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[16384];
            for (int n; (n = in.read(buf)) > 0; ) out.write(buf, 0, n);
            return out.toByteArray();
        } finally {
            c.disconnect();
        }
    }

    private static String hex(byte[] b) {
        StringBuilder s = new StringBuilder();
        for (byte x : b) s.append(String.format("%02x", x));
        return s.toString();
    }

    private static void write(File f, byte[] data) throws Exception {
        FileOutputStream out = new FileOutputStream(f);
        try { out.write(data); } finally { out.close(); }
    }

    private static String read(File f) {
        if (!f.exists()) return null;
        try {
            FileInputStream in = new FileInputStream(f);
            try {
                byte[] b = new byte[(int) f.length()];
                int n = in.read(b);
                return new String(b, 0, Math.max(n, 0), "UTF-8").trim();
            } finally { in.close(); }
        } catch (Exception e) {
            return null;
        }
    }

    private static void deleteAll(File f) {
        File[] kids = f.listFiles();
        if (kids != null) for (File k : kids) deleteAll(k);
        f.delete();
    }
}
