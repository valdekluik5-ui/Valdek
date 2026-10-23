using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace Dragon
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.ThreadException += (s, e) => MainForm.Fail("Something went wrong", e.Exception);
            AppDomain.CurrentDomain.UnhandledException += (s, e) => MainForm.Fail("Something went wrong", e.ExceptionObject as Exception);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    /* Window layout and open tabs, remembered between runs in %LOCALAPPDATA%\Dragon\window.json */
    class WindowState
    {
        public int X = -1, Y = -1, W = 1400, H = 900, Split = 520, ActiveTab = 0;
        public bool Maximized = true, TrainingHidden = false;
        public string TrainingUrl = "";                                  // single page from versions before tabs
        public List<string> Tabs = new List<string>();
        public List<string> TranslateSites = new List<string>();         // sites always shown in English
    }

    class Tab
    {
        public int Id;
        public WebView2 View;
        public string Title = "", Icon = "";
        public bool Loading;
    }

    /* Dragon workplace: the Dragon app on the left, a tabbed browser on the right.
       The browser bar (tabs, address, price bar) is a small page styled like Dragon; links from Dragon open in tabs. */
    class MainForm : Form
    {
        const string Host = "dragon.example";
        const int MaxTabs = 15;
        static readonly Color Bg = Color.FromArgb(7, 5, 5), Ink = Color.FromArgb(240, 234, 234);
        static readonly string DataDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Dragon");
        static readonly string SafeGraphicsFlag = Path.Combine(DataDir, "safe-graphics");
        static readonly HttpClient http = new HttpClient { Timeout = TimeSpan.FromSeconds(15) };

        readonly string stateFile = Path.Combine(DataDir, "window.json");
        readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 8 * 1024 * 1024 };
        WindowState state = new WindowState();

        readonly SplitContainer split = new SplitContainer();
        readonly WebView2 dragon = new WebView2();
        readonly WebView2 bar = new WebView2();                         // browser bar
        readonly Panel content = new Panel();                            // tab pages
        readonly Button showBrowser = new Button();
        readonly List<Tab> tabs = new List<Tab>();
        Tab active;
        int nextTabId = 1;
        CoreWebView2Environment env;
        CoreWebView2Controller scout;                                    // hidden browser that looks up reference prices

        bool pageLoaded, barReady, locked = true, browserStarted;
        string skin = "crimson", accent = "#d42a2a";
        int lookupId;
        object lastPrice;                                                // what the price bar shows
        string lastQuery = "";
        readonly Dictionary<string, (List<decimal> used, List<decimal> fresh)> priceCache = new Dictionary<string, (List<decimal>, List<decimal>)>();
        readonly Dictionary<string, string> translations = new Dictionary<string, string>();
        decimal eurRate, usdRate;                                        // hryvnia per euro / dollar (National Bank of Ukraine)
        FormWindowState beforeFull; bool fullScreen;

        public MainForm()
        {
            LoadState();
            Text = "Dragon";
            BackColor = Bg;
            using (var s = typeof(MainForm).Assembly.GetManifestResourceStream("dragon.ico")) Icon = new Icon(s);
            StartPosition = FormStartPosition.Manual;
            var area = Screen.FromPoint(new Point(Math.Max(0, state.X), Math.Max(0, state.Y))).WorkingArea;
            Bounds = state.X < 0 ? new Rectangle(area.X + 40, area.Y + 40, Math.Min(state.W, area.Width - 80), Math.Min(state.H, area.Height - 80))
                                 : new Rectangle(state.X, state.Y, state.W, state.H);
            if (state.Maximized) WindowState = FormWindowState.Maximized;
            MinimumSize = new Size(420, 500);

            split.Dock = DockStyle.Fill;
            split.BackColor = Color.FromArgb(40, 20, 20);
            split.Panel1.BackColor = Bg;
            split.Panel2.BackColor = Bg;
            split.SplitterWidth = 5;
            split.Panel1MinSize = 380;
            dragon.Dock = DockStyle.Fill;
            dragon.DefaultBackgroundColor = Bg;
            split.Panel1.Controls.Add(dragon);

            content.Dock = DockStyle.Fill;
            content.BackColor = Bg;
            content.Padding = new Padding(Px(8), 0, Px(8), Px(8));   // the page sits in a frame with rounded corners
            bar.Dock = DockStyle.Top;
            bar.Height = Px(80);
            bar.DefaultBackgroundColor = Bg;
            split.Panel2.Controls.Add(content);
            split.Panel2.Controls.Add(bar);
            Controls.Add(split);

            showBrowser.Text = "Browser ◂";
            showBrowser.FlatStyle = FlatStyle.Flat;
            showBrowser.FlatAppearance.BorderColor = Color.FromArgb(59, 29, 29);
            showBrowser.BackColor = Color.FromArgb(30, 14, 14);
            showBrowser.ForeColor = Ink;
            showBrowser.Font = new Font("Segoe UI", 9.5f, FontStyle.Bold);
            showBrowser.AutoSize = true;
            showBrowser.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            showBrowser.Visible = false;
            showBrowser.Click += (s, e) => SetBrowserHidden(false);
            Controls.Add(showBrowser);
            showBrowser.BringToFront();

            Load += async (s, e) => await StartAsync();
            Shown += (s, e) => ApplyLock();
            Resize += (s, e) => showBrowser.Location = new Point(ClientSize.Width - showBrowser.Width - 70, 8);
            FormClosing += (s, e) => SaveState();
        }

        async Task StartAsync()
        {
            var baseDir = AppDomain.CurrentDomain.BaseDirectory;
            var appDir = Path.Combine(baseDir, "app");
            if (!File.Exists(Path.Combine(appDir, "index.html")))
            {
                MessageBox.Show(this, "Dragon's files are missing next to Dragon.exe.\n\nRun Dragon-Setup.exe again to reinstall.", "Dragon", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                Close();
                return;
            }
            bool safe = File.Exists(SafeGraphicsFlag);
            try
            {
                Directory.CreateDirectory(DataDir);
                var arch = Environment.Is64BitProcess ? "win-x64" : "win-x86";
                foreach (var dir in new[] { baseDir, Path.Combine(baseDir, "runtimes", arch, "native") })
                    if (File.Exists(Path.Combine(dir, "WebView2Loader.dll"))) { CoreWebView2Environment.SetLoaderDllFolderPath(dir); break; }
                // safe graphics turns GPU drawing off, for laptops whose driver shows WebView2 as a black area (slower)
                var options = new CoreWebView2EnvironmentOptions(safe ? "--disable-gpu --disable-gpu-compositing" : null);
                env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(DataDir, "WebView2"), options);
                await dragon.EnsureCoreWebView2Async(env);
                await bar.EnsureCoreWebView2Async(env);
                scout = await env.CreateCoreWebView2ControllerAsync(Handle);
                scout.IsVisible = false;
                scout.Bounds = new Rectangle(0, 0, 1280, 900);
            }
            catch (WebView2RuntimeNotFoundException)
            {
                MessageBox.Show(this, "Dragon needs the Microsoft Edge WebView2 Runtime, which is part of Windows 11 and most Windows 10 PCs.\n\nThe download page will open now. Install the Evergreen Runtime, then start Dragon again.",
                    "Dragon", MessageBoxButtons.OK, MessageBoxIcon.Information);
                OpenExternal("https://developer.microsoft.com/microsoft-edge/webview2/");
                Close();
                return;
            }
            catch (Exception ex)
            {
                Fail("Dragon could not start its browser engine", ex);
                Close();
                return;
            }

            // the Dragon app, served from the app folder as a secure https origin so its storage persists
            var core = dragon.CoreWebView2;
            core.SetVirtualHostNameToFolderMapping(Host, appDir, CoreWebView2HostResourceAccessKind.Allow);
            core.Settings.IsStatusBarEnabled = false;
            core.NewWindowRequested += (s, e) => { e.Handled = true; OpenFromDragon(e.Uri); };
            core.NavigationStarting += (s, e) =>
            {
                if (e.Uri.StartsWith("https://" + Host + "/", StringComparison.OrdinalIgnoreCase)) return;
                e.Cancel = true;
                OpenFromDragon(e.Uri);
            };
            core.NavigationCompleted += (s, e) => { if (e.IsSuccess) pageLoaded = true; else Log("Dragon page failed to load: " + e.WebErrorStatus); };
            core.ProcessFailed += (s, e) => { Log("Browser process failed: " + e.ProcessFailedKind); try { core.Reload(); } catch { } };
            core.WebMessageReceived += (s, e) => OnDragonMessage(e);
            core.Navigate("https://" + Host + "/index.html");

            // the browser bar
            var bc = bar.CoreWebView2;
            bc.SetVirtualHostNameToFolderMapping(Host, appDir, CoreWebView2HostResourceAccessKind.Allow);
            bc.Settings.AreDefaultContextMenusEnabled = false;
            bc.Settings.IsZoomControlEnabled = false;
            bc.WebMessageReceived += (s, e) => OnBarMessage(e);
            bc.Navigate("https://" + Host + "/browser.html");

            LoadRates();

            // if the page has not appeared after a while, offer safe graphics
            await Task.Delay(12000);
            if (!pageLoaded && !IsDisposed)
            {
                var msg = safe ? "Dragon's page still did not load, even in safe graphics mode.\n\nThe details are in the log file. Open its folder?"
                               : "Dragon's page did not load. Some graphics drivers show it as a black window.\n\nRestart Dragon in safe graphics mode?";
                if (MessageBox.Show(this, msg, "Dragon", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                {
                    if (safe) OpenExternal(DataDir);
                    else { File.WriteAllText(SafeGraphicsFlag, "on"); Application.Restart(); }
                }
            }
        }

        /* ---------- messages ---------- */
        Dictionary<string, object> Msg(CoreWebView2WebMessageReceivedEventArgs e)
        {
            try { return json.Deserialize<Dictionary<string, object>>(e.WebMessageAsJson) ?? new Dictionary<string, object>(); }
            catch { return new Dictionary<string, object>(); }
        }
        static string Str(Dictionary<string, object> m, string k) => m.TryGetValue(k, out var v) && v != null ? Convert.ToString(v, CultureInfo.InvariantCulture) : "";

        void OnDragonMessage(CoreWebView2WebMessageReceivedEventArgs e)
        {
            string text = null;
            try { text = e.TryGetWebMessageAsString(); } catch { }
            if (text == "lock") { locked = true; ApplyLock(); return; }
            if (text == "unlock") { locked = false; ApplyLock(); return; }
            var m = Msg(e);
            if (Str(m, "type") == "skin")
            {
                skin = Str(m, "skin"); accent = Str(m, "accent");
                Post(bar, new { type = "theme", skin, accent });
                ApplyFrameColours();
            }
        }

        void OnBarMessage(CoreWebView2WebMessageReceivedEventArgs e)
        {
            var m = Msg(e);
            switch (Str(m, "type"))
            {
                case "ready":
                    barReady = true;
                    Post(bar, new { type = "theme", skin, accent });
                    Post(bar, new { type = "safe", safe = File.Exists(SafeGraphicsFlag) });
                    Post(bar, new { type = "rates", eur = eurRate });
                    PushTabs();
                    Post(bar, new { type = "price", price = lastPrice });
                    break;
                case "height": if (int.TryParse(Str(m, "h"), out var h)) bar.Height = Math.Max(Px(76), Math.Min(Px(600), h)); break;  // already in screen pixels
                case "newtab": _ = AddTab(null, true); break;
                case "close": if (int.TryParse(Str(m, "id"), out var c)) CloseTab(tabs.FirstOrDefault(t => t.Id == c)); break;
                case "select": if (int.TryParse(Str(m, "id"), out var sId)) Activate(tabs.FirstOrDefault(t => t.Id == sId)); break;
                case "back": if (active?.View.CoreWebView2?.CanGoBack == true) active.View.CoreWebView2.GoBack(); break;
                case "fwd": if (active?.View.CoreWebView2?.CanGoForward == true) active.View.CoreWebView2.GoForward(); break;
                case "reload": active?.View.CoreWebView2?.Reload(); break;
                case "nav": NavigateActive(AddressToUrl(Str(m, "text"))); break;
                case "external": { var u = active?.View.Source?.ToString(); if (IsWeb(u)) OpenExternal(u); } break;
                case "en": ToggleEnglish(); break;
                case "hide": SetBrowserHidden(true); break;
                case "fullscreen": ToggleFullScreen(); break;
                case "openprice": OpenPriceSearch(Str(m, "which")); break;
                case "gfx":
                    var wantSafe = Str(m, "safe") == "True";
                    if (wantSafe == File.Exists(SafeGraphicsFlag)) break;
                    if (wantSafe) File.WriteAllText(SafeGraphicsFlag, "on"); else File.Delete(SafeGraphicsFlag);
                    SaveState();
                    Application.Restart();
                    break;
            }
        }

        void Post(WebView2 view, object data) { try { view.CoreWebView2?.PostWebMessageAsJson(json.Serialize(data)); } catch { } }

        /* ---------- lock ---------- */
        /* locked: Dragon's PIN screen fills the window; the browser stays hidden and its tabs unloaded until the first unlock */
        void ApplyLock()
        {
            if (locked) { split.Panel2Collapsed = true; showBrowser.Visible = false; return; }
            if (!browserStarted && env != null) { browserStarted = true; _ = RestoreTabs(); }
            SetBrowserHidden(state.TrainingHidden);
            try { if (!split.Panel2Collapsed) split.SplitterDistance = Math.Max(split.Panel1MinSize, Math.Min(state.Split, split.Width - 300)); } catch { }
        }

        void SetBrowserHidden(bool hidden)
        {
            state.TrainingHidden = hidden;
            if (locked) return;
            split.Panel2Collapsed = hidden;
            showBrowser.Visible = hidden;
            showBrowser.Location = new Point(ClientSize.Width - showBrowser.Width - 70, 8);
        }

        void ToggleFullScreen()
        {
            fullScreen = !fullScreen;
            if (fullScreen) { beforeFull = WindowState; FormBorderStyle = FormBorderStyle.None; WindowState = FormWindowState.Normal; WindowState = FormWindowState.Maximized; }
            else { FormBorderStyle = FormBorderStyle.Sizable; WindowState = beforeFull; }
        }

        /* keys reach the form even while a page has focus */
        protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
        {
            switch (keyData)
            {
                case Keys.F11: ToggleFullScreen(); return true;
                case Keys.Escape when fullScreen: ToggleFullScreen(); return true;
                case Keys.Control | Keys.B: if (!locked) SetBrowserHidden(!state.TrainingHidden); return true;
                case Keys.Control | Keys.T: if (!locked) { SetBrowserHidden(false); _ = AddTab(null, true); } return true;
                case Keys.Control | Keys.W: if (!locked && active != null) CloseTab(active); return true;
                case Keys.Control | Keys.L: if (!locked) { bar.Focus(); Post(bar, new { type = "focusaddr" }); } return true;
                case Keys.F5: if (!locked) active?.View.CoreWebView2?.Reload(); return true;
            }
            return base.ProcessCmdKey(ref msg, keyData);
        }

        /* ---------- tabs ---------- */
        string NewTabUrl() => "https://" + Host + "/newtab.html?skin=" + Uri.EscapeDataString(skin) + "&accent=" + Uri.EscapeDataString(accent);
        static bool IsNewTab(string url) => (url ?? "").StartsWith("https://" + Host + "/newtab.html", StringComparison.OrdinalIgnoreCase);

        async Task RestoreTabs()
        {
            var urls = state.Tabs.Where(u => u != null).ToList();
            if (urls.Count == 0 && IsWeb(state.TrainingUrl)) urls.Add(state.TrainingUrl);
            if (urls.Count == 0) urls.Add("");
            var activeIndex = Math.Max(0, Math.Min(state.ActiveTab, urls.Count - 1));
            for (int i = 0; i < urls.Count; i++) await AddTab(IsWeb(urls[i]) ? urls[i] : null, i == activeIndex);
        }

        async Task<Tab> AddTab(string url, bool activate)
        {
            if (env == null) return null;
            var tab = new Tab { Id = nextTabId++, View = new WebView2 { Dock = DockStyle.Fill, DefaultBackgroundColor = Bg, Visible = false } };
            tab.View.SizeChanged += (s, e) => RoundCorners(tab.View);
            tabs.Add(tab);
            content.Controls.Add(tab.View);
            if (activate) Activate(tab);
            await tab.View.EnsureCoreWebView2Async(env);
            var c = tab.View.CoreWebView2;
            c.SetVirtualHostNameToFolderMapping(Host, Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "app"), CoreWebView2HostResourceAccessKind.Allow);
            c.Settings.IsStatusBarEnabled = true;
            await c.AddScriptToExecuteOnDocumentCreatedAsync(TranslatorScript);
            c.NewWindowRequested += (s, e) => { e.Handled = true; if (IsWeb(e.Uri)) _ = AddTab(e.Uri, true); };
            c.NavigationStarting += (s, e) => { tab.Loading = true; PushTabs(); };
            c.NavigationCompleted += (s, e) => { tab.Loading = false; PushTabs(); if (tab == active) CheckListing(tab); };
            c.SourceChanged += (s, e) => { PushTabs(); if (tab == active) CheckListing(tab); };
            c.DocumentTitleChanged += (s, e) => { tab.Title = c.DocumentTitle; PushTabs(); };
            c.FaviconChanged += (s, e) => { tab.Icon = c.FaviconUri ?? ""; PushTabs(); };
            c.DOMContentLoaded += async (s, e) => { if (WantsEnglish(tab)) try { await c.ExecuteScriptAsync("window.__dragonTr&&__dragonTr.start()"); } catch { } };
            c.WebMessageReceived += (s, e) => OnTabMessage(tab, e);
            c.Navigate(IsWeb(url) ? url : NewTabUrl());
            return tab;
        }

        /* screen pixels for a size in 100%-scale pixels (Windows display scaling) */
        int Px(int v) => (int)Math.Round(v * DeviceDpi / 96.0);

        /* frame and divider take the colours of the current Dragon look, so the browser blends in */
        static readonly Dictionary<string, Color> SkinBg = new Dictionary<string, Color>
        {
            ["crimson"] = Color.FromArgb(7, 5, 5), ["frost"] = Color.FromArgb(5, 8, 15), ["steel"] = Color.FromArgb(8, 5, 6),
            ["ember"] = Color.FromArgb(13, 9, 8), ["jade"] = Color.FromArgb(4, 8, 6)
        };
        void ApplyFrameColours()
        {
            var bg = SkinBg.TryGetValue(skin, out var c) ? c : Bg;
            Color acc;
            try { acc = ColorTranslator.FromHtml(accent); } catch { acc = Color.FromArgb(212, 42, 42); }
            content.BackColor = bg;
            split.Panel2.BackColor = bg;
            split.BackColor = Color.FromArgb(bg.R + (acc.R - bg.R) * 35 / 100, bg.G + (acc.G - bg.G) * 35 / 100, bg.B + (acc.B - bg.B) * 35 / 100);
            bar.DefaultBackgroundColor = bg;
        }

        /* rounded corners for a tab page */
        void RoundCorners(Control c)
        {
            var r = Px(12); var w = c.Width; var h = c.Height;
            if (w < r * 2 || h < r * 2) return;
            var path = new GraphicsPath();
            path.AddArc(0, 0, r * 2, r * 2, 180, 90);
            path.AddArc(w - r * 2, 0, r * 2, r * 2, 270, 90);
            path.AddArc(w - r * 2, h - r * 2, r * 2, r * 2, 0, 90);
            path.AddArc(0, h - r * 2, r * 2, r * 2, 90, 90);
            path.CloseFigure();
            var old = c.Region; c.Region = new Region(path); old?.Dispose();
        }

        void Activate(Tab tab)
        {
            if (tab == null) return;
            active = tab;
            foreach (var t in tabs) t.View.Visible = t == tab;
            tab.View.BringToFront();
            PushTabs();
            CheckListing(tab);
        }

        void CloseTab(Tab tab)
        {
            if (tab == null) return;
            var i = tabs.IndexOf(tab);
            tabs.Remove(tab);
            content.Controls.Remove(tab.View);
            tab.View.Dispose();
            if (tabs.Count == 0) { active = null; _ = AddTab(null, true); return; }
            if (tab == active) Activate(tabs[Math.Min(i, tabs.Count - 1)]);
            else PushTabs();
        }

        void PushTabs()
        {
            if (!barReady) return;
            Post(bar, new
            {
                type = "tabs",
                tabs = tabs.Select(t =>
                {
                    var u = t.View.Source?.ToString() ?? "";
                    return new
                    {
                        id = t.Id, active = t == active, loading = t.Loading, icon = IsNewTab(u) ? "" : t.Icon,
                        title = IsNewTab(u) ? "New tab" : t.Title, url = IsNewTab(u) ? "" : u,
                        canBack = t.View.CoreWebView2?.CanGoBack == true, canFwd = t.View.CoreWebView2?.CanGoForward == true,
                        english = WantsEnglish(t)
                    };
                }).ToList()
            });
        }

        /* links from Dragon: use the current tab if it is a new-tab page, otherwise open a new tab */
        void OpenFromDragon(string url)
        {
            if (locked) return;
            if (!IsWeb(url)) { if (!string.IsNullOrEmpty(url) && !url.StartsWith("about:")) OpenExternal(url); return; }
            SetBrowserHidden(false);
            if (active != null && (IsNewTab(active.View.Source?.ToString()) || tabs.Count >= MaxTabs)) NavigateActive(url);
            else _ = AddTab(url, true);
        }

        void NavigateActive(string url)
        {
            if (string.IsNullOrEmpty(url)) return;
            if (active?.View.CoreWebView2 == null) { _ = AddTab(url, true); return; }
            active.View.CoreWebView2.Navigate(url);
        }

        /* what was typed into the address bar: an address, or a Google search */
        static string AddressToUrl(string text)
        {
            text = (text ?? "").Trim();
            if (text.Length == 0) return null;
            if (IsWeb(text)) return text;
            if (!text.Contains(" ") && text.Contains(".") && !text.EndsWith(".")) return "https://" + text;
            return "https://www.google.com/search?q=" + Uri.EscapeDataString(text);
        }

        /* ---------- English: text in the page is translated in place, so the site keeps working ---------- */
        static string HostOf(string url) { try { return new Uri(url).Host.ToLowerInvariant(); } catch { return ""; } }
        static string SiteKey(string url) { var h = HostOf(url); return h.StartsWith("www.") ? h.Substring(4) : h; }
        bool WantsEnglish(Tab t) { var u = t?.View.Source?.ToString(); return IsWeb(u) && state.TranslateSites.Contains(SiteKey(u)); }

        async void ToggleEnglish()
        {
            var u = active?.View.Source?.ToString();
            if (!IsWeb(u) || active.View.CoreWebView2 == null) return;
            var site = SiteKey(u);
            var on = !state.TranslateSites.Contains(site);
            if (on) state.TranslateSites.Add(site); else state.TranslateSites.Remove(site);
            PushTabs();
            var script = on ? "window.__dragonTr&&__dragonTr.start()" : "window.__dragonTr&&__dragonTr.stop()";
            foreach (var t in tabs.Where(t => SiteKey(t.View.Source?.ToString() ?? "") == site).ToList())
                try { await t.View.CoreWebView2.ExecuteScriptAsync(script); } catch { }
        }

        /* the page sends batches of Cyrillic text; they come back in English */
        async void OnTabMessage(Tab tab, CoreWebView2WebMessageReceivedEventArgs e)
        {
            var m = Msg(e);
            if (Str(m, "type") != "tr" || !(m.TryGetValue("texts", out var raw) && raw is System.Collections.ArrayList list)) return;
            var texts = list.Cast<object>().Select(x => Convert.ToString(x)).Take(120).ToList();
            var output = await TranslateAsync(texts);
            Post(tab.View, new { type = "tr", id = m["id"], @out = output });
        }

        async Task<List<string>> TranslateAsync(List<string> texts)
        {
            var result = texts.Select(t => translations.TryGetValue(t, out var hit) ? hit : null).ToList();
            var todo = Enumerable.Range(0, texts.Count).Where(i => result[i] == null).ToList();
            if (todo.Count == 0) return result;
            try
            {
                var joined = string.Join("\n", todo.Select(i => texts[i].Replace("\n", " ")));
                var lines = await GoogleTranslate(joined);
                if (lines.Count != todo.Count) // line breaks got merged: translate one by one
                {
                    lines = new List<string>();
                    foreach (var i in todo) lines.Add((await GoogleTranslate(texts[i])).FirstOrDefault() ?? texts[i]);
                }
                for (int k = 0; k < todo.Count; k++) { result[todo[k]] = lines[k]; translations[texts[todo[k]]] = lines[k]; }
            }
            catch (Exception ex) { Log("Translation failed: " + ex.Message); }
            return result;
        }

        async Task<List<string>> GoogleTranslate(string text)
        {
            var body = new FormUrlEncodedContent(new[] { new KeyValuePair<string, string>("q", text) });
            var res = await http.PostAsync("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t", body);
            res.EnsureSuccessStatusCode();
            var root = json.DeserializeObject(await res.Content.ReadAsStringAsync()) as object[];
            var segs = root?[0] as object[] ?? new object[0];
            var joined = string.Concat(segs.Select(s => (s as object[])?[0] as string ?? ""));
            return joined.Split('\n').Select(l => l.Trim()).ToList();
        }

        /* runs in every page: finds Cyrillic text, asks the app for English, swaps it in, and keeps the originals for "off" */
        const string TranslatorScript = @"(()=>{if(window.__dragonTr||!window.chrome||!chrome.webview)return;
const CYR=/[А-Яа-яЁёІіЇїЄєҐґ]/,SKIP=/^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA|CODE|PRE|SVG)$/;let on=false,seq=0,timer=0,obs=null;const pending=new Map(),orig=new Map(),queue=[];
function collect(root){const out=[];if(!root)return out;const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(n){const p=n.parentElement;
if(!p||SKIP.test(p.tagName)||p.isContentEditable||orig.has(n))return 2;const t=n.nodeValue;return t&&t.trim().length>1&&CYR.test(t)?1:2;}});let n;while((n=w.nextNode()))out.push(n);return out;}
function schedule(nodes){queue.push(...nodes);clearTimeout(timer);timer=setTimeout(flush,120);}
function flush(){while(queue.length){const batch=[];let len=0;while(queue.length&&len<2500&&batch.length<60){const n=queue.shift();if(orig.has(n)||!n.isConnected)continue;
const t=n.nodeValue.replace(/\s+/g,' ').trim();if(!t)continue;batch.push([n,t]);len+=t.length;}if(!batch.length)break;const id=++seq;pending.set(id,batch);
batch.forEach(([n])=>orig.set(n,n.nodeValue));chrome.webview.postMessage({type:'tr',id,texts:batch.map(b=>b[1])});}}
chrome.webview.addEventListener('message',e=>{const d=e.data;if(!d||d.type!=='tr')return;const batch=pending.get(d.id);pending.delete(d.id);if(!batch||!on)return;
batch.forEach(([n],i)=>{const r=d.out&&d.out[i];if(r&&n.isConnected){const v=orig.get(n)||'';n.nodeValue=v.match(/^\s*/)[0]+r+v.match(/\s*$/)[0];}});});
window.__dragonTr={start(){if(on||!document.body)return;on=true;schedule(collect(document.body));
obs=new MutationObserver(ms=>{if(!on)return;const nodes=[];ms.forEach(m=>{m.addedNodes.forEach(a=>{if(a.nodeType===3){if(CYR.test(a.nodeValue)&&!orig.has(a))nodes.push(a);}else if(a.nodeType===1)nodes.push(...collect(a));});
if(m.type==='characterData'&&!orig.has(m.target)&&CYR.test(m.target.nodeValue||''))nodes.push(m.target);});if(nodes.length)schedule(nodes);});
obs.observe(document.body,{childList:true,subtree:true,characterData:true});},
stop(){on=false;if(obs)obs.disconnect();orig.forEach((v,n)=>{if(n.isConnected)n.nodeValue=v;});orig.clear();pending.clear();}};})();";

        /* ---------- price bar ---------- */
        /* reads name and asking price from a listing: schema.org data first, then OLX's or Prom's price block, then page meta */
        const string ListingScript = @"(()=>{const h=document.querySelector('h1');const name=h?h.innerText.trim():'';let price=0,cur='';
