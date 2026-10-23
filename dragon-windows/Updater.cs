using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace Dragon
{
    /* Over-the-air updates for Dragon's pages.
       The update channel is the dragon-update folder on the main branch of the Dragon repository. A newer version is
       downloaded in the background into %LOCALAPPDATA%\Dragon\app-update.new, checked against the SHA-256 sums in
       version.json, and switched in at the next start. The pages are always served from https://dragon.example,
       whichever folder they come from, so the app's saved data stays where it is. */
    static class Updater
    {
        public const string Channel = "https://raw.githubusercontent.com/valdekluik5-ui/Valdek/main/dragon-update/";
        static readonly string Live = Path.Combine(MainForm.DataDir, "app-update");
        static readonly string Staged = Path.Combine(MainForm.DataDir, "app-update.new");
        static readonly HttpClient http = new HttpClient { Timeout = TimeSpan.FromSeconds(60) };
        static readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 32 * 1024 * 1024 };

        public static Version Native => Assembly.GetExecutingAssembly().GetName().Version;

        class Manifest { public string version { get; set; } public string minNative { get; set; } public Dictionary<string, string> files { get; set; } }

        /* the folder to serve the pages from: a downloaded update when it is newer than the installed app */
        public static string PickAppDir(string builtIn, out string applied)
        {
            applied = null;
            try
            {
                if (File.Exists(Path.Combine(Staged, "version.txt")))
                {
                    if (Directory.Exists(Live)) Directory.Delete(Live, true);
                    Directory.Move(Staged, Live);
                    applied = File.ReadAllText(Path.Combine(Live, "version.txt")).Trim();
                }
                var v = ReadVersion(Live);
                if (v != null && v > Native && File.Exists(Path.Combine(Live, "index.html"))) return Live;
                applied = null;
            }
            catch (Exception ex) { MainForm.Log("Update could not be switched in: " + ex.Message); applied = null; }
            return builtIn;
        }

        static Version ReadVersion(string dir)
        {
            try { return Parse(File.ReadAllText(Path.Combine(dir, "version.txt")).Trim()); } catch { return null; }
        }

        static Version Parse(string s)
        {
            var parts = (s ?? "").Split('.').Select(p => int.TryParse(p, out var n) ? n : 0).ToList();
            while (parts.Count < 3) parts.Add(0);
            return new Version(parts[0], parts[1], parts[2], 0);
        }

        /* checks the channel; returns the version that is ready for the next start, or null */
        public static async Task<string> CheckAsync(string builtIn, string current)
        {
            try
            {
                var m = json.Deserialize<Manifest>(await http.GetStringAsync(Channel + "version.json?t=" + DateTime.UtcNow.Ticks));
                if (m?.files == null || m.files.Count == 0) return null;
                var now = Parse(current);
                if (Parse(m.version) <= now) return null;
                if (Parse(m.minNative) > Native) { MainForm.Log("Update " + m.version + " needs a new Dragon-Setup.exe (" + m.minNative + ")."); return null; }
                if (ReadVersion(Staged) == Parse(m.version)) return m.version;

                // start from a full copy of the installed pages, then lay the new files on top
                var tmp = Staged + ".part";
                if (Directory.Exists(tmp)) Directory.Delete(tmp, true);
                Directory.CreateDirectory(tmp);
                foreach (var f in Directory.GetFiles(builtIn)) File.Copy(f, Path.Combine(tmp, Path.GetFileName(f)));
                foreach (var kv in m.files)
                {
                    var name = Path.GetFileName(kv.Key);
                    if (name != kv.Key || name.Length == 0) throw new Exception("bad file name in version.json: " + kv.Key);
                    var bytes = await http.GetByteArrayAsync(Channel + Uri.EscapeDataString(name) + "?v=" + Uri.EscapeDataString(m.version));
                    string sum;
                    using (var sha = SHA256.Create()) sum = string.Concat(sha.ComputeHash(bytes).Select(b => b.ToString("x2")));
                    if (!string.Equals(sum, kv.Value, StringComparison.OrdinalIgnoreCase)) throw new Exception(name + " did not match its checksum");
                    File.WriteAllBytes(Path.Combine(tmp, name), bytes);
                }
                File.WriteAllText(Path.Combine(tmp, "version.txt"), m.version);
                if (Directory.Exists(Staged)) Directory.Delete(Staged, true);
                Directory.Move(tmp, Staged);
                MainForm.Log("Update " + m.version + " downloaded; it starts next time.");
                return m.version;
            }
            catch (Exception ex) { MainForm.Log("Update check failed: " + ex.Message); return null; }
        }

        public static string CurrentVersion(string appDir) =>
            appDir == Live ? File.ReadAllText(Path.Combine(Live, "version.txt")).Trim() : Native.ToString(3);
    }
}
