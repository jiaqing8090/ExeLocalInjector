using System;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
using System.Linq;
using System.Drawing;
using System.Threading;
using System.Net;
using System.Collections.Specialized;
using System.Security.Cryptography;
using System.Diagnostics;
using System.Collections.Generic;
using System.Text.RegularExpressions;

[assembly: System.Reflection.AssemblyVersion("1.0.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.0.0.0")]

namespace ExeProtector
{
    static class Program
    {
        // 标记位与配置
        private static readonly byte[] D_M = Encoding.ASCII.GetBytes("__J_D__");
        private static readonly byte[] K_M = Encoding.ASCII.GetBytes("__J_K__");
        
        private static string AppKey = "";
        private static string AppSecret = "";
        private static string ApiHost = "";
        private static string OriginalName = "app.exe";
        private static string CurrentVersion = "__J_V_000000000000000000000000000000000000000000000000000000000__"; // 版本占位符
        private static byte[] PayloadData = null;
        private static byte XorKey = 0;
        private static long ServerTimeOffset = 0; // 时间偏移量
        private static int HeartbeatInterval = 60; // 心跳间隔 (秒)，默认60
        private static string SiteName = "验证系统";
        private static string BuyLink = "";
        private static string ContactLink = "";
        private static string RemoteVarsJson = "{}";
        private static bool TrialActive = false;
        private static string TrialExpireTime = "";
        private static string LastShopOrderNo = "";
        private static string NoticeText = "";

        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            
            // 解决老版本 .NET 不默认支持 TLS 1.2 导致的 HTTPS 请求失败
            try { ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072 | (SecurityProtocolType)768 | (SecurityProtocolType)192; } catch { }

            // 清洗占位符
            CurrentVersion = CurrentVersion.Trim('_', '0', ' ');

            if (!ExtractMetadata())
            {
                MessageBox.Show("程序损坏或未经过授权处理。", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // 1. 启动即同步云端配置
            FetchConfig();

            if (TrialActive)
            {
                StartHeartbeat("");
                RunPayload();
                return;
            }

            string cacheName = "Auth_" + AppKey.Trim() + ".dat";
            string cachePath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), cacheName);
            string savedCard = "";
            if (File.Exists(cachePath))
            {
                try { savedCard = File.ReadAllText(cachePath).Trim(); } catch { }
            }

            if (!string.IsNullOrEmpty(savedCard))
            {
                string expiry = "";
                if (VerifyCard(savedCard, true, out expiry))
                {
                    MessageBox.Show("自动登录成功！\n到期时间：" + expiry, "授权通过", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    StartHeartbeat(savedCard);
                    RunPayload();
                    return;
                }
            }

            using (LoginForm login = new LoginForm(BuyLink, ContactLink))
            {
                if (login.ShowDialog() == DialogResult.OK)
                {
                    string expiry = "";
                    if (VerifyCard(login.CardCode, false, out expiry))
                    {
                        if (login.RememberCard)
                        {
                            try { File.WriteAllText(cachePath, login.CardCode); } catch { }
                        }
                        
                        MessageBox.Show("验证成功！\n到期时间：" + expiry, "授权通过", MessageBoxButtons.OK, MessageBoxIcon.Information);
                        StartHeartbeat(login.CardCode);
                        RunPayload();
                    }
                    else
                    {
                        Application.Exit();
                    }
                }
                else
                {
                    Application.Exit();
                }
            }
        }

