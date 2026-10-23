using System;
using System.Collections.Generic;
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

        const string WelcomePage = @"<!doctype html><html><body style=""margin:0;height:100vh;display:grid;place-items:center;background:#070505;color:#a69595;font:16px 'Segoe UI',sans-serif;text-align:center"">
<div><div style=""font-size:44px"">🐉</div><p style=""color:#f0eaea;font-size:20px;margin:10px 0 6px"">Training pane</p>
<p>Open a lesson link on the left. It opens here, keeps you signed in,<br>and Dragon reopens the page you were on next time.</p></div></body></html>";
    }
}
