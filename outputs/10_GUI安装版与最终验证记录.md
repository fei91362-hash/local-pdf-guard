# GUI、安装版与最终验证记录

日期：2026-06-07  
范围：V1 本地 Windows 工具落地推进

## 1. 新增能力

本轮在 CLI 核心闭环基础上补齐：

- Tkinter GUI。
- PDF 文件选择。
- PDF 页面预览。
- 自动识别按钮。
- 手动框选脱敏区域。
- 脱敏框列表和删除。
- 水印、压平、权限密码参数。
- 后台线程执行处理。
- 处理报告展示。
- GUI 便携版 PyInstaller 打包。
- Inno Setup 安装版。

## 2. 新增源码

- `src/pdf_guard/ui/app.py`
- `src/pdf_guard/ui/coordinates.py`
- `src/pdf_guard/gui.py`
- `scripts/local_pdf_guard_gui_launcher.py`
- `packaging/pyinstaller/LocalPDFGuard.spec`
- `packaging/inno/LocalPDFGuard.iss`
- `scripts/build_portable_gui.ps1`
- `scripts/build_installer.ps1`

## 3. 新增测试

- `tests/test_coordinates.py`
- `tests/test_gui_import.py`

## 4. 最终产物

### GUI 便携版

```text
dist/LocalPDFGuard-0.1.0-portable-win64.zip
```

SHA256:

```text
648F9DDC16F314617CC6C9DC9221343A60F1CF0B65032B1E65722A08479CCBC7
```

### 安装版

```text
dist/LocalPDFGuard-0.1.0-setup-win64.exe
```

SHA256:

```text
3BE2A2BD9B96C197E1F910F484A98E53EECD90980BAE5DA310554AE2F6DA1AB6
```

### CLI 核心便携版

```text
dist/LocalPDFGuardCore-0.1.0-portable-win64.zip
```

## 5. 已执行验证

### 回归测试

命令：

```powershell
.\.venv\Scripts\pytest.exe
```

结果：

```text
7 passed in 3.57s
```

覆盖：

- 规则识别。
- 自动 redaction 流程。
- 水印。
- 权限加密。
- 压平。
- 坐标转换。
- GUI 模块导入。

### 普通 CLI 冒烟

命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_cli.ps1
```

结果：

```text
smoke passed
```

### 压平 CLI 冒烟

命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_flatten_cli.ps1
```

结果：

```text
flatten smoke passed
```

### GUI 便携版构建

命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_portable_gui.ps1
```

结果：

```text
dist\LocalPDFGuard-0.1.0-portable-win64.zip
```

### 安装版构建

命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

结果：

```text
dist\LocalPDFGuard-0.1.0-setup-win64.exe
```

### GUI 启动冒烟

命令：

```powershell
$p = Start-Process -FilePath .\dist\LocalPDFGuard\LocalPDFGuard.exe -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3
$alive = -not $p.HasExited
if ($alive) { Stop-Process -Id $p.Id -Force }
if (-not $alive) { throw "GUI exited early" }
```

结果：

```text
gui launch smoke passed
```

## 6. 仍需人工验收

以下项目需要真实人工操作或干净虚拟机，不适合在当前自动化环境里完全证明：

- 在 GUI 里手动打开 PDF、拖拽框选、点击执行处理的完整人工路径。
- 安装版实际安装、开始菜单快捷方式、桌面快捷方式、卸载。
- 干净 Windows 虚拟机上无 Python/无 pip 环境运行。

当前证据可以证明：

- 便携版和安装版已经生成。
- GUI 运行时能启动。
- 核心 PDF 处理链路通过自动测试和冒烟测试。