        static long GetUnixTime()
        {
            return (long)(DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalSeconds;
        }

        static void FetchConfig()
        {
            try {
                string deviceId = GetDeviceId();
                string timestamp = GetUnixTime().ToString();
                string nonce = new Random().Next(100000, 999999).ToString();
                string raw = string.Format("{0}{1}{2}{3}", AppKey.Trim(), AppSecret.Trim(), timestamp, nonce);
                string sign = ComputeSha256(raw);

                using (var client = new WebClient()) {
                    client.Encoding = Encoding.UTF8;
                    client.Headers[HttpRequestHeader.ContentType] = "application/json";
                    client.Proxy = null; // 禁用代理加快速度

                    string url = string.Format("{0}/api/init", ApiHost.TrimEnd('/'));
                    string json = string.Format("{{\"app_key\":\"{0}\",\"device_id\":\"{1}\",\"timestamp\":\"{2}\",\"nonce\":\"{3}\",\"sign\":\"{4}\",\"platform\":\"windows\",\"current_version\":\"{5}\"}}", 
                        AppKey.Trim(), deviceId, timestamp, nonce, sign, CurrentVersion);
                    
                    string res = client.UploadString(url, "POST", json);
                    
                    // 同步站点名称 (API 返回的 notice 可能会有站点名，这里优先使用元数据注入的)
                    string sName = JsonValue(res, "site_name");
                    if (!string.IsNullOrEmpty(sName)) SiteName = sName;

                    // 调试弹窗：查看服务器返回的原始数据 (排查热更新字段是否存在)
                    // MessageBox.Show("服务器返回: " + res, "调试");
                    
                    BuyLink = JsonValue(res, "buy_link");
                    ContactLink = JsonValue(res, "contact_link");
                    RemoteVarsJson = JsonObjectValue(res, "remote_vars");
                    TrialActive = JsonValue(res, "status") == "trial";
                    TrialExpireTime = JsonValue(res, "expire_time");
                    NoticeText = JsonValue(res, "notice");
                    string interval = JsonValue(res, "heartbeat_interval");
                    if (!string.IsNullOrEmpty(interval)) {
                        int.TryParse(interval, out HeartbeatInterval);
                        if (HeartbeatInterval < 10) HeartbeatInterval = 10; // 防御性保护：最低 10 秒
                    }

                    // 启动即检查热更新
                    if (res.Contains("\"hotupdate\"") && Regex.IsMatch(res, "\"has_update\"\\s*:\\s*true"))
                    {
                        HandleHotUpdate(res);
                    }
                }
            } catch { }
        }

        static bool ExtractMetadata()
        {
            try
            {
                byte[] self = File.ReadAllBytes(Application.ExecutablePath);
                
                // 1. 查找数据标记
                int dataIdx = FindPattern(self, D_M);
                if (dataIdx == -1) return false;

                // 2. 查找 Key 标记
                int keyIdx = FindPattern(self, K_M);
                if (keyIdx == -1) return false;

                // 3. 提取 XOR 密钥和加密数据
                XorKey = self[dataIdx + D_M.Length];
                int payloadStart = dataIdx + D_M.Length + 1;
                int payloadLen = keyIdx - payloadStart;
                PayloadData = new byte[payloadLen];
                Array.Copy(self, payloadStart, PayloadData, 0, payloadLen);

                // 4. 解密数据
                for (int i = 0; i < PayloadData.Length; i++)
                {
                    PayloadData[i] = (byte)(PayloadData[i] ^ XorKey);
                }

                // 5. 提取元数据 (AppKey|AppSecret|Host|Name|Version)
                string rawMeta = Encoding.UTF8.GetString(self, keyIdx + K_M.Length, self.Length - (keyIdx + K_M.Length)).Trim('\0', ' ', '\r', '\n');
                string[] parts = rawMeta.Split('|');
                if (parts.Length >= 3)
                {
                    AppKey = parts[0].Trim();
                    AppSecret = parts[1].Trim();
                    ApiHost = parts[2].Trim();
                    if (parts.Length >= 4) OriginalName = parts[3].Trim();
                    if (parts.Length >= 5) CurrentVersion = parts[4].Trim();
                    if (parts.Length >= 6) SiteName = parts[5].Trim();
                }
                return true;
            }
            catch { return false; }
        }

        static int FindPattern(byte[] source, byte[] pattern)
        {
            for (int i = 0; i <= source.Length - pattern.Length; i++)
            {
                bool match = true;
                for (int j = 0; j < pattern.Length; j++)
                {
                    if (source[i + j] != pattern[j]) { match = false; break; }
                }
                if (match) return i;
            }
            return -1;
        }

        static bool VerifyCard(string card, bool isAuto, out string expiryTime)
        {
            expiryTime = "未知";
            try
            {
                string deviceId = GetDeviceId();
                string timestamp = (GetUnixTime() + ServerTimeOffset).ToString();
                string nonce = new Random().Next(100000, 999999).ToString();

                // 签名算法: sha256(app_key + app_secret + timestamp + nonce)
                string raw = string.Format("{0}{1}{2}{3}", AppKey.Trim(), AppSecret.Trim(), timestamp, nonce);
                string sign = ComputeSha256(raw);

                // 发送请求
                using (var client = new WebClient())
                {
                    client.Encoding = Encoding.UTF8;
                    client.Headers[HttpRequestHeader.ContentType] = "application/json";
                    client.Proxy = null;

                    string url = string.Format("{0}/api/init", ApiHost.TrimEnd('/'));
                    string json = string.Format("{{\"app_key\":\"{0}\",\"card_code\":\"{1}\",\"device_id\":\"{2}\",\"timestamp\":\"{3}\",\"nonce\":\"{4}\",\"sign\":\"{5}\",\"platform\":\"windows\",\"is_auto\":{6},\"current_version\":\"{7}\"}}", 
                        AppKey.Trim(), card, deviceId, timestamp, nonce, sign, isAuto ? "true" : "false", CurrentVersion);
                    
                    string result = client.UploadString(url, "POST", json);

                    // 1. 同步服务器时间与心跳间隔 (防御性解析)
                    string sTime = JsonValue(result, "server_time");
                    if (!string.IsNullOrEmpty(sTime)) {
                        long sTimeVal;
                        if (long.TryParse(sTime, out sTimeVal)) {
                            ServerTimeOffset = sTimeVal - GetUnixTime();
                        }
                    }
                    string sInterval = JsonValue(result, "heartbeat_interval");
                    if (!string.IsNullOrEmpty(sInterval)) {
                        int intervalVal;
                        if (int.TryParse(sInterval, out intervalVal)) {
                            HeartbeatInterval = intervalVal;
                            if (HeartbeatInterval < 10) HeartbeatInterval = 10;
                        }
                    }

                    // 2. 检查热更新 (改用正则表达式，彻底解决空格和引号导致的匹配失败)
                    if (result.Contains("\"hotupdate\""))
                    {
                        // 匹配 "has_update": true 或 "has_update":true
                        if (Regex.IsMatch(result, "\"has_update\"\\s*:\\s*true"))
                        {
                            HandleHotUpdate(result);
                        }
                    }
                    
                    // 3. 校验服务器响应签名 (安全核心)
                    string serverSign = JsonValue(result, "sign");
                    if (!string.IsNullOrEmpty(serverSign)) {
                        string status = JsonValue(result, "status").Trim();
                        string exp = JsonValue(result, "expire_time").Trim();
                        
                        // 规则: 0 + status + expire_time + secret (api_init 固定传 0)
                        string signRaw = "0" + status + exp + AppSecret.Trim();
                        string calcSign = ComputeSha256(signRaw);
                        
                        if (calcSign.ToLower() != serverSign.ToLower()) {
                            // 暂时仅提醒，不拦截，方便排查
                            MessageBox.Show("校验异常(可忽略): 签名不匹配。\n预期: " + serverSign.Substring(0, 8) + "...\n实际: " + calcSign.Substring(0, 8) + "...", "安全提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                        }
                    }

                    // 必须包含 "status":"active" 才是真正的验证成功
                    if (result.Contains("\"status\":\"active\"") || result.Contains("\"status\": \"active\""))
                    {
                        // 提取过期时间
                        if (result.Contains("\"expire_time\""))
                        {
                            int start = result.IndexOf("\"expire_time\"") + 13;
                            int startQuote = result.IndexOf("\"", start);
                            int endQuote = result.IndexOf("\"", startQuote + 1);
                            if (startQuote != -1 && endQuote != -1)
                            {
                                expiryTime = result.Substring(startQuote + 1, endQuote - startQuote - 1);
                            }
                        }
                        
                        // 4. 展示系统公告
                        string notice = JsonValue(result, "popup_announcement");
                        if (!string.IsNullOrEmpty(notice)) {
                            MessageBox.Show(notice, "系统公告", MessageBoxButtons.OK, MessageBoxIcon.Information);
                        }
                        
                        return true;
                    }
                    else
                    {
                        // 如果是静默验证失败，尝试删除失效的缓存
                        try {
                            string cachePath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Auth_" + AppKey.Trim() + ".dat");
                            if (File.Exists(cachePath)) File.Delete(cachePath);
                        } catch { }

                        // 鲁棒的错误消息提取
                        string errorMsg = "激活码无效或已过期。";
                        if (result.Contains("\"msg\""))
                        {
                            int msgIdx = result.IndexOf("\"msg\"");
                            int startQuote = result.IndexOf("\"", msgIdx + 5);
                            int endQuote = result.IndexOf("\"", startQuote + 1);
                            if (startQuote != -1 && endQuote != -1)
                            {
                                errorMsg = result.Substring(startQuote + 1, endQuote - startQuote - 1);
                            }
                        }
                        
                        MessageBox.Show(errorMsg, "验证失败", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        return false;
                    }
                }
            }
            catch (Exception ex)
            {
                string detail = ex.Message;
                if (ex.InnerException != null) {
                    detail = ex.InnerException.Message;
                }
                MessageBox.Show("网络连接失败: " + detail + "\n\nHost: " + ApiHost, "通讯错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
        }

        static void RunPayload()
        {
            // 恢复 VMP 级别的“原地释放 + 瞬时更名 + 物理锁定”逻辑
            // 这是兼容性最强且最接近商业加壳软件的行为
            RunPayloadAsDisk();
        }

        static void RunPayloadAsDisk()
        {
            try
            {
                string dir = Path.GetDirectoryName(Application.ExecutablePath);
                string selfName = Path.GetFileName(Application.ExecutablePath);
                
                // 【逻辑更新】如果没有填写自定义名，或者是默认名，或者与自己重名，则生成随机名
                string finalPayloadName = OriginalName;
                if (string.IsNullOrEmpty(finalPayloadName) || 
                    finalPayloadName == "app.exe" || 
                    string.Equals(finalPayloadName, selfName, StringComparison.OrdinalIgnoreCase))
                {
                    finalPayloadName = ".~vmp" + Guid.NewGuid().ToString("N").Substring(0, 6) + ".exe";
                }

                string targetPath = Path.Combine(dir, finalPayloadName);

                // 1. 尝试释放 (支持多开)
                bool needWrite = true;
                if (File.Exists(targetPath))
                {
                    try { File.Delete(targetPath); } catch { needWrite = false; }
                }

                if (needWrite)
                {
                    File.WriteAllBytes(targetPath, PayloadData);
                }

                // 2. 强制隐藏副本
                try { File.SetAttributes(targetPath, FileAttributes.Hidden | FileAttributes.System); } catch { }

                // 3. 启动进程
                Process p = new Process();
                p.StartInfo.FileName = targetPath;
                p.StartInfo.WorkingDirectory = dir;
                p.StartInfo.UseShellExecute = false;
                p.StartInfo.EnvironmentVariables["AUTH_REMOTE_VARS_JSON"] = RemoteVarsJson ?? "{}";
                p.StartInfo.EnvironmentVariables["AUTH_TRIAL_ACTIVE"] = TrialActive ? "1" : "0";
                p.StartInfo.EnvironmentVariables["AUTH_TRIAL_EXPIRE_TIME"] = TrialExpireTime ?? "";
                p.Start();
                
                // 4. 异步守护逻辑 (兼容 Python 启动)
                new Thread(() => {
                    try {
                        // 共享读锁定：防止被复制，但允许 Python 读取资源
                        using (FileStream fs = new FileStream(targetPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                        {
                            p.WaitForExit();
                        }
                        
                        // 5. 退出后清理
                        Thread.Sleep(800);
                        if (File.Exists(targetPath)) try { File.Delete(targetPath); } catch { }
                    } catch { }
                }).Start();
            }
            catch (Exception ex)
            {
                MessageBox.Show("启动失败: " + ex.Message, "系统错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        static string GetDeviceId()
        {
            try
            {
                string id = Environment.MachineName + Environment.UserName;
                using (var sha = new SHA256Managed())
                {
                    byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(id));
                    return BitConverter.ToString(hash).Replace("-", "").Substring(0, 16);
                }
            }
            catch { return "WIN_DEV_FALLBACK"; }
        }

        static void StartHeartbeat(string card)
        {
            new Thread(() => {
                while (true)
                {
                    Thread.Sleep(HeartbeatInterval * 1000); 
                    try {
                        string timestamp = (GetUnixTime() + ServerTimeOffset).ToString();
                        string nonce = new Random().Next(100000, 999999).ToString();
                        string raw = string.Format("{0}{1}{2}{3}", AppKey.Trim(), AppSecret.Trim(), timestamp, nonce);
                        string sign = ComputeSha256(raw);

                        using (var client = new WebClient()) {
                            client.Encoding = Encoding.UTF8;
                            client.Headers[HttpRequestHeader.ContentType] = "application/json";
                            client.Proxy = null;

                            string url = string.Format("{0}/api/heartbeat", ApiHost.TrimEnd('/'));
                            string json = string.Format("{{\"app_key\":\"{0}\",\"code\":\"{1}\",\"device_id\":\"{2}\",\"timestamp\":\"{3}\",\"nonce\":\"{4}\",\"sign\":\"{5}\",\"platform\":\"windows\"}}", 
                                AppKey.Trim(), card, GetDeviceId(), timestamp, nonce, sign);
                            
                            string res = client.UploadString(url, "POST", json);
                            
                            if (JsonValue(res, "code") == "1") {
                                string msg = JsonValue(res, "msg");
                                if (string.IsNullOrEmpty(msg)) msg = "授权已失效或在后台被禁用。";
                                MessageBox.Show(msg, "安全校验失败", MessageBoxButtons.OK, MessageBoxIcon.Stop);
                                Environment.Exit(0);
                            }
                        }
                    } catch { }
                }
            }) { IsBackground = true }.Start();
        }

        static void HandleHotUpdate(string json)
        {
            try
            {
                string version = JsonValue(json, "update_version");
                string url = JsonValue(json, "update_url");
                string changelog = JsonValue(json, "changelog");
                string typeStr = JsonValue(json, "update_type"); 

                string msg = string.Format("发现新版本: {0}\n\n更新日志:\n{1}\n\n是否立即前往更新？", version, changelog);
                bool isMandatory = (typeStr == "1" || json.Contains("\"update_type\":1") || json.Contains("\"update_type\": 1"));

                if (isMandatory) 
                {
                    MessageBox.Show(msg, SiteName + " - 强制更新", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    Process.Start(url);
                    Environment.Exit(0);
                }
                else 
                {
                    if (MessageBox.Show(msg, SiteName + " - 建议更新", MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes)
                    {
                        Process.Start(url);
                        Environment.Exit(0);
                    }
                }
            }
            catch { }
        }

        internal static string GetNoticeText() { return NoticeText ?? ""; }

        internal static string PurchaseOnline()
        {
            try {
                string ts = (GetUnixTime() + ServerTimeOffset).ToString();
                string nonce = Guid.NewGuid().ToString("N").Substring(0, 16);
                string sign = ComputeSha256(AppKey.Trim() + AppSecret.Trim() + ts + nonce);
                string body = string.Format("{{\"app_key\":\"{0}\",\"timestamp\":\"{1}\",\"nonce\":\"{2}\",\"sign\":\"{3}\",\"platform\":\"windows\"}}", AppKey.Trim(), ts, nonce, sign);
                string packages;
                using (var client = NewJsonClient()) packages = client.UploadString(ApiHost.TrimEnd('/') + "/api/shop/packages", "POST", body);
                string[] rows = JsonArrayObjects(packages, "data");
                if (rows.Length == 0) { MessageBox.Show(JsonValue(packages, "msg") ?? "当前没有可购买套餐。", "在线激活"); return ""; }
                int selected = SelectChoice("选择套餐", rows.Select((r, i) => (i + 1) + ". " + JsonValue(r, "name") + "    ¥" + JsonValue(r, "price")).ToArray());
                if (selected < 0) return "";
                string packageId = JsonValue(rows[selected], "package_id");
                string[] methods = JsonArrayObjects(packages, "payment_methods");
                if (methods.Length == 0 && packages.IndexOf("\"payment_methods\"", StringComparison.OrdinalIgnoreCase) < 0) methods = new[] { "{\"code\":\"alipay\",\"name\":\"支付宝\"}", "{\"code\":\"wechat\",\"name\":\"微信支付\"}" };
                if (methods.Length == 0) { MessageBox.Show("商家暂未配置在线支付。", "在线激活"); return ""; }
                int payIndex = SelectChoice("选择支付方式", methods.Select(m => JsonValue(m, "name")).ToArray());
                if (payIndex < 0) return "";
                string payType = JsonValue(methods[payIndex], "code");
                ts = (GetUnixTime() + ServerTimeOffset).ToString(); nonce = Guid.NewGuid().ToString("N").Substring(0, 16); sign = ComputeSha256(AppKey.Trim() + AppSecret.Trim() + ts + nonce);
                string orderBody = string.Format("{{\"app_key\":\"{0}\",\"package_id\":{1},\"device_id\":\"{2}\",\"pay_type\":\"{3}\",\"auto_activate\":true,\"platform\":\"windows\",\"timestamp\":\"{4}\",\"nonce\":\"{5}\",\"sign\":\"{6}\"}}", AppKey.Trim(), packageId, GetDeviceId(), payType, ts, nonce, sign);
                string order; using (var client = NewJsonClient()) order = client.UploadString(ApiHost.TrimEnd('/') + "/api/shop/order/create", "POST", orderBody);
                string orderData = JsonObjectValue(order, "data"); string orderNo = JsonValue(orderData, "order_no"); string payUrl = JsonValue(orderData, "pay_url");
                if (string.IsNullOrEmpty(orderNo) || string.IsNullOrEmpty(payUrl)) { MessageBox.Show(JsonValue(order, "msg"), "创建订单失败"); return ""; }
                LastShopOrderNo = orderNo; Process.Start(payUrl);
                for (int i = 0; i < 60; i++) {
                    Thread.Sleep(2000); ts = (GetUnixTime() + ServerTimeOffset).ToString(); nonce = Guid.NewGuid().ToString("N").Substring(0, 16); sign = ComputeSha256(AppKey.Trim() + AppSecret.Trim() + ts + nonce);
                    string statusBody = string.Format("{{\"app_key\":\"{0}\",\"order_no\":\"{1}\",\"device_id\":\"{2}\",\"platform\":\"windows\",\"timestamp\":\"{3}\",\"nonce\":\"{4}\",\"sign\":\"{5}\"}}", AppKey.Trim(), orderNo, GetDeviceId(), ts, nonce, sign);
                    string status; using (var client = NewJsonClient()) status = client.UploadString(ApiHost.TrimEnd('/') + "/api/shop/order/status", "POST", statusBody);
                    string data = JsonObjectValue(status, "data"); string card = JsonValue(data, "key_code");
                    if ((JsonValue(data, "paid") == "true" || JsonValue(data, "activated") == "1") && !string.IsNullOrEmpty(card)) return card;
                    Application.DoEvents();
                }
                MessageBox.Show("暂未查询到支付结果，请稍后重试。", "在线激活");
            } catch (Exception ex) { MessageBox.Show("在线激活失败：" + ex.Message, "错误"); }
            return "";
        }

        static WebClient NewJsonClient() { var c = new WebClient(); c.Encoding = Encoding.UTF8; c.Headers[HttpRequestHeader.ContentType] = "application/json; charset=utf-8"; c.Proxy = null; return c; }

        static int SelectChoice(string title, string[] labels)
        {
            using (Form f = new Form()) {
                f.Text = title; f.Width = 460; f.Height = 180 + labels.Length * 28; f.StartPosition = FormStartPosition.CenterScreen; f.FormBorderStyle = FormBorderStyle.FixedDialog;
                ListBox list = new ListBox { Left = 15, Top = 15, Width = 415, Height = Math.Max(80, labels.Length * 26) }; list.Items.AddRange(labels); if (labels.Length > 0) list.SelectedIndex = 0;
                Button ok = new Button { Text = "确定", Left = 275, Top = list.Bottom + 10, Width = 70, DialogResult = DialogResult.OK };
                Button cancel = new Button { Text = "取消", Left = 360, Top = list.Bottom + 10, Width = 70, DialogResult = DialogResult.Cancel };
                f.Controls.Add(list); f.Controls.Add(ok); f.Controls.Add(cancel); f.AcceptButton = ok; f.CancelButton = cancel;
                return f.ShowDialog() == DialogResult.OK ? list.SelectedIndex : -1;
            }
        }

        static string[] JsonArrayObjects(string json, string key)
        {
            try { string marker = "\"" + key + "\""; int idx = json.IndexOf(marker); if (idx < 0) return new string[0]; int start = json.IndexOf('[', idx + marker.Length); if (start < 0) return new string[0]; int depth = 0; bool quoted = false, escaped = false; int objectStart = -1; List<string> result = new List<string>(); for (int i = start + 1; i < json.Length; i++) { char c = json[i]; if (escaped) { escaped = false; continue; } if (c == '\\' && quoted) { escaped = true; continue; } if (c == '"') { quoted = !quoted; continue; } if (quoted) continue; if (c == '{') { if (depth == 0) objectStart = i; depth++; } else if (c == '}' && depth > 0) { depth--; if (depth == 0) result.Add(json.Substring(objectStart, i - objectStart + 1)); } else if (c == ']' && depth == 0) break; } return result.ToArray(); } catch { return new string[0]; }
        }

        static string JsonObjectValue(string json, string key)
        {
            try { string marker = "\"" + key + "\""; int idx = json.IndexOf(marker); if (idx < 0) return "{}"; int start = json.IndexOf('{', idx + marker.Length); if (start < 0) return "{}"; int depth = 0; bool quoted = false, escaped = false; for (int i = start; i < json.Length; i++) { char c = json[i]; if (escaped) { escaped = false; continue; } if (c == '\\' && quoted) { escaped = true; continue; } if (c == '"') { quoted = !quoted; continue; } if (quoted) continue; if (c == '{') depth++; else if (c == '}' && --depth == 0) return json.Substring(start, i - start + 1); } } catch { } return "{}";
        }

        static string JsonValue(string json, string key)
        {
            try {
                string searchKey = "\"" + key + "\"";
                int idx = json.IndexOf(searchKey);
                if (idx == -1) return "";
                
                int colonIdx = json.IndexOf(":", idx + searchKey.Length);
                if (colonIdx == -1) return "";
                
                int startPos = colonIdx + 1;
                while (startPos < json.Length && char.IsWhiteSpace(json[startPos])) startPos++;
                
                if (startPos >= json.Length) return "";

                if (json[startPos] == '\"') {
                    int endQuote = json.IndexOf("\"", startPos + 1);
                    if (endQuote == -1) return "";
                    return json.Substring(startPos + 1, endQuote - startPos - 1).Replace("\\n", "\n");
                } else {
                    int endPos = json.IndexOfAny(new char[] { ',', '}', ']' }, startPos);
                    if (endPos == -1) endPos = json.Length;
                    return json.Substring(startPos, endPos - startPos).Trim();
                }
            } catch { return ""; }
        }

        static string ComputeSha256(string input)
        {
            using (var sha = new SHA256Managed())
            {
                byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(input));
                StringBuilder sb = new StringBuilder();
                foreach (byte b in hash) sb.Append(b.ToString("x2"));
                return sb.ToString().ToLower();
            }
        }
    }

    public class LoginForm : Form
    {
        private TextBox txtCard;
        private Button btnLogin, btnBuy, btnContact, btnMode;
        private CheckBox chkSave;
        private Label lblCard, lblNotice;
        private System.Windows.Forms.Timer noticeTimer;
        private string fullNoticeText;
        private int noticePos;
        private bool onlineMode;
        public string CardCode { get; private set; }
        public bool RememberCard { get; private set; }

        public LoginForm(string buyUrl, string contactUrl)
        {
            Text = "授权激活"; Size = new Size(420, 290); FormBorderStyle = FormBorderStyle.FixedDialog; StartPosition = FormStartPosition.CenterScreen; BackColor = Color.WhiteSmoke; MaximizeBox = false;
            lblCard = new Label { Text = "请输入卡密进行激活:", Left = 20, Top = 20, Width = 280, Font = new Font("微软雅黑", 10, FontStyle.Bold) };
            txtCard = new TextBox { Left = 20, Top = 50, Width = 360, Font = new Font("Consolas", 11) };
            chkSave = new CheckBox { Text = "记住卡密 (下次自动登录)", Left = 20, Top = 90, Width = 220, Checked = true, Font = new Font("微软雅黑", 9) };
            btnMode = new Button { Text = "在线激活", Left = 320, Top = 12, Width = 80, Height = 28, FlatStyle = FlatStyle.Flat, Font = new Font("微软雅黑", 8) };
            btnLogin = new Button { Text = "验证启动", Left = 280, Top = 195, Width = 100, Height = 40, FlatStyle = FlatStyle.Flat, BackColor = Color.DeepSkyBlue, ForeColor = Color.White, Font = new Font("微软雅黑", 9, FontStyle.Bold) };
            btnBuy = new Button { Text = "购买卡密", Left = 20, Top = 200, Width = 90, Height = 30, FlatStyle = FlatStyle.Flat, Font = new Font("微软雅黑", 8) };
            btnContact = new Button { Text = "联系客服", Left = 120, Top = 200, Width = 90, Height = 30, FlatStyle = FlatStyle.Flat, Font = new Font("微软雅黑", 8), Visible = !string.IsNullOrEmpty(contactUrl) };

            Panel noticePanel = new Panel { Left = 15, Top = 135, Width = 390, Height = 32, BackColor = Color.FromArgb(255, 243, 205), BorderStyle = BorderStyle.FixedSingle };
            fullNoticeText = ExeProtector.Program.GetNoticeText();
            lblNotice = new Label { Left = 5, Top = 5, Width = 378, Height = 20, Font = new Font("微软雅黑", 9), ForeColor = Color.FromArgb(133, 100, 4), TextAlign = ContentAlignment.MiddleLeft };
            noticePanel.Controls.Add(lblNotice); Controls.Add(noticePanel);
            if (!string.IsNullOrEmpty(fullNoticeText)) {
                lblNotice.Text = "公告：" + fullNoticeText;
                noticeTimer = new System.Windows.Forms.Timer { Interval = 220 };
                noticeTimer.Tick += delegate { string all = "公告：" + fullNoticeText + "        "; noticePos = (noticePos + 1) % all.Length; string loop = all + all; lblNotice.Text = loop.Substring(noticePos, Math.Min(38, loop.Length - noticePos)); };
                noticeTimer.Start();
            } else noticePanel.Visible = false;

            btnMode.Click += delegate { SetOnlineMode(!onlineMode, buyUrl); };
            btnLogin.Click += delegate { CardCode = txtCard.Text.Trim(); RememberCard = chkSave.Checked; if (!string.IsNullOrEmpty(CardCode)) DialogResult = DialogResult.OK; else MessageBox.Show("请输入有效的卡密！"); };
            btnBuy.Click += delegate {
                if (!onlineMode) { if (!string.IsNullOrEmpty(buyUrl)) Process.Start(buyUrl); return; }
                string card = ExeProtector.Program.PurchaseOnline();
                if (!string.IsNullOrEmpty(card)) { CardCode = card; RememberCard = chkSave.Checked; DialogResult = DialogResult.OK; }
            };
            btnContact.Click += delegate { if (!string.IsNullOrEmpty(contactUrl)) Process.Start(contactUrl); };

            Controls.Add(lblCard); Controls.Add(txtCard); Controls.Add(chkSave); Controls.Add(btnMode); Controls.Add(btnLogin); Controls.Add(btnBuy); Controls.Add(btnContact); AcceptButton = btnLogin;
        }

        private void SetOnlineMode(bool online, string buyUrl)
        {
            onlineMode = online; lblCard.Visible = !online; txtCard.Visible = !online; chkSave.Visible = !online; btnLogin.Visible = !online;
            btnMode.Text = online ? "卡密激活" : "在线激活";
            btnBuy.Text = online ? "选择套餐并支付" : "购买卡密"; btnBuy.Width = online ? 130 : 90; btnBuy.Left = online ? 125 : 20;
            btnContact.Left = online ? 265 : 120; btnBuy.Visible = online || !string.IsNullOrEmpty(buyUrl); AcceptButton = online ? null : btnLogin;
        }

        protected override void Dispose(bool disposing) { if (disposing && noticeTimer != null) noticeTimer.Dispose(); base.Dispose(disposing); }
    }
}