for(const s of document.querySelectorAll('script[type=""application/ld+json""]')){try{const d=JSON.parse(s.textContent);const arr=Array.isArray(d)?d:(d['@graph']||[d]);
for(const x of arr){let o=x&&x.offers;if(Array.isArray(o))o=o[0];if(o&&(o.price||o.lowPrice)){price=+String(o.price||o.lowPrice).replace(/[^\d.]/g,'');cur=o.priceCurrency||'';break;}}}catch(e){}if(price)break;}
if(!price){const el=document.querySelector('[data-testid=""ad-price-container""] h3,[data-testid=""ad-price-container""],[data-qaid=""product_price""],meta[property=""product:price:amount""]');
const t=el?(el.content||el.innerText||''):'';const m=t.match(/\d[\d\s  ]*/);if(m){price=+m[0].replace(/\D/g,'');cur=/\$/.test(t)?'USD':/€/.test(t)?'EUR':'UAH';}}
return JSON.stringify({name,price,cur});})()";

        /* collects prices from a search results page (OLX ad prices, shop price blocks) */
        const string ResultsScript = @"(()=>{const out=[];const re=/(\d[\d\s  ]{1,9})\s*(?:грн|₴|uah)/i;
document.querySelectorAll('[data-testid=""ad-price""],[class*=""price""]').forEach(el=>{if(el.querySelector('[data-testid=""ad-price""],[class*=""price""]'))return;
const m=(el.innerText||'').match(re);if(m){const v=+m[1].replace(/\D/g,'');if(v>=100&&v<10000000)out.push(v);}});return JSON.stringify(out.slice(0,60));})()";

        class Listing { public string name { get; set; } = ""; public decimal price { get; set; } public string cur { get; set; } = ""; }

        async void CheckListing(Tab tab)
        {
            var id = ++lookupId;
            await Task.Delay(1500);                                      // let the listing render
            if (id != lookupId || tab != active || tab.View.CoreWebView2 == null) return;
            Listing l;
            try { l = json.Deserialize<Listing>(json.Deserialize<string>(await tab.View.CoreWebView2.ExecuteScriptAsync(ListingScript))); }
            catch { l = null; }
            if (id != lookupId) return;
            if (l == null || l.price <= 0 || l.name.Length < 3) { SetPrice(null); return; }

            var q = SearchName(l.name);
            lastQuery = q;
            var asking = ToUah(l.price, l.cur);
            SetPrice(new { state = "checking", name = l.name, asking });
            List<decimal> used, fresh;
            if (priceCache.TryGetValue(q, out var hit)) { used = hit.used; fresh = hit.fresh; }
            else
            {
                used = await ScoutPrices(OlxUrl(q, true), id);
                if (id != lookupId) return;
                if (used.Count < 3) used = await ScoutPrices(OlxUrl(q, false), id);
                if (id != lookupId) return;
                fresh = await ScoutPrices("https://hotline.ua/ua/sr/?q=" + Uri.EscapeDataString(q), id);
                if (id != lookupId) return;
                priceCache[q] = (used, fresh);
            }
            object usedInfo = null;
            if (used.Count >= 3)
            {
                // good-condition used: drop the cheapest quarter (broken and parts-only ads), then the median and middle range
                var u = used.OrderBy(x => x).ToList(); u = u.Skip(u.Count / 4).ToList();
                usedInfo = new { mid = Quantile(u, 0.5), lo = Quantile(u, 0.25), hi = Quantile(u, 0.75), n = used.Count };
            }
            decimal newFrom = fresh.Count > 0 ? Quantile(fresh.Take(12).OrderBy(x => x).ToList(), 0.25) : 0;
            SetPrice(new { state = "done", name = l.name, asking, used = usedInfo, fresh = newFrom > 0 ? (object)newFrom : null });
        }

        void SetPrice(object p) { lastPrice = p; Post(bar, new { type = "price", price = p }); }

        static string OlxUrl(string q, bool usedOnly) =>
            "https://www.olx.ua/uk/list/q-" + string.Join("-", q.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries).Select(Uri.EscapeDataString)) + "/" +
            (usedOnly ? "?search%5Bfilter_enum_state%5D%5B0%5D=used" : "");

        void OpenPriceSearch(string which)
        {
            if (lastQuery.Length == 0) return;
            var e = Uri.EscapeDataString(lastQuery);
            var url = which == "new" ? "https://hotline.ua/ua/sr/?q=" + e
                    : which == "sold" ? "https://www.ebay.com/sch/i.html?_nkw=" + e + "&LH_Sold=1&LH_Complete=1"
                    : OlxUrl(lastQuery, true);
            _ = AddTab(url, true);
        }

        /* load a search page in the hidden browser and read its prices */
        async Task<List<decimal>> ScoutPrices(string url, int id)
        {
            var list = new List<decimal>();
            if (scout == null) return list;
            var done = new TaskCompletionSource<bool>();
            EventHandler<CoreWebView2NavigationCompletedEventArgs> h = (s, e) => done.TrySetResult(e.IsSuccess);
            scout.CoreWebView2.NavigationCompleted += h;
            try
            {
                scout.CoreWebView2.Navigate(url);
                await Task.WhenAny(done.Task, Task.Delay(15000));
                for (int tries = 0; tries < 3 && list.Count == 0 && id == lookupId; tries++)
                {
                    await Task.Delay(1800);                              // results are often drawn by script after load
                    var raw = json.Deserialize<string>(await scout.CoreWebView2.ExecuteScriptAsync(ResultsScript));
                    list = json.Deserialize<List<decimal>>(raw) ?? new List<decimal>();
                }
            }
            catch (Exception ex) { Log("Price lookup failed for " + url + ": " + ex.Message); }
            finally { scout.CoreWebView2.NavigationCompleted -= h; }
            return list;
        }

        static decimal Quantile(List<decimal> sorted, double q)
        {
            if (sorted.Count == 0) return 0;
            var pos = (sorted.Count - 1) * q; int lo = (int)Math.Floor(pos), hi = (int)Math.Ceiling(pos);
            return Math.Round(sorted[lo] + (sorted[hi] - sorted[lo]) * (decimal)(pos - lo));
        }

        static string CleanProduct(string t)
        {
            t = (t ?? "").Replace("\n", " ").Trim();
            foreach (var sep in new[] { " | ", " - OLX", " – OLX", ": купити", ": Купити", " - Prom", " — " }) { var i = t.IndexOf(sep, StringComparison.Ordinal); if (i > 3) t = t.Substring(0, i); }
            return t.Length > 80 ? t.Substring(0, 80) : t;
        }

        /* shorter search text: first words of the title without sale words */
        static string SearchName(string title)
        {
            var drop = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "продам", "продаю", "продається", "б/у", "бу", "б.у.", "на", "запчастини", "запчасти", "терміново", "срочно", "новий", "новый", "ідеал", "идеал", "стан", "состояние", "розбитий", "розбита", "разбитый", "разбит", "не", "працює", "работает", "робочий", "рабочий", "екран", "экран", "-", "|" };
            var words = CleanProduct(title).Split(new[] { ' ', ',', '(', ')', '/' }, StringSplitOptions.RemoveEmptyEntries).Where(w => !drop.Contains(w)).Take(5);
            return string.Join(" ", words);
        }

        decimal ToUah(decimal v, string cur) => cur == "USD" && usdRate > 0 ? v * usdRate : cur == "EUR" && eurRate > 0 ? v * eurRate : v;

        /* hryvnia rates from the National Bank of Ukraine, for euros next to prices */
        async void LoadRates()
        {
            try
            {
                ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
                var rows = json.Deserialize<List<Dictionary<string, object>>>(await http.GetStringAsync("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"));
                foreach (var r in rows)
                {
                    var code = r["cc"] as string; var rate = Convert.ToDecimal(r["rate"], CultureInfo.InvariantCulture);
                    if (code == "EUR") eurRate = rate; else if (code == "USD") usdRate = rate;
                }
                Post(bar, new { type = "rates", eur = eurRate });
            }
            catch (Exception ex) { Log("Exchange rates not loaded: " + ex.Message); }
        }

        /* ---------- helpers ---------- */
        static bool IsWeb(string url) =>
            !string.IsNullOrEmpty(url) && (url.StartsWith("https://", StringComparison.OrdinalIgnoreCase) || url.StartsWith("http://", StringComparison.OrdinalIgnoreCase)) && !IsNewTab(url);

        static void OpenExternal(string url)
        {
            try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); } catch { }
        }

        /* every failure is written to %LOCALAPPDATA%\Dragon\dragon.log and shown once */
        public static void Log(string text)
        {
            try { Directory.CreateDirectory(DataDir); File.AppendAllText(Path.Combine(DataDir, "dragon.log"), DateTime.Now.ToString("s") + "  " + text + Environment.NewLine); } catch { }
        }

        public static void Fail(string what, Exception ex)
        {
            Log(what + ": " + ex);
            MessageBox.Show(what + ".\n\n" + (ex?.Message ?? "Unknown error") + "\n\nDetails were saved to " + Path.Combine(DataDir, "dragon.log"),
                "Dragon", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }

        void LoadState()
        {
            try { if (File.Exists(stateFile)) state = json.Deserialize<WindowState>(File.ReadAllText(stateFile)) ?? new WindowState(); }
            catch { state = new WindowState(); }
            if (state.Tabs == null) state.Tabs = new List<string>();
            if (state.TranslateSites == null) state.TranslateSites = new List<string>();
        }

        void SaveState()
        {
            try
            {
                if (fullScreen) ToggleFullScreen();
                state.Maximized = WindowState == FormWindowState.Maximized;
                var b = WindowState == FormWindowState.Normal ? Bounds : RestoreBounds;
                state.X = b.X; state.Y = b.Y; state.W = b.Width; state.H = b.Height;
                if (!split.Panel2Collapsed) state.Split = split.SplitterDistance;
                if (browserStarted)
                {
                    state.Tabs = tabs.Select(t => { var u = t.View.Source?.ToString(); return IsWeb(u) ? u : ""; }).ToList();
                    state.ActiveTab = Math.Max(0, tabs.IndexOf(active));
                    state.TrainingUrl = "";
                }
                Directory.CreateDirectory(DataDir);
                File.WriteAllText(stateFile, json.Serialize(state));
            }
            catch { }
        }
    }
}
