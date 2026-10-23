package com.valdek.launchpad;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.File;
import java.io.FileInputStream;

/* Full-screen wrapper around the Dragon page bundled in assets/. Progress, notes and the PIN live in the
   WebView's local storage, which is part of this app's private storage on the phone. */
public class MainActivity extends Activity {
    private static final int PICK_IMAGE = 1;
    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private Updater updater;
    private String applied;     // update switched in at this start, announced once the page has loaded

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        updater = new Updater(this);
        applied = updater.applyStaged();
        web = new WebView(this);
        web.setBackgroundColor(0xFF070505);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setSupportMultipleWindows(false);  // "Open" links (target=_blank) then come through shouldOverrideUrlLoading

        web.setWebViewClient(new WebViewClient() {
            /* the bundled page is replaced by a downloaded update when there is a newer one */
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                if ("file".equals(url.getScheme()) && "/android_asset/index.html".equals(url.getPath())) {
                    File f = updater.page("index.html");
                    if (f != null) try { return new WebResourceResponse("text/html", "utf-8", new FileInputStream(f)); } catch (Exception ignored) { }
                }
                return null;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                if (applied != null) { tell("applied", applied); applied = null; }
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                if ("file".equals(url.getScheme())) return false;
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, url));
                } catch (Exception ignored) {
                }
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                try {
                    startActivityForResult(params.createIntent(), PICK_IMAGE);
                } catch (Exception e) {
                    fileCallback = null;
                    return false;
                }
                return true;
            }
        });

        if (state != null) web.restoreState(state);
        else web.loadUrl("file:///android_asset/index.html");

        new Thread(new Runnable() {
            public void run() {
                final String ready = updater.check();
                if (ready != null) runOnUiThread(new Runnable() { public void run() { tell("ready", ready); } });
            }
        }).start();
    }

    private void tell(String what, String version) {
        web.evaluateJavascript("window.dragonUpdate&&dragonUpdate('" + what + "','" + version.replaceAll("[^0-9.]", "") + "')", null);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == PICK_IMAGE && fileCallback != null) {
            fileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data));
            fileCallback = null;
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemBars();
    }

    /* immersive: status and navigation bars stay hidden; a swipe from the edge shows them briefly */
    private void hideSystemBars() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onPause() {
        web.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
    }
}
