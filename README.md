# Local PDF Guard

Windows 本地 PDF 脱敏、水印、压平和权限密码工具。

当前落地范围是 V1 第一轮 CLI 核心闭环：

```text
输入 PDF -> 自动识别 -> 真脱敏 -> 加水印 -> 可选压平 -> 加权限密码 -> 验证 -> 输出 PDF
```

## 开发运行

```powershell
py -3 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.lock.txt
.\.venv\Scripts\pip.exe install -r requirements-dev.lock.txt
.\.venv\Scripts\pip.exe install -e .
.\.venv\Scripts\python.exe -m pdf_guard --help
```

## CLI 示例

```powershell
.\.venv\Scripts\python.exe -m pdf_guard process `
  --input sample.pdf `
  --output sample_guarded.pdf `
  --owner-password "change-me" `
  --watermark "内部资料 禁止外传" `
  --redact-mobile `
  --redact-id-card `
  --redact-email
```

## GUI 运行

```powershell
.\.venv\Scripts\python.exe -m pdf_guard.gui
```

便携版 GUI：

```powershell
.\dist\LocalPDFGuard\LocalPDFGuard.exe
```

