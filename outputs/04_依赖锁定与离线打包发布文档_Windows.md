# 依赖锁定与离线打包发布文档：Windows V1

版本：V1.0  
日期：2026-06-07  
目标：目标电脑没有 Python、pip、qpdf、PyMuPDF，也能运行

## 1. 版本锁定

截至 2026-06-07，建议锁定：

| 类型 | 名称 | 版本 | 用途 | 运行时是否打包 |
|---|---:|---:|---|---|
| Python | CPython x64 | 3.12.10 | 构建和开发解释器 | PyInstaller 会打入 exe 目录 |
| PDF 核心 | PyMuPDF | 1.27.2.3 | 脱敏、水印、渲染、压平 | 是 |
| PDF 安全 | pikepdf | 10.7.3 | 加密、权限、元数据收尾 | 是 |
| 图像适配 | Pillow | 12.2.0 | Tkinter 页面预览 | 是 |
| 打包 | PyInstaller | 6.20.0 | 生成便携版 | 构建机使用 |
| 测试 | pytest | 9.0.3 | 自动测试 | 构建机使用 |
| 命令行后备 | qpdf | 12.3.2 msvc64 | 权限加密/验证后备 | 是，作为资源打包 |
| 安装包 | Inno Setup | 6.7.3 | 生成安装版 | 构建机使用 |

版本来源：

- PyMuPDF PyPI：`https://pypi.org/project/PyMuPDF/`
- pikepdf PyPI：`https://pypi.org/project/pikepdf/`
- Pillow PyPI：`https://pypi.org/project/pillow/`
- PyInstaller PyPI：`https://pypi.org/project/PyInstaller/`
- qpdf GitHub Releases：`https://github.com/qpdf/qpdf/releases`
- Python Windows Releases：`https://www.python.org/downloads/windows/`
- Inno Setup Downloads：`https://jrsoftware.org/isdl.php`

## 2. 依赖文件

`requirements.lock.txt`：

```text
PyMuPDF==1.27.2.3
pikepdf==10.7.3
Pillow==12.2.0
```

`requirements-dev.lock.txt`：

```text
pyinstaller==6.20.0
pytest==9.0.3
```

如果后续实际 pip 解析出 pikepdf 的间接依赖，例如 `Deprecated`、`lxml` 或其他 wheel，需要用 `pip freeze` 生成完整锁定文件：

```powershell
.\.venv\Scripts\pip.exe freeze > requirements.full.lock.txt
```

正式构建以 `requirements.full.lock.txt` 为准。

## 3. Wheelhouse 离线依赖包

首次联网构建机执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe download -r requirements.lock.txt -d vendor\wheelhouse
.\.venv\Scripts\pip.exe download -r requirements-dev.lock.txt -d vendor\wheelhouse
```

离线安装验证：

```powershell
py -3.12 -m venv .venv-offline-test
.\.venv-offline-test\Scripts\pip.exe install --no-index --find-links vendor\wheelhouse -r requirements.lock.txt
.\.venv-offline-test\Scripts\pip.exe install --no-index --find-links vendor\wheelhouse -r requirements-dev.lock.txt
```

## 4. qpdf 二进制依赖

下载：

```text
qpdf-12.3.2-msvc64.zip
```

放置：

```text
vendor/qpdf-12.3.2-msvc64/
resources/qpdf/
```

运行时路径建议：

```text
resources/qpdf/bin/qpdf.exe
```

PyInstaller 打包时必须把 `resources/qpdf` 加入数据文件。

## 5. 便携版方案

便携版目录：

```text
LocalPDFGuard-1.0.0-portable/
  LocalPDFGuard.exe
  _internal/
  resources/
    qpdf/
      bin/
        qpdf.exe
  README.txt
  LICENSES/
```

特点：

- 解压即用。
- 不写注册表。
- 不需要管理员权限。
- 输出和配置默认写用户目录：

```text
%LOCALAPPDATA%\LocalPDFGuard\
```

构建命令：

```powershell
.\.venv\Scripts\pyinstaller.exe packaging\pyinstaller\LocalPDFGuard.spec --clean --noconfirm
Compress-Archive -Path dist\LocalPDFGuard\* -DestinationPath dist\LocalPDFGuard-1.0.0-portable-win64.zip
```

PyInstaller spec 要点：

- `console=False`
- `onedir`
- 包含 `resources/qpdf`
- 包含图标
- 包含 Tcl/Tk 运行文件
- 明确 hiddenimports：`pymupdf`, `pikepdf`, `PIL._tkinter_finder`

## 6. 安装版方案

安装版使用 Inno Setup 6.7.3。

安装包输入：便携版目录。  
安装包输出：

```text
LocalPDFGuard-1.0.0-setup-win64.exe
```

安装目录：

```text
{autopf}\LocalPDFGuard
```

创建：

- 桌面快捷方式，可选。
- 开始菜单快捷方式。
- 卸载项。

不做：

- 不安装 Python 到系统。
- 不修改系统 PATH。
- 不注册 PDF 默认打开方式。

Inno Setup 脚本要点：

```ini
[Setup]
AppName=Local PDF Guard
AppVersion=1.0.0
DefaultDirName={autopf}\LocalPDFGuard
DefaultGroupName=Local PDF Guard
OutputBaseFilename=LocalPDFGuard-1.0.0-setup-win64
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "..\..\dist\LocalPDFGuard\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Local PDF Guard"; Filename: "{app}\LocalPDFGuard.exe"
Name: "{commondesktop}\Local PDF Guard"; Filename: "{app}\LocalPDFGuard.exe"; Tasks: desktopicon
```

## 7. 构建流水线

```mermaid
flowchart LR
    A["联网构建机"] --> B["下载 wheelhouse"]
    B --> C["创建 venv"]
    C --> D["离线安装依赖验证"]
    D --> E["运行测试"]
    E --> F["PyInstaller onedir"]
    F --> G["便携版 zip"]
    F --> H["Inno Setup"]
    H --> I["安装版 exe"]
    G --> J["干净机器验收"]
    I --> J
```

## 8. 干净机器验收

准备一台没有以下内容的 Windows 机器或虚拟机：

- 没有 Python。
- 没有 pip。
- 没有 PyMuPDF。
- 没有 qpdf。
- 没有 Inno Setup。

验收：

1. 便携版解压后双击运行。
2. 安装版双击安装后运行。
3. 打开样例 PDF。
4. 自动识别。
5. 手动框选。
6. 输出 PDF。
7. 检查输出 PDF 存在水印。
8. 检查复制/修改限制。
9. 检查敏感文本不可提取。
10. 删除安装版，确认卸载正常。

## 9. 发布物清单

最终 `dist` 应包含：

```text
LocalPDFGuard-1.0.0-portable-win64.zip
LocalPDFGuard-1.0.0-setup-win64.exe
LocalPDFGuard-1.0.0-sha256.txt
release-notes-1.0.0.md
licenses.zip
```

SHA256 文件示例：

```text
<sha256>  LocalPDFGuard-1.0.0-portable-win64.zip
<sha256>  LocalPDFGuard-1.0.0-setup-win64.exe
```

## 10. 许可证文件

必须随包附带：

- Python license。
- PyMuPDF license 或商业授权说明。
- pikepdf MPL-2.0 license。
- qpdf license。
- Pillow license。
- PyInstaller license。
- Inno Setup license，安装包构建工具说明。

商业闭源发布前，必须单独确认 PyMuPDF 授权。

