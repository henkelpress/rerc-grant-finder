using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace RERCieDesktop
{
    internal static class Config
    {
        public const string Version = "0.3.2";
        public const string AppUrl = "http://127.0.0.1:8789";
        public const string AppHealthUrl = AppUrl + "/health";
        public const string ModelHealthUrl = "http://127.0.0.1:8788/health";
        public const string ModelListUrl = "http://127.0.0.1:8788/v1/models";
        public const string ModelName = "gemma-3-1b-it-Q4_K_M.gguf";
        public const string ModelUrl = "https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf?download=true";
        public const long ModelBytes = 806058240L;
        public const string ModelSha256 = "8ccc5cd1f1b3602548715ae25a66ed73fd5dc68a210412eea643eb20eb75a135";
        public const string VcRuntimeUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe";
        public const string ModelPageUrl = "https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF";
        public const string ModelLicenseUrl = "https://ai.google.dev/gemma/terms";
    }

    internal sealed class IntegrityEntry
    {
        public string path { get; set; }
        public long bytes { get; set; }
        public string sha256 { get; set; }
    }

    internal sealed class IntegrityManifest
    {
        public List<IntegrityEntry> files { get; set; }
    }

    internal sealed class ProcessRecord
    {
        public int pid { get; set; }
        public string executable_path { get; set; }
        public string start_time_utc { get; set; }
        public string session_token { get; set; }
    }

    internal static class Runtime
    {
        public static readonly string Root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
        public static readonly string ModelsDir = Path.Combine(Root, "models");
        public static readonly string ModelPath = Path.Combine(ModelsDir, Config.ModelName);
        public static readonly string RuntimeDir = Path.Combine(Root, "runtime");
        public static readonly string LlamaDir = Path.Combine(RuntimeDir, "llama");
        public static readonly string LlamaExe = Path.Combine(LlamaDir, "llama-server.exe");
        public static readonly string ServiceDir = Path.Combine(Root, "service");
        public static readonly string ServiceExe = Path.Combine(ServiceDir, "RERCieService.exe");
        public static readonly string PidDir = Path.Combine(RuntimeDir, "pids");
        public static readonly string IntegrityPath = Path.Combine(Root, "file_integrity.json");
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

        public static string Sha256(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 hash = SHA256.Create())
            {
                byte[] bytes = hash.ComputeHash(stream);
                StringBuilder output = new StringBuilder(bytes.Length * 2);
                foreach (byte value in bytes) output.Append(value.ToString("x2"));
                return output.ToString();
            }
        }

        public static void VerifyPackage()
        {
            if (!File.Exists(IntegrityPath)) throw new InvalidOperationException("RERCie is missing its safety file. Run the installer again.");
            IntegrityManifest manifest = Json.Deserialize<IntegrityManifest>(File.ReadAllText(IntegrityPath));
            if (manifest == null || manifest.files == null || manifest.files.Count == 0) throw new InvalidOperationException("RERCie's safety file is not valid. Run the installer again.");
            foreach (IntegrityEntry entry in manifest.files)
            {
                string relative = (entry.path ?? "").Replace('/', Path.DirectorySeparatorChar);
                string fullPath = Path.GetFullPath(Path.Combine(Root, relative));
                if (!fullPath.StartsWith(Root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("RERCie's safety file has an invalid path.");
                FileInfo file = new FileInfo(fullPath);
                if (!file.Exists || file.Length != entry.bytes || !string.Equals(Sha256(fullPath), entry.sha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("A RERCie file did not pass its safety check: " + relative + ". Run the installer again.");
            }
        }

        public static bool ModelReady()
        {
            FileInfo file = new FileInfo(ModelPath);
            return file.Exists && file.Length == Config.ModelBytes && string.Equals(Sha256(ModelPath), Config.ModelSha256, StringComparison.OrdinalIgnoreCase);
        }

        public static bool VcRuntimeReady()
        {
            string system = Environment.GetFolderPath(Environment.SpecialFolder.System);
            string[] names = { "MSVCP140.dll", "VCRUNTIME140.dll", "VCRUNTIME140_1.dll" };
            foreach (string name in names) if (!File.Exists(Path.Combine(system, name))) return false;
            return true;
        }

        public static bool PortInUse(int port)
        {
            using (TcpClient client = new TcpClient())
            {
                try
                {
                    IAsyncResult attempt = client.BeginConnect("127.0.0.1", port, null, null);
                    if (!attempt.AsyncWaitHandle.WaitOne(600)) return false;
                    client.EndConnect(attempt);
                    return true;
                }
                catch { return false; }
            }
        }

        private static bool TryGetOwnedProcess(string name, string expectedExecutable, out ProcessRecord record, out Process process)
        {
            record = null;
            process = null;
            string recordPath = Path.Combine(PidDir, name + ".json");
            if (!File.Exists(recordPath)) return false;
            try
            {
                record = Json.Deserialize<ProcessRecord>(File.ReadAllText(recordPath));
                if (record == null || record.pid <= 0 || string.IsNullOrWhiteSpace(record.executable_path) || string.IsNullOrWhiteSpace(record.start_time_utc)) return false;
                process = Process.GetProcessById(record.pid);
                if (process.HasExited) return false;
                string actualPath = process.MainModule.FileName;
                DateTime actualStart = process.StartTime.ToUniversalTime();
                DateTime recordedStart = DateTime.Parse(record.start_time_utc).ToUniversalTime();
                return string.Equals(Path.GetFullPath(actualPath), Path.GetFullPath(expectedExecutable), StringComparison.OrdinalIgnoreCase)
                    && string.Equals(Path.GetFullPath(record.executable_path), Path.GetFullPath(expectedExecutable), StringComparison.OrdinalIgnoreCase)
                    && Math.Abs((actualStart - recordedStart).TotalSeconds) < 3;
            }
            catch { return false; }
        }

        public static bool AppReady()
        {
            ProcessRecord record;
            Process process;
            return TryGetOwnedProcess("app", ServiceExe, out record, out process)
                && !string.IsNullOrWhiteSpace(record.session_token)
                && EndpointContains(Config.AppHealthUrl, "\"app\": \"RERCie\"", record.session_token);
        }

        public static bool ModelServerReady()
        {
            ProcessRecord record;
            Process process;
            return TryGetOwnedProcess("llama", LlamaExe, out record, out process)
                && EndpointContains(Config.ModelHealthUrl, "ok", null)
                && EndpointContains(Config.ModelListUrl, Config.ModelName, null);
        }

        public static string AppBrowserUrl()
        {
            ProcessRecord record;
            Process process;
            if (!TryGetOwnedProcess("app", ServiceExe, out record, out process) || string.IsNullOrWhiteSpace(record.session_token))
                throw new InvalidOperationException("RERCie's local session is not ready. Start RERCie again.");
            return Config.AppUrl + "/#token=" + Uri.EscapeDataString(record.session_token);
        }

        public static string CreateSessionToken()
        {
            byte[] bytes = new byte[32];
            using (RandomNumberGenerator generator = RandomNumberGenerator.Create()) generator.GetBytes(bytes);
            StringBuilder token = new StringBuilder(64);
            foreach (byte value in bytes) token.Append(value.ToString("x2"));
            return token.ToString();
        }

        private static bool EndpointContains(string url, string expected, string sessionToken)
        {
            try
            {
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
                request.Timeout = 1800;
                request.ReadWriteTimeout = 1800;
                request.Proxy = null;
                if (!string.IsNullOrWhiteSpace(sessionToken)) request.Headers["X-RERCie-Token"] = sessionToken;
                using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
                using (StreamReader reader = new StreamReader(response.GetResponseStream()))
                    return reader.ReadToEnd().IndexOf(expected, StringComparison.OrdinalIgnoreCase) >= 0;
            }
            catch { return false; }
        }
        public static async Task WaitForAsync(Func<bool> check, int seconds, string message)
        {
            for (int i = 0; i < seconds * 2; i++)
            {
                if (check()) return;
                await Task.Delay(500);
            }
            throw new InvalidOperationException(message);
        }

        public static Process StartHidden(string name, string executable, string arguments, string workingDirectory, IDictionary<string, string> environment, string sessionToken)
        {
            ProcessStartInfo info = new ProcessStartInfo(executable, arguments);
            info.WorkingDirectory = workingDirectory;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.WindowStyle = ProcessWindowStyle.Hidden;
            if (environment != null)
                foreach (KeyValuePair<string, string> item in environment) info.EnvironmentVariables[item.Key] = item.Value;
            Process process = Process.Start(info);
            if (process == null) throw new InvalidOperationException("A part of RERCie could not start. Restart RERCie and try again.");
            WriteProcessRecord(name, process, executable, sessionToken);
            return process;
        }

        private static void WriteProcessRecord(string name, Process process, string executable, string sessionToken)
        {
            Directory.CreateDirectory(PidDir);
            process.Refresh();
            ProcessRecord record = new ProcessRecord
            {
                pid = process.Id,
                executable_path = Path.GetFullPath(executable),
                start_time_utc = process.StartTime.ToUniversalTime().ToString("o"),
                session_token = sessionToken
            };
            File.WriteAllText(Path.Combine(PidDir, name + ".json"), Json.Serialize(record), new UTF8Encoding(false));
        }
        public static int StopOwnedProcesses(out int failures)
        {
            int stopped = 0;
            failures = 0;
            foreach (string name in new[] { "app", "llama" })
            {
                string recordPath = Path.Combine(PidDir, name + ".json");
                if (!File.Exists(recordPath)) continue;
                try
                {
                    ProcessRecord record = Json.Deserialize<ProcessRecord>(File.ReadAllText(recordPath));
                    string expected = name == "app" ? ServiceExe : LlamaExe;
                    Process process;
                    ProcessRecord verified;
                    if (!TryGetOwnedProcess(name, expected, out verified, out process))
                    {
                        try { Process.GetProcessById(record.pid); failures++; }
                        catch (ArgumentException) { File.Delete(recordPath); }
                        continue;
                    }
                    process.Kill();
                    bool exited = process.WaitForExit(10000) && process.HasExited;
                    if (!exited) { failures++; continue; }
                    File.Delete(recordPath);
                    stopped++;
                }
                catch { failures++; }
            }
            return stopped;
        }
        public static void OpenBrowser(string url)
        {
            ProcessStartInfo info = new ProcessStartInfo(url);
            info.UseShellExecute = true;
            Process.Start(info);
        }

        public static async Task DownloadAsync(string url, string destination, Action<long, long> progress)
        {
            bool isModelDownload = string.Equals(url, Config.ModelUrl, StringComparison.OrdinalIgnoreCase);
            string downloadName = isModelDownload ? "Google Gemma" : "the required Microsoft Windows component";
            string partial = destination + ".partial";
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            Exception lastError = null;
            for (int attempt = 1; attempt <= 4; attempt++)
            {
                try
                {
                    long existing = File.Exists(partial) ? new FileInfo(partial).Length : 0L;
                    if (existing < 0 || (isModelDownload && existing > Config.ModelBytes))
                    {
                        File.Delete(partial);
                        existing = 0L;
                    }
                    using (HttpClientHandler handler = new HttpClientHandler())
                    {
                        handler.AllowAutoRedirect = true;
                        handler.MaxAutomaticRedirections = 10;
                        handler.AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate;
                        handler.Proxy = WebRequest.DefaultWebProxy;
                        if (handler.Proxy != null) handler.Proxy.Credentials = CredentialCache.DefaultCredentials;
                        using (HttpClient client = new HttpClient(handler))
                        using (HttpRequestMessage request = new HttpRequestMessage(HttpMethod.Get, url))
                        {
                            client.Timeout = Timeout.InfiniteTimeSpan;
                            request.Headers.UserAgent.ParseAdd("RERCie/" + Config.Version + " (Windows; local grant-writing guide)");
                            request.Headers.Accept.ParseAdd("application/octet-stream");
                            if (existing > 0) request.Headers.Range = new RangeHeaderValue(existing, null);
                            using (HttpResponseMessage response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead))
                            {
                                if (response.StatusCode == HttpStatusCode.RequestedRangeNotSatisfiable)
                                {
                                    File.Delete(partial);
                                    throw new IOException("The saved partial download could not be resumed.");
                                }
                                response.EnsureSuccessStatusCode();
                                bool resumed = existing > 0 && response.StatusCode == HttpStatusCode.PartialContent;
                                long offset = resumed ? existing : 0L;
                                long contentLength = response.Content.Headers.ContentLength.GetValueOrDefault();
                                long total = contentLength > 0 ? offset + contentLength : (isModelDownload ? Config.ModelBytes : 0L);
                                FileMode mode = resumed ? FileMode.Append : FileMode.Create;
                                using (Stream input = await response.Content.ReadAsStreamAsync())
                                using (FileStream output = new FileStream(partial, mode, FileAccess.Write, FileShare.None, 131072, true))
                                {
                                    byte[] buffer = new byte[131072];
                                    long done = offset;
                                    if (progress != null) progress(done, total);
                                    int read;
                                    while ((read = await input.ReadAsync(buffer, 0, buffer.Length)) > 0)
                                    {
                                        await output.WriteAsync(buffer, 0, read);
                                        done += read;
                                        if (progress != null) progress(done, total);
                                    }
                                }
                            }
                        }
                    }
                    if (File.Exists(destination)) File.Delete(destination);
                    File.Move(partial, destination);
                    return;
                }
                catch (Exception error)
                {
                    lastError = error;
                }
                if (attempt < 4) await Task.Delay(attempt * 1500);
            }
            string detail = lastError == null ? "Unknown network error." : RootMessage(lastError);
            throw new InvalidOperationException("RERCie could not download " + downloadName + ". Check your internet connection and try again. The saved partial download will resume. Details: " + detail, lastError);
        }

        private static string RootMessage(Exception error)
        {
            Exception current = error;
            while (current.InnerException != null) current = current.InnerException;
            return string.IsNullOrWhiteSpace(current.Message) ? error.GetType().Name : current.Message;
        }

        public static async Task<object> ProbeModelDownloadAsync()
        {
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            using (HttpClientHandler handler = new HttpClientHandler())
            {
                handler.AllowAutoRedirect = true;
                handler.MaxAutomaticRedirections = 10;
                handler.AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate;
                handler.Proxy = WebRequest.DefaultWebProxy;
                if (handler.Proxy != null) handler.Proxy.Credentials = CredentialCache.DefaultCredentials;
                using (HttpClient client = new HttpClient(handler))
                using (HttpRequestMessage request = new HttpRequestMessage(HttpMethod.Get, Config.ModelUrl))
                {
                    client.Timeout = TimeSpan.FromSeconds(45);
                    request.Headers.UserAgent.ParseAdd("RERCie/" + Config.Version + " (Windows; download probe)");
                    request.Headers.Accept.ParseAdd("application/octet-stream");
                    request.Headers.Range = new RangeHeaderValue(0, 1023);
                    using (HttpResponseMessage response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead))
                    {
                        response.EnsureSuccessStatusCode();
                        byte[] body = await response.Content.ReadAsByteArrayAsync();
                        if (body.Length != 1024) throw new InvalidOperationException("The Gemma endpoint returned an unexpected probe size.");
                        return new { status = "PASS", http_status = (int)response.StatusCode, bytes = body.Length, model = Config.ModelName, source = Config.ModelPageUrl };
                    }
                }
            }
        }
    }

    internal sealed class AccessibleStatusLabel : Label
    {
        private int lastDownloadMilestone = -1;

        protected override void OnTextChanged(EventArgs e)
        {
            base.OnTextChanged(e);
            AccessibleDescription = Text;
            bool notify = true;
            const string prefix = "Downloading the local model... ";
            if ((Text ?? "").StartsWith(prefix, StringComparison.Ordinal))
            {
                int percentEnd = Text.IndexOf('%', prefix.Length);
                int percent;
                if (percentEnd > prefix.Length && int.TryParse(Text.Substring(prefix.Length, percentEnd - prefix.Length), out percent))
                {
                    int milestone = percent / 10;
                    notify = milestone != lastDownloadMilestone;
                    lastDownloadMilestone = milestone;
                }
            }
            else
            {
                lastDownloadMilestone = -1;
            }
            if (notify && IsHandleCreated)
                AccessibilityNotifyClients(AccessibleEvents.DescriptionChange, -1);
        }
    }

    internal sealed class MainForm : Form
    {
        private readonly AccessibleStatusLabel statusLabel = new AccessibleStatusLabel();
        private readonly ProgressBar progressBar = new ProgressBar();

        private readonly Button startButton = new Button();
        private readonly Button openButton = new Button();
        private readonly Button stopButton = new Button();
        private bool busy;

        public MainForm()
        {
            Text = "RERCie";
            ClientSize = new Size(700, 520);
            MinimumSize = new Size(716, 559);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.White;
            Font = new Font("Segoe UI", 9.5f);
            Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);

            PictureBox picture = new PictureBox();
            picture.Location = new Point(20, 24);
            picture.Size = new Size(220, 420);
            picture.SizeMode = PictureBoxSizeMode.Zoom;
            picture.AccessibleName = "RERCie, a river otter holding a field notebook";
            picture.AccessibleDescription = "RERCie is the outdoor guide character for this local grant-writing app.";
            string imagePath = Path.Combine(Runtime.Root, "assets", "rercie-otter.jpg");
            if (File.Exists(imagePath)) picture.Image = Image.FromFile(imagePath);
            Controls.Add(picture);

            RichTextBox brand = new RichTextBox();
            brand.Location = new Point(260, 20);
            brand.Size = new Size(410, 28);
            brand.BorderStyle = BorderStyle.None;
            brand.BackColor = Color.White;
            brand.ReadOnly = true;
            brand.TabStop = false;
            brand.ScrollBars = RichTextBoxScrollBars.None;
            brand.Rtf = @"{\rtf1\ansi\deff0{\fonttbl{\f0 Segoe UI;}}{\colortbl;\red0\green87\blue63;}\f0\fs20\cf1\b Recreation Economy \i for\i0  Rural Communities\b0}";
            Label title = MakeLabel("Meet RERCie", 260, 58, 410, 46, 24f, true, Color.FromArgb(23, 63, 53));
            Label intro = MakeLabel("RERCie helps you use a funding option and your project notes to make a first draft.", 260, 112, 410, 54, 11f, false, Color.FromArgb(27, 31, 35));
            Label boundary = MakeLabel("RERCie is a community-built tool. It is not an EPA grant program. It does not decide who can apply or submit an application for you.", 260, 174, 410, 64, 9.5f, false, Color.FromArgb(70, 80, 75));
            Controls.Add(brand); Controls.Add(title); Controls.Add(intro); Controls.Add(boundary);

            Label modelNote = MakeLabel("Google Gemma is about 0.81 GB. It stays on this computer.", 260, 244, 410, 32, 9.5f, true, Color.FromArgb(27, 31, 35));
            Controls.Add(modelNote);

            LinkLabel modelLink = MakeLink("View the model page", 260, 280, 150, Config.ModelPageUrl);
            LinkLabel licenseLink = MakeLink("Read the Apache license", 418, 280, 170, Config.ModelLicenseUrl);
            Controls.Add(modelLink); Controls.Add(licenseLink);

            Label licenseNote = MakeLabel("The model is open under Apache License 2.0.", 260, 310, 410, 36, 9.5f, false, Color.FromArgb(70, 80, 75));
            Controls.Add(licenseNote);




            statusLabel.Location = new Point(260, 360);
            statusLabel.Size = new Size(410, 44);
            statusLabel.Text = "Checking RERCie...";
            statusLabel.ForeColor = Color.FromArgb(70, 80, 75);
            statusLabel.AccessibleName = "RERCie status";
            statusLabel.AccessibleDescription = statusLabel.Text;
            Controls.Add(statusLabel);

            progressBar.Location = new Point(260, 408);
            progressBar.Size = new Size(410, 18);
            progressBar.Style = ProgressBarStyle.Continuous;
            progressBar.AccessibleName = "RERCie setup progress";
            progressBar.AccessibleDescription = "Shows download and startup progress.";
            Controls.Add(progressBar);

            startButton.Text = "Start RERCie";
            startButton.Location = new Point(260, 448);
            startButton.Size = new Size(130, 38);
            StylePrimary(startButton);
            startButton.Click += StartClicked;
            Controls.Add(startButton);

            openButton.Text = "Open RERCie";
            openButton.Location = new Point(398, 448);
            openButton.Size = new Size(130, 38);
            openButton.Click += delegate { Runtime.OpenBrowser(Runtime.AppBrowserUrl()); };
            Controls.Add(openButton);

            stopButton.Text = "Stop";
            stopButton.Location = new Point(536, 448);
            stopButton.Size = new Size(90, 38);
            stopButton.Click += StopClicked;
            Controls.Add(stopButton);

            Shown += async delegate { await RefreshStateAsync(); };
        }

        private Label MakeLabel(string text, int x, int y, int width, int height, float size, bool bold, Color color)
        {
            Label label = new Label();
            label.Text = text;
            label.Location = new Point(x, y);
            label.Size = new Size(width, height);
            label.Font = new Font("Segoe UI", size, bold ? FontStyle.Bold : FontStyle.Regular);
            label.ForeColor = color;
            return label;
        }

        private LinkLabel MakeLink(string text, int x, int y, int width, string url)
        {
            LinkLabel link = new LinkLabel();
            link.Text = text;
            link.Location = new Point(x, y);
            link.Size = new Size(width, 24);
            link.LinkColor = Color.FromArgb(27, 106, 143);
            link.LinkClicked += delegate { Runtime.OpenBrowser(url); };
            return link;
        }

        private void StylePrimary(Button button)
        {
            button.BackColor = Color.FromArgb(0, 87, 63);
            button.ForeColor = Color.White;
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderColor = Color.FromArgb(0, 87, 63);
        }

        private async Task RefreshStateAsync()
        {
            busy = true;
            RefreshButtons();
            try
            {
                statusLabel.Text = "Checking the installed files...";
                await Task.Run((Action)Runtime.VerifyPackage);
                bool modelReady = await Task.Run((Func<bool>)Runtime.ModelReady);
                bool appReady = Runtime.AppReady();

                statusLabel.Text = appReady ? "RERCie is ready. Open it in your browser." : modelReady ? "The local model is ready. Start RERCie when you are ready." : "Select Download and start. RERCie will check the model before it runs.";
            }
            catch (Exception error)
            {
                statusLabel.Text = error.Message;
                statusLabel.ForeColor = Color.FromArgb(139, 30, 30);
            }
            finally
            {
                busy = false;
                progressBar.Value = 0;
                RefreshButtons();
            }
        }

        private void RefreshButtons()
        {
            bool appReady = Runtime.AppReady();
            bool modelExists = File.Exists(Runtime.ModelPath) && new FileInfo(Runtime.ModelPath).Length == Config.ModelBytes;
            startButton.Text = modelExists ? "Start RERCie" : "Download and start";
            startButton.Enabled = !busy && !appReady;
            openButton.Enabled = !busy && appReady;
            stopButton.Enabled = !busy && appReady;
        }

        private async void StartClicked(object sender, EventArgs args)
        {
            busy = true;
            statusLabel.ForeColor = Color.FromArgb(70, 80, 75);
            RefreshButtons();
            try
            {
                statusLabel.Text = "Checking the installed files...";
                await Task.Run((Action)Runtime.VerifyPackage);
                if (!Runtime.VcRuntimeReady()) await InstallWindowsRuntimeAsync();
                bool modelReady = await Task.Run((Func<bool>)Runtime.ModelReady);
                if (!modelReady)
                {

                    statusLabel.Text = "Downloading the local model...";
                    await Runtime.DownloadAsync(Config.ModelUrl, Runtime.ModelPath, UpdateDownloadProgress);
                    statusLabel.Text = "Checking the model file...";
                    modelReady = await Task.Run((Func<bool>)Runtime.ModelReady);
                    if (!modelReady)
                    {
                        try { File.Delete(Runtime.ModelPath); } catch { }
                        throw new InvalidOperationException("The model did not pass its safety check. It was removed. Try again.");
                    }
                }
                await StartServicesAsync();
                progressBar.Value = 100;
                statusLabel.Text = "RERCie is ready. Your browser is opening.";
                Runtime.OpenBrowser(Runtime.AppBrowserUrl());
            }
            catch (Exception error)
            {
                statusLabel.Text = error.Message;
                statusLabel.ForeColor = Color.FromArgb(139, 30, 30);
                MessageBox.Show(this, error.Message, "RERCie could not start", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            finally
            {
                busy = false;
                RefreshButtons();
            }
        }

        private void UpdateDownloadProgress(long done, long total)
        {
            long expected = total > 0 ? total : Config.ModelBytes;
            int percent = (int)Math.Max(0, Math.Min(100, done * 100L / Math.Max(1L, expected)));
            progressBar.Value = percent;
            statusLabel.Text = string.Format("Downloading the local model... {0}% ({1:0.0} of {2:0.0} MB)", percent, done / 1048576d, expected / 1048576d);
        }

        private async Task InstallWindowsRuntimeAsync()
        {
            DialogResult choice = MessageBox.Show(this, "RERCie needs a standard Microsoft Windows component. Windows may ask for permission while the official Microsoft installer runs.", "One Windows component is needed", MessageBoxButtons.OKCancel, MessageBoxIcon.Information);
            if (choice != DialogResult.OK) throw new InvalidOperationException("Setup stopped before the Windows component was installed.");
            string installer = Path.Combine(Path.GetTempPath(), "RERCie-vc_redist.x64.exe");
            statusLabel.Text = "Downloading the Microsoft Windows component...";
            await Runtime.DownloadAsync(Config.VcRuntimeUrl, installer, null);
            if (!AuthenticodeVerifier.IsTrustedMicrosoftFile(installer))
            {
                try { File.Delete(installer); } catch { }
                throw new InvalidOperationException("The Microsoft installer did not pass its signature check.");
            }
            ProcessStartInfo info = new ProcessStartInfo(installer, "/install /quiet /norestart");
            info.UseShellExecute = true;
            info.Verb = "runas";
            Process process = Process.Start(info);
            if (process == null) throw new InvalidOperationException("The Microsoft installer could not start.");
            process.WaitForExit();
            try { File.Delete(installer); } catch { }
            if (process.ExitCode != 0 && process.ExitCode != 1638 && process.ExitCode != 3010) throw new InvalidOperationException("The Microsoft installer returned error " + process.ExitCode + ".");
            if (!Runtime.VcRuntimeReady()) throw new InvalidOperationException("The Windows component is still missing. Restart Windows, then open RERCie again.");
        }

        private async Task StartServicesAsync()
        {
            if (!Runtime.ModelServerReady())
            {
                if (Runtime.PortInUse(8788)) throw new InvalidOperationException("Another program is blocking RERCie. Close it, then start RERCie again.");
                int threads = Math.Max(2, Environment.ProcessorCount - 1);
                string llamaArgs = "-m \"" + Runtime.ModelPath + "\" --host 127.0.0.1 --port 8788 -c 8192 -t " + threads;
                Runtime.StartHidden("llama", Runtime.LlamaExe, llamaArgs, Runtime.LlamaDir, null, null);
                statusLabel.Text = "Starting the local writing model...";
                await Runtime.WaitForAsync(Runtime.ModelServerReady, 150, "The local model did not start. Restart RERCie and try again.");
            }
            if (!Runtime.AppReady())
            {
                if (Runtime.PortInUse(8789)) throw new InvalidOperationException("Another program is blocking RERCie. Close it, then start RERCie again.");
                string sessionToken = Runtime.CreateSessionToken();
                Dictionary<string, string> environment = new Dictionary<string, string>();
                environment["RERCIE_LOCAL_CHAT_URL"] = "http://127.0.0.1:8788/v1/chat/completions";
                environment["RERCIE_LOCAL_HEALTH_URL"] = Config.ModelHealthUrl;
                environment["RERCIE_LOCAL_MODELS_URL"] = Config.ModelListUrl;
                environment["RERCIE_SESSION_TOKEN"] = sessionToken;
                environment["RERCIE_EXPECTED_HOST"] = "127.0.0.1:8789";
                environment["RERCIE_APP_ROOT"] = Runtime.Root;
                Runtime.StartHidden("app", Runtime.ServiceExe, "--serve --host 127.0.0.1 --port 8789", Runtime.ServiceDir, environment, sessionToken);
                statusLabel.Text = "Starting RERCie...";
                await Runtime.WaitForAsync(Runtime.AppReady, 35, "RERCie did not start. Restart the app and try again.");
            }
        }

        private async void StopClicked(object sender, EventArgs args)
        {
            busy = true;
            RefreshButtons();
            int failures = 0;
            int stopped = await Task.Run(() => Runtime.StopOwnedProcesses(out failures));
            statusLabel.Text = failures > 0 ? "RERCie could not stop every local process. Close RERCie and try again." : stopped > 0 ? "RERCie stopped." : "RERCie was already stopped.";
            progressBar.Value = 0;
            busy = false;
            RefreshButtons();
        }
    }

    internal static class AuthenticodeVerifier
    {
        private static readonly Guid VerifyAction = new Guid("00AAC56B-CD44-11d0-8CC2-00C04FC295EE");

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct WinTrustFileInfo
        {
            public uint cbStruct;
            [MarshalAs(UnmanagedType.LPWStr)] public string pcwszFilePath;
            public IntPtr hFile;
            public IntPtr pgKnownSubject;
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct WinTrustData
        {
            public uint cbStruct;
            public IntPtr pPolicyCallbackData;
            public IntPtr pSIPClientData;
            public uint dwUIChoice;
            public uint fdwRevocationChecks;
            public uint dwUnionChoice;
            public IntPtr pFile;
            public uint dwStateAction;
            public IntPtr hWVTStateData;
            public IntPtr pwszURLReference;
            public uint dwProvFlags;
            public uint dwUIContext;
        }

        [DllImport("wintrust.dll", ExactSpelling = true, SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern uint WinVerifyTrust(IntPtr hwnd, [MarshalAs(UnmanagedType.LPStruct)] Guid action, IntPtr data);

        public static bool IsTrustedMicrosoftFile(string path)
        {
            IntPtr filePtr = IntPtr.Zero;
            IntPtr dataPtr = IntPtr.Zero;
            try
            {
                WinTrustFileInfo file = new WinTrustFileInfo();
                file.cbStruct = (uint)Marshal.SizeOf(typeof(WinTrustFileInfo));
                file.pcwszFilePath = path;
                filePtr = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(WinTrustFileInfo)));
                Marshal.StructureToPtr(file, filePtr, false);

                WinTrustData data = new WinTrustData();
                data.cbStruct = (uint)Marshal.SizeOf(typeof(WinTrustData));
                data.dwUIChoice = 2;
                data.fdwRevocationChecks = 0;
                data.dwUnionChoice = 1;
                data.pFile = filePtr;
                data.dwStateAction = 0;
                data.dwProvFlags = 0;
                dataPtr = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(WinTrustData)));
                Marshal.StructureToPtr(data, dataPtr, false);
                if (WinVerifyTrust(IntPtr.Zero, VerifyAction, dataPtr) != 0) return false;
                X509Certificate2 certificate = new X509Certificate2(X509Certificate.CreateFromSignedFile(path));
                return certificate.Subject.IndexOf("Microsoft Corporation", StringComparison.OrdinalIgnoreCase) >= 0;
            }
            catch { return false; }
            finally
            {
                if (dataPtr != IntPtr.Zero) { Marshal.DestroyStructure(dataPtr, typeof(WinTrustData)); Marshal.FreeHGlobal(dataPtr); }
                if (filePtr != IntPtr.Zero) { Marshal.DestroyStructure(filePtr, typeof(WinTrustFileInfo)); Marshal.FreeHGlobal(filePtr); }
            }
        }
    }

    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            if (Array.IndexOf(args, "--stop") >= 0)
            {
                int failures;
                Runtime.StopOwnedProcesses(out failures);
                return failures == 0 ? 0 : 1;
            }
            int probeIndex = Array.IndexOf(args, "--probe-download-output");
            if (probeIndex >= 0 && probeIndex + 1 < args.Length)
            {
                try
                {
                    object result = Runtime.ProbeModelDownloadAsync().GetAwaiter().GetResult();
                    File.WriteAllText(args[probeIndex + 1], new JavaScriptSerializer().Serialize(result), new UTF8Encoding(false));
                    return 0;
                }
                catch (Exception error)
                {
                    File.WriteAllText(args[probeIndex + 1], "{\"status\":\"FAIL\",\"error\":" + new JavaScriptSerializer().Serialize(error.Message) + "}", new UTF8Encoding(false));
                    return 1;
                }
            }
            int smokeIndex = Array.IndexOf(args, "--smoke-output");
            if (smokeIndex >= 0 && smokeIndex + 1 < args.Length)
            {
                try
                {
                    Runtime.VerifyPackage();
                    string json = new JavaScriptSerializer().Serialize(new
                    {
                        status = "PASS",
                        app = "RERCie",
                        version = Config.Version,
                        powershell_required = false,
                        model_name = Config.ModelName,
                        model_sha256 = Config.ModelSha256,
                        model_source = Config.ModelPageUrl,
                        model_download_bytes = Config.ModelBytes,
                        launcher = Application.ExecutablePath
                    });
                    File.WriteAllText(args[smokeIndex + 1], json, new UTF8Encoding(false));
                    return 0;
                }
                catch (Exception error)
                {
                    File.WriteAllText(args[smokeIndex + 1], "{\"status\":\"FAIL\",\"error\":" + new JavaScriptSerializer().Serialize(error.Message) + "}", new UTF8Encoding(false));
                    return 1;
                }
            }

            bool created;
            using (Mutex mutex = new Mutex(true, "Local\\RERCie-0.3", out created))
            {
                if (!created)
                {
                    if (!Runtime.AppReady()) return 1;
                    Runtime.OpenBrowser(Runtime.AppBrowserUrl());
                    return 0;
                }
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                Application.Run(new MainForm());
            }
            return 0;
        }
    }
}