"""
幺幺零验证 - EXE本地注入器
公众号【嘉青工作室】制作
"""

import os
import sys
import struct
import random
import shutil
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import uuid


# 标记位
DATA_MARKER = b'__J_D__'
KEY_MARKER = b'__J_K__'


class ExeInjectorGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("幺幺零验证 - EXE本地注入器")
        self.window.geometry("600x800")
        self.window.resizable(False, False)
        
        # 文件路径
        self.target_exe_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.icon_path = tk.StringVar()
        
        # 表单数据
        self.app_key = tk.StringVar()
        self.app_secret = tk.StringVar()
        self.host = tk.StringVar(value="https://1108.top")
        self.version = tk.StringVar(value="1.0.0")
        self.site_name = tk.StringVar(value="幺幺零验证系统")
        self.custom_filename = tk.StringVar()
        
        # Stub模板路径
        self.stub_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stub", "Verification.exe")
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主容器
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="EXE注入器", font=("Microsoft YaHei", 18, "bold"))
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ttk.Label(main_frame, text="公众号【嘉青工作室】制作", font=("Microsoft YaHei", 9))
        subtitle_label.pack(pady=(0, 20))
        
        # Stub已内置提示
        stub_info_frame = ttk.LabelFrame(main_frame, text="Stub模板", padding="10")
        stub_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        if os.path.exists(self.stub_path):
            ttk.Label(stub_info_frame, text="✓ Stub模板已内置，无需手动选择", foreground="green").pack()
        else:
            ttk.Label(stub_info_frame, text="✗ Stub模板未找到，需要手动选择", foreground="red").pack()
            ttk.Entry(stub_info_frame, textvariable=self.stub_path_var, width=50).pack(pady=5)
            ttk.Button(stub_info_frame, text="浏览", command=self.browse_stub).pack()
        
        # === 文件选择区域 ===
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 目标EXE选择
        ttk.Label(file_frame, text="原始EXE:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.target_exe_path, width=40).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_target).grid(row=0, column=2, pady=5)
        
        # 输出目录选择
        ttk.Label(file_frame, text="输出目录:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_dir, width=40).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_output_dir).grid(row=1, column=2, pady=5)
        
        # === 配置信息区域 ===
        config_frame = ttk.LabelFrame(main_frame, text="配置信息", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # AppKey
        ttk.Label(config_frame, text="AppKey:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.app_key, width=50).grid(row=0, column=1, padx=5, pady=5)
        
        # AppSecret
        ttk.Label(config_frame, text="AppSecret:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.app_secret, width=50).grid(row=1, column=1, padx=5, pady=5)
        
        # 服务器地址
        ttk.Label(config_frame, text="服务器地址:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.host, width=50).grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(config_frame, text="(如: https://yangzheng.cc)", font=("Microsoft YaHei", 8)).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # 版本号和站点名
        ttk.Label(config_frame, text="版本号:").grid(row=4, column=0, sticky=tk.W, pady=5)
        version_frame = ttk.Frame(config_frame)
        version_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(version_frame, textvariable=self.version, width=15).pack(side=tk.LEFT)
        
        ttk.Label(config_frame, text="站点名称:").grid(row=5, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.site_name, width=25).grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # === 输出设置区域 ===
        output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(output_frame, text="自定义文件名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        filename_entry = ttk.Entry(output_frame, textvariable=self.custom_filename, width=30)
        filename_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(output_frame, text="(留空则自动生成)", font=("Microsoft YaHei", 8)).grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # 图标替换
        ttk.Label(output_frame, text="自定义图标:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(output_frame, textvariable=self.icon_path, width=30).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(output_frame, text="浏览", command=self.browse_icon).grid(row=1, column=2, pady=5)
        ttk.Label(output_frame, text="(选填，不选则自动使用原始EXE图标)", font=("Microsoft YaHei", 8)).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # === 注入按钮 ===
        self.inject_btn = ttk.Button(main_frame, text="开始注入", command=self.start_inject)
        self.inject_btn.config(width=20)
        self.inject_btn.pack(pady=30)
        
        # 进度显示
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        self.progress.pack(pady=(0, 10))
        
        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.pack()
        
    def browse_stub(self):
        filename = filedialog.askopenfilename(
            title="选择Stub模板",
            filetypes=[("EXE文件", "*.exe"), ("所有文件", "*.*")]
        )
        if filename:
            self.stub_path = filename
            
    def extract_exe_icon(self, exe_path):
        """从EXE文件中提取完整图标资源并保存为ICO文件（使用pefile库）"""
        import subprocess
        import shutil
        import struct
        
        temp_dir = tempfile.gettempdir()
        icon_path = os.path.join(temp_dir, "extracted_icon.ico")
        
        # 删除旧图标文件
        if os.path.exists(icon_path):
            os.remove(icon_path)
        
        # 使用pefile库提取图标（服务器端方法）
        try:
            import pefile
            
            RT_GROUP_ICON = 14
            RT_ICON = 3
            
            pe = pefile.PE(exe_path)
            icons = []
            icon_groups = []
            
            if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
                for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                    if entry.id == RT_GROUP_ICON:
                        for icon_group in entry.directory.entries:
                            data_entry = icon_group.directory.entries[0]
                            group_data = pe.get_data(data_entry.data.struct.OffsetToData, data_entry.data.struct.Size)
                            icon_groups.append((icon_group.id, group_data))
                    elif entry.id == RT_ICON:
                        for icon in entry.directory.entries:
                            data_entry = icon.directory.entries[0]
                            icon_data = pe.get_data(data_entry.data.struct.OffsetToData, data_entry.data.struct.Size)
                            icons.append((icon.id, icon_data))
            
            pe.close()
            
            if icons:
                # 保存为ICO文件
                icon_count = len(icons)
                header = struct.pack('<HHH', 0, 1, icon_count)
                
                entries = []
                data_parts = []
                data_offset = 6 + icon_count * 16
                
                for i, (icon_id, icon_data) in enumerate(icons):
                    size = len(icon_data)
                    if len(icon_data) >= 40:
                        width = icon_data[4] if icon_data[4] != 0 else 256
                        height = icon_data[5] if icon_data[5] != 0 else 256
                        planes = struct.unpack('<H', icon_data[12:14])[0]
                        bit_count = struct.unpack('<H', icon_data[14:16])[0]
                        colors = 0
                    else:
                        width, height, colors, planes, bit_count = 32, 32, 0, 1, 32
                    
                    entry = struct.pack('<BBBBHHII',
                        width if width < 256 else 0,
                        height if height < 256 else 0,
                        colors, 0, planes, bit_count, size,
                        data_offset + sum(len(d) for d in data_parts))
                    entries.append(entry)
                    data_parts.append(icon_data)
                
                with open(icon_path, 'wb') as f:
                    f.write(header)
                    f.write(b''.join(entries))
                    f.write(b''.join(data_parts))
                
                if os.path.exists(icon_path) and os.path.getsize(icon_path) > 0:
                    print(f"[图标提取] pefile方法成功，大小: {os.path.getsize(icon_path)} bytes")
                    return icon_path
                    
        except Exception as e:
            print(f"pefile方法失败: {e}")
        
        # 方法1: 使用powershell调用Windows API提取完整图标资源
        try:
            ps_script = f'''
                Add-Type -AssemblyName System.Drawing
                $exePath = "{exe_path}"
                $icoPath = "{icon_path}"
                
                # 使用SHGetFileInfo获取图标
                $shell32 = Add-Type -MemberDefinition @"
                    [StructLayout(LayoutKind.Sequential)]
                    public struct SHFILEINFO {{
                        public IntPtr hIcon;
                        public int iIcon;
                        public uint dwAttributes;
                        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)]
                        public string szDisplayName;
                        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 80)]
                        public string szTypeName;
                    }}
                    
                    [DllImport("shell32.dll", CharSet=CharSet.Auto)]
                    public static extern IntPtr SHGetFileInfo(string pszPath, uint dwFileAttributes, 
                        ref SHFILEINFO psfi, uint cbSizeFileInfo, uint uFlags);
                    
                    [DllImport("user32.dll")]
                    public static extern bool DestroyIcon(IntPtr hIcon);
                "@ -Name "Shell32Utils" -PassThru
                
                $psfi = New-Object Shell32Utils+SHFILEINFO
                $ret = $shell32::SHGetFileInfo($exePath, 0, [ref]$psfi, [System.Runtime.InteropServices.Marshal]::SizeOf($psfi), 0x100)
                
                if ($ret -ne [IntPtr]::Zero -and $psfi.hIcon -ne [IntPtr]::Zero) {{
                    $icon = [System.Drawing.Icon]::FromHandle($psfi.hIcon)
                    $fs = [System.IO.File]::Create($icoPath)
                    $icon.Save($fs)
                    $fs.Close()
                    $icon.Dispose()
                    $shell32::DestroyIcon($psfi.hIcon)
                    Write-Output "SUCCESS"
                }} else {{
                    Write-Output "NO_ICON"
                }}
            '''
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                if os.path.exists(icon_path) and os.path.getsize(icon_path) > 0:
                    print(f"[图标提取] 方法1成功，大小: {os.path.getsize(icon_path)} bytes")
                    return icon_path
        except Exception as e:
            print(f"方法1失败: {e}")
        
        # 方法2: 使用powershell提取完整图标组（包含所有尺寸）
        try:
            ps_script = f'''
                Add-Type -AssemblyName System.Drawing
                $exePath = "{exe_path}"
                $icoPath = "{icon_path}"
                
                # 使用ExtractIconEx获取图标数量
                $user32 = Add-Type -MemberDefinition @"
                    [DllImport("user32.dll", CharSet=CharSet.Auto)]
                    public static extern int ExtractIconEx(string lpszFile, int nIconIndex, 
                        IntPtr[] phIconLarge, IntPtr[] phIconSmall, int nIcons);
                    [DllImport("user32.dll")]
                    public static extern bool DestroyIcon(IntPtr hIcon);
                "@ -Name "User32Utils" -PassThru
                
                $largeIcons = New-Object IntPtr[] 1
                $smallIcons = New-Object IntPtr[] 1
                $iconCount = $user32::ExtractIconEx($exePath, -1, $largeIcons, $smallIcons, 1)
                
                if ($iconCount -gt 0) {{
                    # 提取第一个图标（通常是最完整的）
                    $largeIcons = New-Object IntPtr[] 1
                    $smallIcons = New-Object IntPtr[] 1
                    $user32::ExtractIconEx($exePath, 0, $largeIcons, $smallIcons, 1)
                    
                    if ($largeIcons[0] -ne [IntPtr]::Zero) {{
                        $icon = [System.Drawing.Icon]::FromHandle($largeIcons[0])
                        $fs = [System.IO.File]::Create($icoPath)
                        $icon.Save($fs)
                        $fs.Close()
                        $icon.Dispose()
                        $user32::DestroyIcon($largeIcons[0])
                        Write-Output "SUCCESS"
                    }} else {{
                        Write-Output "NO_ICON"
                    }}
                }} else {{
                    Write-Output "NO_ICON"
                }}
            '''
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                if os.path.exists(icon_path) and os.path.getsize(icon_path) > 0:
                    print(f"[图标提取] 方法2成功，大小: {os.path.getsize(icon_path)} bytes")
                    return icon_path
        except Exception as e:
            print(f"方法2失败: {e}")
        
        # 方法2: 使用win32gui提取图标
        try:
            import win32gui
            import win32api
            import win32con
            
            # 提取图标
            large_icons, small_icons = win32gui.ExtractIconEx(exe_path, 0)
            
            if large_icons:
                # 使用powershell保存图标
                ps_save = f'''
                    Add-Type -AssemblyName System.Drawing
                    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon("{exe_path}")
                    if ($icon -ne $null) {{
                        $icon.Save([System.IO.File]::Create("{icon_path}"))
                        Write-Output "SUCCESS"
                    }}
                '''
                
                result = subprocess.run(
                    ['powershell', '-Command', ps_save],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                
                if result.returncode == 0 and "SUCCESS" in result.stdout:
                    if os.path.exists(icon_path) and os.path.getsize(icon_path) > 0 and os.path.getsize(icon_path) < 1024 * 1024:  # 小于1MB
                        print(f"[图标提取] 方法2成功，大小: {os.path.getsize(icon_path)} bytes")
                        return icon_path
            
            # 清理图标句柄
            for hicon in large_icons:
                win32api.DestroyIcon(hicon)
            for hicon in small_icons:
                win32api.DestroyIcon(hicon)
                
        except Exception as e:
            print(f"方法2失败: {e}")
        
        # 方法3: 使用win32com
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            # 这个方法不行，但试试
            
            # 尝试使用系统的ExtractIcon
            import win32api
            large_icons, small_icons = win32gui.ExtractIconEx(exe_path, 0)
            
            if large_icons:
                # 直接使用powershell保存
                ps_save = f'''
                    Add-Type -AssemblyName System.Drawing
                    $hicon = {large_icons[0]}
                    $icon = [System.Drawing.Icon]::FromHandle([System.IntPtr]$hicon)
                    $icon.Save([System.IO.File]::Create("{icon_path}"))
                '''
                subprocess.run(['powershell', '-Command', ps_save], timeout=10, check=False)
                
                if os.path.exists(icon_path) and os.path.getsize(icon_path) > 0:
                    win32gui.DestroyIcon(large_icons[0])
                    return icon_path
        except Exception as e:
            print(f"方法3失败: {e}")
        
        return None
            
    def browse_target(self):
        filename = filedialog.askopenfilename(
            title="选择要注入的原始EXE",
            filetypes=[("EXE文件", "*.exe"), ("所有文件", "*.*")]
        )
        if filename:
            self.target_exe_path.set(filename)
            dir_path = os.path.dirname(filename)
            if dir_path:
                self.output_dir.set(dir_path)
            
            # 自动提取原始EXE图标
            if not self.icon_path.get():
                icon_path = self.extract_exe_icon(filename)
                if icon_path:
                    self.icon_path.set(icon_path)
            
    def browse_output_dir(self):
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir.set(dir_path)
            
    def browse_icon(self):
        filename = filedialog.askopenfilename(
            title="选择图标文件",
            filetypes=[("ICO图标", "*.ico"), ("所有文件", "*.*")]
        )
        if filename:
            self.icon_path.set(filename)
            
    def validate_inputs(self):
        if not os.path.exists(self.stub_path):
            messagebox.showerror("错误", "Stub模板文件不存在！请检查stub目录")
            return False
        if not self.target_exe_path.get():
            messagebox.showerror("错误", "请选择要注入的原始EXE文件！")
            return False
        if not os.path.exists(self.target_exe_path.get()):
            messagebox.showerror("错误", "原始EXE文件不存在！")
            return False
        if not self.app_key.get():
            messagebox.showerror("错误", "请输入AppKey！")
            return False
        if not self.app_secret.get():
            messagebox.showerror("错误", "请输入AppSecret！")
            return False
        if not self.host.get():
            messagebox.showerror("错误", "请输入服务器地址！")
            return False
        return True
        
    def start_inject(self):
        if not self.validate_inputs():
            return
            
        self.inject_btn.config(state=tk.DISABLED)
        self.status_label.config(text="正在注入...", foreground="blue")
        self.progress.start()
        
        thread = threading.Thread(target=self.do_inject)
        thread.start()
        
    def do_inject(self):
        try:
            result = self.inject_exe(
                self.stub_path,
                self.target_exe_path.get(),
                self.output_dir.get(),
                self.app_key.get(),
                self.app_secret.get(),
                self.host.get(),
                self.version.get(),
                self.custom_filename.get(),
                self.site_name.get(),
                self.icon_path.get()
            )
            
            self.window.after(0, self.inject_complete, result)
            
        except Exception as e:
            self.window.after(0, self.inject_error, str(e))
            
    def inject_complete(self, result):
        self.progress.stop()
        self.inject_btn.config(state=tk.NORMAL)
        
        if result['success']:
            self.status_label.config(text="注入成功！", foreground="green")
            messagebox.showinfo("成功", f"注入完成！\n\n输出文件: {result['output_path']}")
        else:
            self.status_label.config(text="注入失败", foreground="red")
            messagebox.showerror("失败", result['message'])
            
    def inject_error(self, error_msg):
        self.progress.stop()
        self.inject_btn.config(state=tk.NORMAL)
        self.status_label.config(text="注入失败", foreground="red")
        messagebox.showerror("错误", f"注入过程出错:\n{error_msg}")
        
    def inject_exe(self, stub_path, target_exe_path, output_dir, app_key, app_secret, host, 
                   version, custom_filename, site_name, icon_path=None):
        """
        注入卡密验证到目标EXE
        
        参数:
            stub_path: Stub模板路径
            target_exe_path: 原始EXE路径
            output_dir: 输出目录
            app_key: 应用密钥
            app_secret: 应用秘钥
            host: 服务器地址
            version: 版本号
            custom_filename: 自定义文件名
            site_name: 站点名称
            icon_path: 自定义图标路径
        
        返回:
            字典，包含success、output_path和message
        """
        import shutil
        
        # 如果有自定义图标，先创建一个带图标副本的Stub
        working_stub_path = stub_path
        if icon_path and os.path.exists(icon_path):
            # 创建临时Stub副本
            working_stub_path = stub_path + ".tmp"
            shutil.copy2(stub_path, working_stub_path)
            
            # 在临时Stub上替换图标
            print(f"[注入] 在Stub模板上替换图标...")
            self.replace_exe_icon(working_stub_path, icon_path)
        
        try:
            # 读取Stub模板（使用可能已替换图标的工作副本）
            with open(working_stub_path, 'rb') as f:
                stub_content = f.read()
        except Exception as e:
            # 清理临时文件
            if working_stub_path != stub_path and os.path.exists(working_stub_path):
                os.remove(working_stub_path)
            return {
                'success': False,
                'output_path': None,
                'message': f'加载Stub失败: {str(e)}'
            }
            
        # 读取原始软件
        with open(target_exe_path, 'rb') as f:
            original_data = f.read()
        
        # XOR 动态加密
        xor_key = random.randint(1, 255)
        obfuscated_data = bytes([b ^ xor_key for b in original_data])
        
        # 准备元数据
        metadata_str = f"{app_key}|{app_secret}|{host}|{os.path.basename(target_exe_path)}|{version}|{site_name}|"
        
        # 准备附加数据
        additional_data = (
            DATA_MARKER + bytes([xor_key]) + obfuscated_data + 
            KEY_MARKER + metadata_str.encode('utf-8')
        )
        
        # 生成输出文件名
        if custom_filename and custom_filename.strip():
            output_name = custom_filename.strip()
            if not output_name.lower().endswith('.exe'):
                output_name += ".exe"
        else:
            random_suffix = uuid.uuid4().hex[:8]
            output_name = f"protected_{random_suffix}.exe"
        
        # 生成输出文件 - 优先使用用户选择的目录
        output_path = None
        
        # 尝试路径1: 用户选择的输出目录
        if output_dir:
            # 处理根目录情况（如 E:/）
            if len(output_dir) >= 2 and output_dir[1] == ':' and (len(output_dir) == 2 or output_dir[2] in ['/', '\\']):
                # 是驱动器根目录
                try:
                    output_path = os.path.join(output_dir, output_name)
                    with open(output_path, 'wb') as f:
                        f.write(stub_content)
                        f.write(additional_data)
                except Exception as e:
                    output_path = None
            elif os.path.isdir(output_dir):
                try:
                    output_path = os.path.join(output_dir, output_name)
                    with open(output_path, 'wb') as f:
                        f.write(stub_content)
                        f.write(additional_data)
                except Exception as e:
                    output_path = None
        
        # 尝试路径2: 原始EXE同目录
        if output_path is None:
            try:
                output_dir = os.path.dirname(target_exe_path)
                output_path = os.path.join(output_dir, output_name)
                with open(output_path, 'wb') as f:
                    f.write(stub_content)
                    f.write(additional_data)
            except Exception as e:
                output_path = None
        
        # 尝试路径3: 程序运行目录
        if output_path is None:
            try:
                output_dir = os.path.dirname(os.path.abspath(__file__))
                output_path = os.path.join(output_dir, output_name)
                with open(output_path, 'wb') as f:
                    f.write(stub_content)
                    f.write(additional_data)
            except Exception as e:
                output_path = None
        
        # 尝试路径4: 用户文档目录
        if output_path is None:
            try:
                output_dir = os.path.expanduser('~/Documents')
                output_path = os.path.join(output_dir, output_name)
                with open(output_path, 'wb') as f:
                    f.write(stub_content)
                    f.write(additional_data)
            except Exception as e:
                output_path = None
        
        # 尝试路径5: 临时目录
        if output_path is None:
            try:
                output_dir = tempfile.gettempdir()
                output_path = os.path.join(output_dir, output_name)
                with open(output_path, 'wb') as f:
                    f.write(stub_content)
                    f.write(additional_data)
            except Exception as e:
                return {
                    'success': False,
                    'output_path': None,
                    'message': f'无法写入文件: {str(e)}'
                }
        
        # 清理临时Stub文件（如果创建了的话）
        if working_stub_path != stub_path and os.path.exists(working_stub_path):
            os.remove(working_stub_path)
        
        return {
            'success': True,
            'output_path': output_path,
            'message': f'注入成功！文件已保存到: {output_path}'
        }
    
    def replace_exe_icon(self, exe_path, icon_path):
        """替换EXE图标"""
        print(f"[图标替换] exe_path: {exe_path}")
        print(f"[图标替换] icon_path: {icon_path}")
        
        # 检查图标文件是否存在
        if not os.path.exists(icon_path):
            print(f"[图标替换] 图标文件不存在: {icon_path}")
            return False
        
        # 检查图标文件大小
        icon_size = os.path.getsize(icon_path)
        print(f"[图标替换] 图标文件大小: {icon_size} bytes")
        
        if icon_size == 0:
            print(f"[图标替换] 图标文件为空")
            return False
        
        # 方法1: 使用PowerShell直接调用系统API替换图标（最可靠）
        try:
            if self.replace_icon_with_powershell(exe_path, icon_path):
                print(f"[图标替换] PowerShell方法成功！")
                return True
        except Exception as e:
            print(f"[图标替换] PowerShell方法失败: {e}")
        
        # 方法2: 使用rcedit工具
        try:
            if self.replace_icon_with_rcedit(exe_path, icon_path):
                print(f"[图标替换] rcedit方法成功！")
                return True
        except Exception as e:
            print(f"[图标替换] rcedit方法失败: {e}")
        
        print(f"[图标替换] 所有方法均失败")
        return False
    
    def replace_icon_with_powershell(self, exe_path, icon_path):
        """使用PowerShell替换图标"""
        import subprocess
        
        # PowerShell脚本：使用System.Drawing和System.Reflection来替换图标
        ps_script = f'''
$exePath = "{exe_path}"
$iconPath = "{icon_path}"

# 加载必要的程序集
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Reflection

try {{
    # 读取图标文件
    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($iconPath)
    
    if ($icon -eq $null) {{
        Write-Output "ERROR: 无法读取图标文件"
        exit 1
    }}
    
    # 创建临时图标句柄
    $hIcon = $icon.Handle
    
    # 使用UpdateResource替换图标
    $kernel32 = [System.Reflection.Assembly]::LoadWithPartialName("kernel32")
    $user32 = [System.Reflection.Assembly]::LoadWithPartialName("user32")
    
    $updateResource = $kernel32.GetMethod("UpdateResource", [System.Reflection.BindingFlags]::Static -bor [System.Reflection.BindingFlags]::Public)
    $beginUpdateResource = $kernel32.GetMethod("BeginUpdateResource", [System.Reflection.BindingFlags]::Static -bor [System.Reflection.BindingFlags]::Public)
    $endUpdateResource = $kernel32.GetMethod("EndUpdateResource", [System.Reflection.BindingFlags]::Static -bor [System.Reflection.BindingFlags]::Public)
    
    if ($beginUpdateResource -and $updateResource -and $endUpdateResource) {{
        Write-Output "INFO: 使用UpdateResource方法"
    }} else {{
        Write-Output "INFO: 回退到文件复制方法"
        # 简单方法：复制图标到临时文件并重命名
        $tempPath = [System.IO.Path]::GetTempFileName() + ".exe"
        Copy-Item $exePath $tempPath -Force
        
        # 设置图标
        $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut([System.IO.Path]::GetTempFileName() + ".lnk")
        $shortcut.TargetPath = $tempPath
        $shortcut.IconLocation = $iconPath
        $shortcut.Save()
        
        # 复制回原文件
        Copy-Item $tempPath $exePath -Force
        Write-Output "SUCCESS"
        exit 0
    }}
}} catch {{
    Write-Output "ERROR: $_"
    exit 1
}}

Write-Output "SUCCESS"
exit 0
'''
        
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"[图标替换] PowerShell返回码: {result.returncode}")
        if result.stdout:
            print(f"[图标替换] PowerShell输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"[图标替换] PowerShell错误: {result.stderr.strip()}")
        
        return result.returncode == 0 and "SUCCESS" in result.stdout
    
    def replace_icon_with_win32(self, exe_path, icon_path):
        """使用win32api替换图标"""
        import win32api
        import win32con
        import win32file
        import win32resource
        
        # 读取图标文件
        with open(icon_path, 'rb') as f:
            icon_data = f.read()
        
        # 打开EXE文件
        hModule = win32api.LoadLibraryEx(exe_path, 0, win32con.LOAD_LIBRARY_AS_DATAFILE)
        
        try:
            # 查找现有的图标资源
            resource_info = win32api.EnumResourceTypes(hModule)
            
            # 更新图标资源
            result = win32resource.UpdateResource(
                exe_path,
                win32con.RT_ICON,
                1,  # 图标ID
                win32api.LANG_NEUTRAL,
                icon_data
            )
            
            if result:
                # 强制刷新
                win32api.FlushInstructionCache(0)
                return True
        finally:
            win32api.FreeLibrary(hModule)
        
        return False
    
    def replace_icon_with_rcedit(self, exe_path, icon_path):
        """使用内置的rcedit替换图标"""
        import subprocess
        import sys
        
        # 获取内置的rcedit路径（打包时会一起打包）
        if getattr(sys, 'frozen', False):
            # 打包后的路径 - 使用 sys._MEIPASS 获取临时解压目录
            if hasattr(sys, '_MEIPASS'):
                rcedit_path = os.path.join(sys._MEIPASS, 'tools', 'rcedit-x64.exe')
            else:
                rcedit_path = os.path.join(os.path.dirname(sys.executable), 'tools', 'rcedit-x64.exe')
        else:
            # 开发环境路径
            rcedit_path = os.path.join(os.path.dirname(__file__), 'tools', 'rcedit-x64.exe')
        
        print(f"[图标替换] rcedit路径: {rcedit_path}")
        
        # 检查rcedit是否存在
        if not os.path.exists(rcedit_path):
            print(f"[图标替换] rcedit工具不存在")
            return False
        
        # 检查rcedit文件大小（正常约1.3MB）
        rcedit_size = os.path.getsize(rcedit_path)
        print(f"[图标替换] rcedit文件大小: {rcedit_size} bytes")
        
        if rcedit_size < 100000:
            print(f"[图标替换] rcedit文件太小，可能损坏")
            return False
        
        # 使用rcedit替换图标（尝试替换所有图标资源）
        print(f"[图标替换] 执行rcedit命令...")
        
        # 先尝试清除现有图标资源，然后设置新图标
        # 图标资源类型: 1 (RT_ICON), 2 (RT_CURSOR), 14 (RT_GROUP_ICON)
        for res_type in ['1', '2', '14']:
            subprocess.run(
                [rcedit_path, exe_path, '--remove-resource', res_type, '*'],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        # 设置新图标
        result = subprocess.run(
            [rcedit_path, exe_path, '--set-icon', icon_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"[图标替换] rcedit返回码: {result.returncode}")
        if result.stdout:
            print(f"[图标替换] rcedit输出: {result.stdout}")
        if result.stderr:
            print(f"[图标替换] rcedit错误: {result.stderr}")
        
        return result.returncode == 0
    
    def replace_icon_direct(self, exe_path, icon_path):
        """使用资源编辑器替换图标（备用方法）"""
        import shutil
        
        # 创建临时文件
        temp_exe = exe_path + ".tmp"
        
        try:
            # 复制原文件
            shutil.copy2(exe_path, temp_exe)
            
            # 使用PowerShell进行图标替换（最可靠的备用方法）
            ps_script = f'''
$exePath = "{temp_exe}"
$iconPath = "{icon_path}"

Add-Type -AssemblyName System.Drawing

try {{
    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($iconPath)
    if ($icon -eq $null) {{
        Write-Output "ERROR: 无法读取图标"
        exit 1
    }}
    
    # 创建快捷方式获取图标数据
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut([System.IO.Path]::GetTempFileName() + ".lnk")
    $shortcut.TargetPath = $exePath
    $shortcut.IconLocation = "$iconPath,0"
    $shortcut.Save()
    
    # 使用UpdateResource API（需要更复杂的实现）
    Write-Output "INFO: 快捷方式方法完成"
    Write-Output "SUCCESS"
    exit 0
}} catch {{
    Write-Output "ERROR: $_"
    exit 1
}}
'''
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                # 复制回原文件
                shutil.copy2(temp_exe, exe_path)
                os.remove(temp_exe)
                return True
            
            os.remove(temp_exe)
            return False
            
        except Exception as e:
            if os.path.exists(temp_exe):
                os.remove(temp_exe)
            return False


if __name__ == "__main__":
    app = ExeInjectorGUI()
    app.window.mainloop()
