using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Diagnostics;
using System.Drawing;
using System.IO;
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

    /* Window layout and the training page, remembered between runs in %LOCALAPPDATA%\Dragon\window.json */
    class WindowState
    {
        public int X = -1, Y = -1, W = 1400, H = 900, Split = 520;
        public bool Maximized = true, TrainingHidden = false;
        public string TrainingUrl = "";
        public List<string> TranslateSites = new List<string>();  // sites always shown in English
        public bool PriceOpen = false;
    }

    /* Dragon workplace: the Dragon app on the left, a training browser on the right.
       Links from Dragon open in the training pane; it keeps you signed in and reopens the last page. */
    class MainForm : Form
    {
        const string Host = "dragon.example";
        static readonly Color Bg = Color.FromArgb(7, 5, 5), Bar = Color.FromArgb(18, 9, 9), Ink = Color.FromArgb(240, 234, 234);

        readonly string dataDir = DataDir;
        readonly string stateFile;
        readonly JavaScriptSerializer json = new JavaScriptSerializer();
        WindowState state = new WindowState();

        static readonly string DataDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Dragon");
        static readonly string SafeGraphicsFlag = Path.Combine(DataDir, "safe-graphics");
        bool pageLoaded;
        readonly SplitContainer split = new SplitContainer();
        readonly WebView2 dragon = new WebView2();
        readonly WebView2 training = new WebView2();
        readonly Label title = new Label();
        readonly Button showTraining = new Button();
        Button translateBtn;
        readonly WebView2 prices = new WebView2();
        readonly Panel pricePanel = new Panel();
        readonly TextBox query = new TextBox(), resale = new TextBox(), parts = new TextBox();
        readonly Label maxBuy = new Label();
        static readonly Color On = Color.FromArgb(212, 42, 42);

        public MainForm()
        {
            stateFile = Path.Combine(dataDir, "window.json");
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
            KeyPreview = true;

            split.Dock = DockStyle.Fill;
            split.BackColor = Color.FromArgb(40, 20, 20);
            split.Panel1.BackColor = Bg;
            split.Panel2.BackColor = Bg;
            split.SplitterWidth = 5;
            split.Panel1MinSize = 380;
            dragon.Dock = DockStyle.Fill;
            dragon.DefaultBackgroundColor = Bg;
            split.Panel1.Controls.Add(dragon);

            training.Dock = DockStyle.Fill;
            training.DefaultBackgroundColor = Color.White;
            split.Panel2.Controls.Add(training);
            split.Panel2.Controls.Add(BuildPricePanel());
            split.Panel2.Controls.Add(BuildToolbar());
            Controls.Add(split);

            showTraining.Text = "Training ◂";
            StyleButton(showTraining);
            showTraining.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            showTraining.Visible = false;
            showTraining.Click += (s, e) => SetTrainingHidden(false);
            Controls.Add(showTraining);
            showTraining.BringToFront();

            Load += async (s, e) => await StartAsync();
            Shown += (s, e) => { try { split.SplitterDistance = Math.Max(split.Panel1MinSize, Math.Min(state.Split, split.Width - 300)); } catch { } SetTrainingHidden(state.TrainingHidden); };
            Resize += (s, e) => PlaceShowButton();
            FormClosing += (s, e) => SaveState();
            KeyDown += OnKeys;
        }

        Control BuildToolbar()
        {
            var bar = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 40, BackColor = Bar, Padding = new Padding(6, 5, 6, 0), WrapContents = false };
            Button btn(string text, string tip, Action act)
            {
                var b = new Button { Text = text };
                StyleButton(b);
                new ToolTip().SetToolTip(b, tip);
                b.Click += (s, e) => act();
                bar.Controls.Add(b);
                return b;
            }
            btn("◀", "Back (Alt+Left)", () => { if (training.CoreWebView2?.CanGoBack == true) training.CoreWebView2.GoBack(); });
            btn("▶", "Forward (Alt+Right)", () => { if (training.CoreWebView2?.CanGoForward == true) training.CoreWebView2.GoForward(); });
            btn("⟳", "Reload (F5)", () => training.CoreWebView2?.Reload());
            btn("Browser ↗", "Open this page in your normal browser", () => { var u = training.Source?.ToString(); if (IsWeb(u)) OpenExternal(u); });
            translateBtn = btn("EN", "Show this site in English (Google Translate). Click again for the original.", ToggleTranslate);
            btn("Price ₴", "Price check: new and used prices for what you are looking at", () => SetPriceOpen(!pricePanel.Visible));
            btn("Hide ▸", "Hide the training pane (Ctrl+T)", () => SetTrainingHidden(true));
            title.AutoSize = false;
            title.Width = 600;
            title.Height = 28;
            title.ForeColor = Color.FromArgb(166, 149, 149);
            title.TextAlign = ContentAlignment.MiddleLeft;
            title.Font = new Font("Segoe UI", 9.5f);
            bar.Controls.Add(title);
            return bar;
        }

        /* price check panel: product name, new and used price searches, and the 60% rule */
        Control BuildPricePanel()
        {
            pricePanel.Dock = DockStyle.Right;
            pricePanel.Width = 420;
            pricePanel.BackColor = Bar;
            pricePanel.Visible = false;
            pricePanel.Padding = new Padding(1, 0, 0, 0);
            prices.Dock = DockStyle.Fill;
            prices.DefaultBackgroundColor = Color.White;

            var top = new TableLayoutPanel { Dock = DockStyle.Top, Height = 190, BackColor = Bar, Padding = new Padding(10, 8, 10, 6), ColumnCount = 4, RowCount = 5 };
            for (int i = 0; i < 4; i++) top.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25));
            Label lbl(string t) => new Label { Text = t, ForeColor = Color.FromArgb(166, 149, 149), Font = new Font("Segoe UI", 8.5f, FontStyle.Bold), AutoSize = true, Margin = new Padding(0, 4, 0, 2) };
            void box(TextBox b, string cue) { b.BackColor = Color.FromArgb(30, 14, 14); b.ForeColor = Ink; b.BorderStyle = BorderStyle.FixedSingle; b.Font = new Font("Segoe UI", 10f); b.Dock = DockStyle.Fill; b.Margin = new Padding(0, 0, 6, 4); }
            var head = lbl("PRICE CHECK · product");
            top.Controls.Add(head, 0, 0); top.SetColumnSpan(head, 3);
            var close = new Button { Text = "✕" }; StyleButton(close); close.Anchor = AnchorStyles.Right; close.Click += (s, e) => SetPriceOpen(false);
            top.Controls.Add(close, 3, 0);
            box(query, "product");
            query.KeyDown += (s, e) => { if (e.KeyCode == Keys.Enter) { Search("hotline"); e.SuppressKeyPress = true; } };
            top.Controls.Add(query, 0, 1); top.SetColumnSpan(query, 4);
            var sites = new[] { ("New · Hotline", "hotline"), ("New · Rozetka", "rozetka"), ("Used · OLX", "olx"), ("Sold · eBay", "ebay") };
            for (int i = 0; i < sites.Length; i++)
            {
                var (text, key) = sites[i];
                var b = new Button { Text = text }; StyleButton(b); b.AutoSize = false; b.Dock = DockStyle.Fill; b.Font = new Font("Segoe UI", 8.5f, FontStyle.Bold);
                b.Click += (s, e) => Search(key);
                top.Controls.Add(b, i, 2);
            }
            top.Controls.Add(lbl("RESALE PRICE"), 0, 3); top.Controls.Add(lbl("PARTS"), 1, 3);
            var ml = lbl("MAX BUY (60% RULE)"); top.Controls.Add(ml, 2, 3); top.SetColumnSpan(ml, 2);
            box(resale, "used price"); box(parts, "parts");
            top.Controls.Add(resale, 0, 4); top.Controls.Add(parts, 1, 4);
            maxBuy.ForeColor = Color.FromArgb(214, 165, 72); maxBuy.Font = new Font("Segoe UI", 12f, FontStyle.Bold); maxBuy.AutoSize = true; maxBuy.Text = "—";
            top.Controls.Add(maxBuy, 2, 4); top.SetColumnSpan(maxBuy, 2);
            resale.TextChanged += (s, e) => UpdateMaxBuy(); parts.TextChanged += (s, e) => UpdateMaxBuy();

            pricePanel.Controls.Add(prices);
            pricePanel.Controls.Add(top);
            return pricePanel;
        }

        static decimal Num(string t) => decimal.TryParse((t ?? "").Replace(" ", "").Replace(",", "."), NumberStyles.Number, CultureInfo.InvariantCulture, out var v) ? v : 0;

        /* buy + parts must stay under ~60% of what it sells for used */
        void UpdateMaxBuy()
        {
            var r = Num(resale.Text);
            if (r <= 0) { maxBuy.Text = "—"; return; }
            var m = r * 0.6m - Num(parts.Text);
            maxBuy.Text = m > 0 ? m.ToString("#,0", CultureInfo.InvariantCulture).Replace(",", " ") : "don't buy";
        }

        async void SetPriceOpen(bool open)
        {
            state.PriceOpen = open;
            pricePanel.Visible = open;
            if (!open || training.CoreWebView2 == null) return;
            // read the product name from the page you are looking at
            try
            {
                var raw = await training.CoreWebView2.ExecuteScriptAsync("(document.querySelector('h1')&&document.querySelector('h1').innerText)||document.title||''");
                var name = CleanProduct(json.Deserialize<string>(raw));
                if (name.Length > 0) query.Text = name;
            }
            catch { }
            if (query.Text.Trim().Length > 0) Search("hotline");
        }

        static string CleanProduct(string t)
        {
            t = (t ?? "").Replace("\n", " ").Trim();
            foreach (var sep in new[] { " | ", " - OLX", " – OLX", ": купити", ": Купити", " - Prom", " — " }) { var i = t.IndexOf(sep, StringComparison.Ordinal); if (i > 3) t = t.Substring(0, i); }
            return t.Length > 80 ? t.Substring(0, 80) : t;
        }

        void Search(string site)
        {
            var q = query.Text.Trim();
            if (q.Length == 0 || prices.CoreWebView2 == null) return;
            var e = Uri.EscapeDataString(q);
            string url;
            switch (site)
            {
                case "rozetka": url = "https://rozetka.com.ua/ua/search/?text=" + e; break;
                case "olx": url = "https://www.olx.ua/uk/list/q-" + string.Join("-", q.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries).Select(Uri.EscapeDataString)) + "/"; break;
                case "ebay": url = "https://www.ebay.com/sch/i.html?_nkw=" + e + "&LH_Sold=1&LH_Complete=1"; break;
                default: url = "https://hotline.ua/ua/sr/?q=" + e; break;
            }
            prices.CoreWebView2.Navigate(url);
        }

        /* ---------- English: pages of a chosen site are shown through Google Translate ---------- */
        static string HostOf(string url) { try { return new Uri(url).Host.ToLowerInvariant(); } catch { return ""; } }
        static string SiteKey(string host) => host.StartsWith("www.") ? host.Substring(4) : host;
        static bool IsTranslated(string url) => HostOf(url).EndsWith(".translate.goog");

        static string Translated(string url) =>
            "https://translate.google.com/translate?sl=auto&tl=en&hl=en&u=" + Uri.EscapeDataString(url);

        /* www-olx-ua.translate.goog/path?x=1&_x_tr_sl=auto... → https://www.olx.ua/path?x=1 */
        static string Original(string url)
        {
            try
            {
                var u = new Uri(url);
                var label = u.Host.Substring(0, u.Host.Length - ".translate.goog".Length);
                var host = label.Replace("--", "\u0001").Replace("-", ".").Replace("\u0001", "-");
                var query = string.Join("&", u.Query.TrimStart('?').Split('&').Where(p => p.Length > 0 && !p.StartsWith("_x_tr_")));
                return "https://" + host + u.AbsolutePath + (query.Length > 0 ? "?" + query : "") + u.Fragment;
            }
            catch { return url; }
        }

        bool WantsEnglish(string url) => state.TranslateSites.Contains(SiteKey(HostOf(IsTranslated(url) ? Original(url) : url)));

        void ToggleTranslate()
        {
            var cur = training.Source?.ToString();
            if (!IsWeb(cur)) return;
            var original = IsTranslated(cur) ? Original(cur) : cur;
            var site = SiteKey(HostOf(original));
            if (state.TranslateSites.Contains(site)) { state.TranslateSites.Remove(site); training.CoreWebView2.Navigate(original); }
            else { state.TranslateSites.Add(site); training.CoreWebView2.Navigate(Translated(original)); }
            UpdateTranslateButton();
        }

        void UpdateTranslateButton()
        {
            var on = WantsEnglish(training.Source?.ToString() ?? "");
            translateBtn.BackColor = on ? On : Color.FromArgb(30, 14, 14);
            translateBtn.Text = on ? "EN ✓" : "EN";
        }

        /* send pages of English-wanted sites through the translator (both the training pane and price results) */
        void RouteEnglish(CoreWebView2 view, CoreWebView2NavigationStartingEventArgs e)
        {
            var u = e.Uri;
            if (!IsWeb(u) || IsTranslated(u) || HostOf(u).EndsWith("google.com") || HostOf(u).EndsWith("translate.goog")) return;
            if (!state.TranslateSites.Contains(SiteKey(HostOf(u)))) return;
            e.Cancel = true;
            view.Navigate(Translated(u));
        }

        static void StyleButton(Button b)
        {
            b.FlatStyle = FlatStyle.Flat;
            b.FlatAppearance.BorderColor = Color.FromArgb(59, 29, 29);
            b.BackColor = Color.FromArgb(30, 14, 14);
            b.ForeColor = Ink;
            b.Font = new Font("Segoe UI", 9.5f, FontStyle.Bold);
            b.AutoSize = true;
            b.Height = 30;
            b.Margin = new Padding(0, 0, 6, 0);
            b.Cursor = Cursors.Hand;
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
                // point WebView2 at its loader explicitly: next to the exe, or in runtimes\<arch>\native
                var arch = Environment.Is64BitProcess ? "win-x64" : "win-x86";
                foreach (var dir in new[] { baseDir, Path.Combine(baseDir, "runtimes", arch, "native") })
                    if (File.Exists(Path.Combine(dir, "WebView2Loader.dll"))) { CoreWebView2Environment.SetLoaderDllFolderPath(dir); break; }
                // safe graphics turns GPU drawing off, for laptops whose driver shows WebView2 as a black area
                var options = new CoreWebView2EnvironmentOptions(safe ? "--disable-gpu --disable-gpu-compositing" : null);
                var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(DataDir, "WebView2"), options);
                await dragon.EnsureCoreWebView2Async(env);
                await training.EnsureCoreWebView2Async(env);
                await prices.EnsureCoreWebView2Async(env);
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

            // the Dragon app: served from the app folder next to the exe, as a secure https origin so storage persists
            var core = dragon.CoreWebView2;
            core.SetVirtualHostNameToFolderMapping(Host, appDir, CoreWebView2HostResourceAccessKind.Allow);
            core.Settings.IsStatusBarEnabled = false;
            core.NewWindowRequested += (s, e) => { e.Handled = true; OpenTraining(e.Uri); };
            core.NavigationStarting += (s, e) =>
            {
                if (e.Uri.StartsWith("https://" + Host + "/", StringComparison.OrdinalIgnoreCase)) return;
                e.Cancel = true;
                OpenTraining(e.Uri);
            };
            core.NavigationCompleted += (s, e) =>
            {
                if (e.IsSuccess) { pageLoaded = true; return; }
                Log("Dragon page failed to load: " + e.WebErrorStatus);
            };
            core.ProcessFailed += (s, e) => { Log("Browser process failed: " + e.ProcessFailedKind); try { core.Reload(); } catch { } };
            core.Navigate("https://" + Host + "/index.html");

            // the training pane: new windows stay in the pane, and the page you are on is remembered
            var tc = training.CoreWebView2;
            tc.NewWindowRequested += (s, e) => { e.Handled = true; if (IsWeb(e.Uri)) tc.Navigate(e.Uri); };
            tc.NavigationStarting += (s, e) => RouteEnglish(tc, e);
            tc.NavigationCompleted += (s, e) => UpdateTranslateButton();
            var pc = prices.CoreWebView2;
            pc.NewWindowRequested += (s, e) => { e.Handled = true; if (IsWeb(e.Uri)) pc.Navigate(e.Uri); };
            pc.NavigationStarting += (s, e) => RouteEnglish(pc, e);
            pc.NavigateToString(PriceWelcome);
            if (state.PriceOpen) pricePanel.Visible = true;
            tc.SourceChanged += (s, e) => { var u = training.Source?.ToString(); if (IsWeb(u)) state.TrainingUrl = u; };
            tc.DocumentTitleChanged += (s, e) => title.Text = tc.DocumentTitle;
            if (IsWeb(state.TrainingUrl)) tc.Navigate(state.TrainingUrl);
            else tc.NavigateToString(WelcomePage);

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

        void OpenTraining(string url)
        {
            if (!IsWeb(url)) { if (!string.IsNullOrEmpty(url) && !url.StartsWith("about:")) OpenExternal(url); return; }
            SetTrainingHidden(false);
            training.CoreWebView2?.Navigate(url);
        }

        void SetTrainingHidden(bool hidden)
        {
            state.TrainingHidden = hidden;
            split.Panel2Collapsed = hidden;
            showTraining.Visible = hidden;
            PlaceShowButton();
        }

        void PlaceShowButton()
        {
            showTraining.Location = new Point(ClientSize.Width - showTraining.Width - 70, 8);
        }

        void OnKeys(object sender, KeyEventArgs e)
        {
            if (e.Control && e.KeyCode == Keys.T) { SetTrainingHidden(!state.TrainingHidden); e.Handled = true; }
            else if (e.Alt && e.KeyCode == Keys.Left && training.CoreWebView2?.CanGoBack == true) { training.CoreWebView2.GoBack(); e.Handled = true; }
            else if (e.Alt && e.KeyCode == Keys.Right && training.CoreWebView2?.CanGoForward == true) { training.CoreWebView2.GoForward(); e.Handled = true; }
        }

        static bool IsWeb(string url) =>
            !string.IsNullOrEmpty(url) && (url.StartsWith("https://", StringComparison.OrdinalIgnoreCase) || url.StartsWith("http://", StringComparison.OrdinalIgnoreCase));

        static void OpenExternal(string url)
        {
            try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); } catch { }
        }

        void LoadState()
        {
            try { if (File.Exists(stateFile)) state = json.Deserialize<WindowState>(File.ReadAllText(stateFile)) ?? new WindowState(); }
            catch { state = new WindowState(); }
        }

        void SaveState()
        {
            try
            {
                state.Maximized = WindowState == FormWindowState.Maximized;
                var b = WindowState == FormWindowState.Normal ? Bounds : RestoreBounds;
                state.X = b.X; state.Y = b.Y; state.W = b.Width; state.H = b.Height;
                if (!split.Panel2Collapsed) state.Split = split.SplitterDistance;
                Directory.CreateDirectory(dataDir);
                File.WriteAllText(stateFile, json.Serialize(state));
            }
            catch { }
        }

        const string PriceWelcome = @"<!doctype html><html><body style=""margin:0;padding:24px;background:#120909;color:#a69595;font:14px 'Segoe UI',sans-serif"">
<p style=""color:#f0eaea;font-size:16px;margin:0 0 8px"">Price check</p><p>Open a listing on the left, then press <b>Price ₴</b>. The product name is read from the page; edit it if needed.</p>
<p><b>New</b>: Hotline.ua compares Ukrainian shops, Rozetka is the biggest one. <b>Used</b>: OLX listings, and eBay sold items show what used ones really sold for.</p>
<p>Enter the used resale price and the parts cost to see the most you should pay (60% rule).</p></body></html>";

        const string WelcomePage = @"<!doctype html><html><body style=""margin:0;height:100vh;display:grid;place-items:center;background:#070505;color:#a69595;font:16px 'Segoe UI',sans-serif;text-align:center"">
<div><div style=""font-size:44px"">🐉</div><p style=""color:#f0eaea;font-size:20px;margin:10px 0 6px"">Training pane</p>
<p>Open a lesson link on the left. It opens here, keeps you signed in,<br>and Dragon reopens the page you were on next time.</p></div></body></html>";
    }
}
