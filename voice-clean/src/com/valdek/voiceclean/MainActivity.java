package com.valdek.voiceclean;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.MediaController;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.VideoView;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;

public class MainActivity extends Activity {
    private static final int PICK = 1, SAVE = 2;
    private static final int BG = 0xFF0E1116, CARD = 0xFF181C24, TEXT = 0xFFE8EAF0, DIM = 0xFF9AA3B2, ACCENT = 0xFF35C28A;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private Uri source;
    private String sourceName = "video";
    private File result;
    private volatile boolean cancel;
    private Thread worker;

    private TextView fileText, strengthText, stageText, resultText;
    private SeekBar strength;
    private CheckBox voiceBand, louder;
    private Button pickBtn, cleanBtn, cancelBtn, playClean, playOrig, saveBtn, shareBtn;
    private ProgressBar bar;
    private LinearLayout resultBox, progressBox;
    private VideoView player;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        buildUi();
        handleIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        handleIntent(intent);
    }

    private void handleIntent(Intent in) {
        if (in == null) return;
        Uri u = null;
        if (Intent.ACTION_SEND.equals(in.getAction())) u = in.getParcelableExtra(Intent.EXTRA_STREAM);
        else if (Intent.ACTION_VIEW.equals(in.getAction())) u = in.getData();
        if (u != null && worker == null) setSource(u);
    }

    // ---------------------------------------------------------------- layout

    private int dp(float v) { return (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, getResources().getDisplayMetrics()); }

    private TextView text(String s, float sp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        if (bold) t.setTypeface(Typeface.DEFAULT_BOLD);
        return t;
    }

    private Button button(String s, boolean primary) {
        Button btn = new Button(this);
        btn.setText(s);
        btn.setAllCaps(false);
        btn.setTextSize(16);
        btn.setTextColor(primary ? 0xFF06140E : TEXT);
        GradientDrawable g = new GradientDrawable();
        g.setCornerRadius(dp(12));
        g.setColor(primary ? ACCENT : 0xFF262C38);
        btn.setBackground(g);
        btn.setPadding(dp(16), dp(12), dp(16), dp(12));
        return btn;
    }

    private LinearLayout card() {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(16), dp(16), dp(16), dp(16));
        GradientDrawable g = new GradientDrawable();
        g.setCornerRadius(dp(16));
        g.setColor(CARD);
        c.setBackground(g);
        return c;
    }

    private void add(LinearLayout parent, View v, int topDp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(topDp);
        parent.addView(v, lp);
    }

    private LinearLayout row(View a, View b) {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams la = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        la.rightMargin = dp(6);
        LinearLayout.LayoutParams lb = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        lb.leftMargin = dp(6);
        r.addView(a, la);
        r.addView(b, lb);
        return r;
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        scroll.setFillViewport(true);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(24), dp(16), dp(32));
        scroll.addView(root);

        add(root, text("Voice Clean", 28, TEXT, true), 0);
        add(root, text("Removes background noise from a video and keeps the voice of the person talking. The picture is not changed.", 15, DIM, false), 6);

        // 1. pick
        LinearLayout c1 = card();
        add(c1, text("1. Video", 13, DIM, true), 0);
        fileText = text("No video chosen yet", 16, TEXT, false);
        add(c1, fileText, 6);
        pickBtn = button("Choose video", false);
        pickBtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { pick(); } });
        add(c1, pickBtn, 12);
        add(root, c1, 20);

        // 2. settings
        LinearLayout c2 = card();
        add(c2, text("2. Settings", 13, DIM, true), 0);
        strengthText = text("", 16, TEXT, false);
        add(c2, strengthText, 6);
        strength = new SeekBar(this);
        strength.setMax(100);
        strength.setProgress(60);
        strength.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onProgressChanged(SeekBar s, int p, boolean user) { showStrength(); }
            public void onStartTrackingTouch(SeekBar s) { }
            public void onStopTrackingTouch(SeekBar s) { }
        });
        add(c2, strength, 4);
        add(c2, text("Higher removes more noise; too high can make the voice sound thin.", 13, DIM, false), 2);
        showStrength();
        voiceBand = new CheckBox(this);
        voiceBand.setText("Cut rumble and hiss outside the voice range");
        voiceBand.setTextColor(TEXT);
        voiceBand.setChecked(true);
        add(c2, voiceBand, 10);
        louder = new CheckBox(this);
        louder.setText("Make a quiet voice louder");
        louder.setTextColor(TEXT);
        louder.setChecked(true);
        add(c2, louder, 2);
        add(root, c2, 14);

        // 3. run
        cleanBtn = button("Remove background noise", true);
        cleanBtn.setEnabled(false);
        cleanBtn.setAlpha(0.5f);
        cleanBtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { startClean(); } });
        add(root, cleanBtn, 18);

        progressBox = new LinearLayout(this);
        progressBox.setOrientation(LinearLayout.VERTICAL);
        stageText = text("", 15, TEXT, false);
        add(progressBox, stageText, 0);
        bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        bar.setMax(100);
        add(progressBox, bar, 8);
        cancelBtn = button("Cancel", false);
        cancelBtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { cancel = true; } });
        add(progressBox, cancelBtn, 10);
        progressBox.setVisibility(View.GONE);
        add(root, progressBox, 14);

        // 4. result
        resultBox = card();
        add(resultBox, text("3. Result", 13, DIM, true), 0);
        resultText = text("", 15, TEXT, false);
        add(resultBox, resultText, 6);
        FrameLayout frame = new FrameLayout(this);
        frame.setBackgroundColor(Color.BLACK);
        player = new VideoView(this);
        MediaController mc = new MediaController(this);
        mc.setAnchorView(player);
        player.setMediaController(mc);
        frame.addView(player, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(240), Gravity.CENTER));
        add(resultBox, frame, 10);
        playClean = button("▶ Cleaned", true);
        playOrig = button("▶ Original", false);
        playClean.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { play(Uri.fromFile(result)); } });
        playOrig.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { play(source); } });
        add(resultBox, row(playClean, playOrig), 10);
        saveBtn = button("Save to phone", true);
        shareBtn = button("Share", false);
        saveBtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { save(); } });
        shareBtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { share(); } });
        add(resultBox, row(saveBtn, shareBtn), 10);
        resultBox.setVisibility(View.GONE);
        add(root, resultBox, 14);

        setContentView(scroll);
    }

    private void showStrength() { strengthText.setText("Noise removal: " + strength.getProgress() + "%"); }

    // ---------------------------------------------------------------- actions

    private void pick() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("video/*");
        i.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"video/*", "audio/*"});
        startActivityForResult(i, PICK);
    }

    private void setSource(Uri u) {
        source = u;
        sourceName = "video";
        try (Cursor c = getContentResolver().query(u, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (c != null && c.moveToFirst() && c.getString(0) != null) sourceName = c.getString(0);
        } catch (Exception ignored) { }
        if ("file".equals(u.getScheme()) && u.getLastPathSegment() != null) sourceName = u.getLastPathSegment();
        fileText.setText(sourceName);
        cleanBtn.setEnabled(true);
        cleanBtn.setAlpha(1f);
        resultBox.setVisibility(View.GONE);
        player.stopPlayback();
    }

    private String outName() {
        String base = sourceName;
        int dot = base.lastIndexOf('.');
        if (dot > 0) base = base.substring(0, dot);
        return base + "_clean.mp4";
    }

    private void startClean() {
        if (source == null || worker != null) return;
        cancel = false;
        player.stopPlayback();
        resultBox.setVisibility(View.GONE);
        progressBox.setVisibility(View.VISIBLE);
        stageText.setText("Starting…");
        bar.setProgress(0);
        setBusy(true);
        final VideoProcessor.Options opt = new VideoProcessor.Options();
        opt.strength = strength.getProgress() / 100f;
        opt.voiceBand = voiceBand.isChecked();
        opt.louder = louder.isChecked();
        final Uri src = source;
        final File out = new File(getCacheDir(), "out/" + outName());
        File dir = out.getParentFile();
        if (dir != null) {
            dir.mkdirs();
            File[] old = dir.listFiles();
            if (old != null) for (File f : old) f.delete();
        }
        worker = new Thread(new Runnable() { public void run() {
            String error = null;
            long t0 = System.currentTimeMillis();
            try {
                new VideoProcessor(MainActivity.this, new VideoProcessor.Progress() {
                    private long last;
                    private String lastStage;
                    public void update(String stage, int pct) {
                        long now = System.currentTimeMillis();
                        if (now - last < 150 && stage.equals(lastStage)) return;
                        last = now; lastStage = stage;
                        ui.post(new Runnable() { public void run() { stageText.setText(stage + " – " + pct + "%"); bar.setProgress(pct); } });
                    }
                    public boolean cancelled() { return cancel; }
                }).run(src, out, opt);
            } catch (InterruptedException e) {
                error = "";
            } catch (Throwable e) {
                error = e.getMessage() != null ? e.getMessage() : e.toString();
            }
            final String err = error;
            final long secs = (System.currentTimeMillis() - t0) / 1000;
            ui.post(new Runnable() { public void run() { finished(out, err, secs); } });
        } }, "clean");
        worker.start();
    }

    private void finished(File out, String error, long secs) {
        worker = null;
        setBusy(false);
        progressBox.setVisibility(View.GONE);
        if (error != null) {
            out.delete();
            if (!error.isEmpty()) Toast.makeText(this, "Could not clean this video: " + error, Toast.LENGTH_LONG).show();
            return;
        }
        result = out;
        resultText.setText("Done in " + secs + " s. Listen to it, then save or share it.\n" + out.getName());
        resultBox.setVisibility(View.VISIBLE);
        play(Uri.fromFile(result));
    }

    private void setBusy(boolean busy) {
        if (busy) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        cleanBtn.setEnabled(!busy);
        cleanBtn.setAlpha(busy ? 0.5f : 1f);
        pickBtn.setEnabled(!busy);
        strength.setEnabled(!busy);
        voiceBand.setEnabled(!busy);
        louder.setEnabled(!busy);
    }

    private void play(Uri u) {
        if (u == null) return;
        player.setVideoURI(u);
        player.setOnPreparedListener(new android.media.MediaPlayer.OnPreparedListener() { public void onPrepared(android.media.MediaPlayer mp) { player.start(); } });
        player.requestFocus();
    }

    private void save() {
        if (result == null) return;
        Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("video/mp4");
        i.putExtra(Intent.EXTRA_TITLE, result.getName());
        startActivityForResult(i, SAVE);
    }

    private void share() {
        if (result == null) return;
        Uri u = Uri.parse("content://" + ShareProvider.AUTHORITY + "/" + Uri.encode(result.getName()));
        Intent i = new Intent(Intent.ACTION_SEND);
        i.setType("video/mp4");
        i.putExtra(Intent.EXTRA_STREAM, u);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivity(Intent.createChooser(i, "Share cleaned video"));
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (res != RESULT_OK || data == null || data.getData() == null) return;
        if (req == PICK) {
            setSource(data.getData());
        } else if (req == SAVE && result != null) {
            final Uri dst = data.getData();
            final File src = result;
            Toast.makeText(this, "Saving…", Toast.LENGTH_SHORT).show();
            new Thread(new Runnable() { public void run() {
                String msg;
                try (InputStream in = new FileInputStream(src); OutputStream os = getContentResolver().openOutputStream(dst)) {
                    VideoProcessor.copy(in, os);
                    msg = "Saved";
                } catch (Exception e) {
                    msg = "Could not save: " + e.getMessage();
                }
                final String m = msg;
                ui.post(new Runnable() { public void run() { Toast.makeText(MainActivity.this, m, Toast.LENGTH_LONG).show(); } });
            } }).start();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (player != null && player.isPlaying()) player.pause();
    }

    @Override
    protected void onDestroy() {
        cancel = true;
        super.onDestroy();
    }
}
