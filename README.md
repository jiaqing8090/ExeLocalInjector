# 幺幺零验证 - EXE本地注入器

基于 Stub 模卡的 EXE 文件卡密验证注入工具。

## 功能

- 选择原始 EXE 文件，注入卡密验证逻辑
- 支持自定义服务器地址、AppKey、AppSecret
- 自动提取并保留原始 EXE 图标
- 支持自定义图标替换
- XOR 动态加密原始程序数据
- 生成带验证的独立 EXE 文件

## 目录结构

```
.
├── ExeLocalInjector.py    # 主程序（Python + tkinter GUI）
├── stub/
│   └── Verification.exe   # Stub 模板（注入验证逻辑的外壳）
└── tools/
    └── rcedit-x64.exe     # EXE 图标编辑工具
```

## 使用方式

```bash
pip install pefile pywin32
python ExeLocalInjector.py
```

1. 选择原始 EXE 文件
2. 填写 AppKey / AppSecret / 服务器地址
3. 点击「开始注入」
4. 输出生成带卡密验证的 EXE

## 注入原理

1. 读取 Stub 模板作为外壳
2. 将原始 EXE 数据进行 XOR 加密
3. 将加密数据 + 元数据（AppKey/AppSecret/服务器地址等）追加到 Stub 尾部
4. Stub 启动时先连接验证服务器校验卡密，通过后解密并运行原始程序

## 注意事项

- 仅用于自己软件的保护，请勿用于非法用途
- Stub 模板和 rcedit 为二进制文件，已包含在仓库中