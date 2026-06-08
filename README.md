# LocalPDFGuard

LocalPDFGuard 是一个 Windows 本地运行的 PDF 脱敏、水印、权限保护和批量处理工具。

它的目标是让办公场景里的 PDF 在本机完成处理，不把文件上传到云端。适合处理需要加水印、防复制/防修改、手动框选脱敏、文本规则脱敏，以及扫描件 OCR 候选识别的 PDF。

当前版本：`1.1.0-dev`

## 主要功能

- PDF 脱敏：支持手动框选、手机号、身份证号、邮箱、银行卡号、统一社会信用代码、关键词规则。
- 扫描件脱敏：OCR Full 版本内置 PaddleOCR，可识别扫描件/图片型 PDF 中的手机号、身份证、姓名、地址候选。
- 水印：支持给 PDF 添加文字水印。
- 权限保护：支持 owner password、user password，并控制打印、复制、修改权限。
- 安全压平：可将页面压平成图片 PDF，降低底层文本、图片、对象残留风险。
- 安全检查报告：输出后复查文本残留、权限状态、结构清理状态，并给出 `PASS/WARN/FAIL` 风险等级。
- 批量处理：支持多文件、文件夹、递归扫描、失败继续、单文件报告和批次报告。
- Windows GUI：支持打开 PDF、框选脱敏区域、拖拽/缩放/删除框、翻页、缩放、滚动、处理后打开输出文件/目录/报告。

## v1.1 新增内容

相比上一版基础能力，v1.1 主要新增：

- GUI 框选区域可编辑：选中、拖拽移动、8 个手柄缩放、Delete 删除、右键删除。
- 处理完成后可以直接打开输出 PDF、输出目录、处理报告。
- 页面浏览增强：首页、上一页、下一页、末页、页码跳转、适合宽度、适合整页、缩放预设、Ctrl+滚轮缩放。
- 本地 OCR 脱敏：新增 OCR 抽象层和 PaddleOCR provider。
- CLI 新增 `--enable-ocr` 和 `--verify-ocr`。
- 新增 `batch` 批量处理子命令。
- GUI 新增批量处理入口。
- 安全报告增强：增加风险等级、权限状态、结构告警、清理项记录。
- 发布流程增强：Standard / OCR Full 双版本构建，GitHub Actions 自动发布 workflow。

## 已修复问题

- 修复“处理完成后中间预览仍显示原 PDF，导致误以为没有脱敏”的问题。
- 修复扫描件/图片型 PDF 框选后可能没有真正像素打黑的问题。
- 修复 GUI 中文文案乱码问题。
- 修复 Standard 版误带 PaddleOCR / PaddlePaddle / numpy 等 OCR 重依赖的问题。
- 修复 PaddleOCR 3.6.0 API 兼容问题。
- 修复 PaddleOCR 模型缓存默认写到用户目录的问题，改为运行时内置缓存路径。
- 修复安装包构建可能混用 Standard/OCR Full 目录的问题。
- 修复未启用 OCR 时 OCR 依赖缺失影响基础功能的问题。

## 版本区别

| 版本 | 适合场景 | 是否内置 OCR |
| --- | --- | --- |
| Standard | 水印、文本规则脱敏、手动框选脱敏、权限保护、批量处理 | 否 |
| OCR Full | 扫描件/图片型 PDF 自动候选识别 | 是 |

两个版本都面向 Windows 本地运行。OCR Full 包体更大，但不要求最终用户自己安装 Python、PaddleOCR 或 OCR 模型。

## 开发环境

要求：

- Windows 10/11 x64
- Python 3.10+

初始化：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.lock.txt
.\.venv\Scripts\pip.exe install -r requirements-dev.lock.txt
.\.venv\Scripts\pip.exe install -e .
```

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

v1.1 冒烟测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_v1_1.ps1
```

OCR 冒烟测试：

```powershell
.\.venv\Scripts\pip.exe install -r requirements.ocr.lock.txt
.\.venv\Scripts\python.exe scripts\ocr_smoke_v1_1.py
```

## GUI 运行

```powershell
.\.venv\Scripts\python.exe -m pdf_guard.gui
```

## CLI 用法

单文件处理：

```powershell
.\.venv\Scripts\python.exe -m pdf_guard process `
  --input work\sample_sensitive.pdf `
  --output work\sample_guarded.pdf `
  --owner-password "change-me" `
  --watermark "Internal Use Only" `
  --redact-mobile `
  --redact-id-card `
  --redact-email `
  --report-json work\sample_guarded.report.json
```

启用 OCR：

```powershell
.\.venv\Scripts\python.exe -m pdf_guard process `
  --input work\scan.pdf `
  --output work\scan_guarded.pdf `
  --owner-password "change-me" `
  --enable-ocr `
  --verify-ocr `
  --report-json work\scan_guarded.report.json
```

批量处理：

```powershell
.\.venv\Scripts\python.exe -m pdf_guard batch `
  --input work\batch `
  --output-dir work\batch_out `
  --owner-password "change-me" `
  --redact-mobile `
  --redact-id-card `
  --recursive
```

## Windows 打包

Standard 便携版：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_portable_gui.ps1 -Edition standard
```

Standard 安装版：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -Edition standard
```

OCR Full 便携版和安装版：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer_ocrfull.ps1
```

发布产物默认输出到 `dist` 目录。源码仓库不提交 `dist`、`build`、`.venv`、`work`、PDF、ZIP、EXE、DLL、OCR 模型缓存等产物。

## 安全边界

- PDF 权限密码可以降低普通软件中的复制、修改风险，但不是强 DRM。
- 真正脱敏应优先使用 redaction 或安全压平，不应只用遮挡层覆盖。
- OCR 的姓名、地址识别存在误判风险，默认作为候选，需要人工确认。
- 对高敏文件建议开启安全压平，并查看处理报告中的 `PASS/WARN/FAIL`。

## 当前验证

v1.1 已完成本地冒烟：

- `pytest`: `14 passed`
- 单文件 CLI 处理：`PASS`
- 批量处理：`2/2` 成功
- OCR smoke：PaddleOCR 可用，命中手机号和身份证样本
- 已生成 Standard / OCR Full 便携版和安装版
