# ReactOS Application Manager - Python/PySide6 Rewrite

Python 重写版本 of the ReactOS Application Manager (RAPPS).

## 项目结构

```
python/
├── rapps/
│   ├── __init__.py          # Package init
│   ├── main.py              # 入口点 (Entry point)
│   ├── config.py            # 配置常量 (Configuration constants)
│   ├── config_parser.py     # INI 配置解析器 (Multi-language INI parser)
│   ├── app_info.py          # 应用信息类 (App info data classes)
│   ├── database.py          # 数据库管理 (Database management)
│   ├── registry.py          # 注册表操作 (Windows registry operations)
│   ├── downloader.py        # 下载管理器 (Download manager)
│   ├── installer.py         # 安装/卸载 (Install/Uninstall)
│   ├── settings.py          # 设置管理 (Settings management)
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py   # 主窗口 (Main window)
│       ├── category_tree.py # 分类树 (Category tree)
│       ├── app_list.py      # 应用列表 (Application list)
│       ├── info_panel.py    # 信息面板 (Info panel)
│       ├── download_dialog.py # 下载对话框 (Download dialog)
│       └── settings_dialog.py # 设置对话框 (Settings dialog)
├── requirements.txt         # Python 依赖
└── README.md
```

## 功能对照

| 原始 C++ 文件 | Python 模块 | 功能 |
|-------------|-----------|------|
| winmain.cpp | main.py | 程序入口、命令行解析 |
| gui.cpp | ui/main_window.py | 主窗口、菜单、布局 |
| appdb.cpp | database.py | 数据库管理、文件枚举 |
| appinfo.cpp | app_info.py | 应用信息类 |
| configparser.cpp | config_parser.py | INI 配置解析 |
| asyncinet.cpp | downloader.py | 异步下载 |
| cabinet.cpp | database.py | CAB 文件解压 |
| geninst.cpp | installer.py | 生成安装器 |
| loaddlg.cpp | ui/download_dialog.py | 下载进度对话框 |
| settings.cpp | settings.py | 设置管理 |
| settingsdlg.cpp | ui/settings_dialog.py | 设置对话框 |
| unattended.cpp | main.py | 命令行处理 |
| misc.cpp | registry.py | 注册表操作、工具函数 |

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
# 图形界面模式
python -m rapps.main

# 命令行模式
python -m rapps.main /help
python -m rapps.main /find "browser"
python -m rapps.main /info "7zip"
python -m rapps.main /install "7zip"
python -m rapps.main /uninstall "Firefox"
python -m rapps.main /appwiz
```

## 主要变化

1. **GUI 框架**: Win32/ATL → PySide6 (Qt6)
2. **配置存储**: Windows 注册表 → JSON 文件 (%APPDATA%/RAPPS/settings.json)
3. **下载**: WinINet → urllib (Python 标准库)
4. **CAB 解压**: cabinet.dll FDI API → tar/PowerShell 回退
5. **注册表**: ATL CRegKey → winreg (Python 标准库)
6. **多线程**: Windows API → threading 模块
7. **INI 解析**: 自定义 CConfigParser → configparser + 自定义多语言支持

## 依赖

- Python 3.9+
- PySide6 >= 6.5.0
- Windows 平台 (使用 winreg 模块)

## 许可

GPL-2.0-or-later (与原始 ReactOS 项目保持一致)
