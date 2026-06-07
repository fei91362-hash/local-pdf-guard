# 开发文档: LocalPDFGuard v1.1

版本: v1.1  
日期: 2026-06-07  
目标: 将已确认的 GUI、OCR、批量、安全、发布需求拆成可执行开发任务。

## 1. 开发原则

- 继续以 PyMuPDF 为 PDF 核心处理底座。
- 继续保持 Windows 本地离线运行。
- 新能力必须兼容现有 CLI 和 GUI。
- OCR 候选默认可人工复核，不做静默自动脱敏。
- 安全清理失败时必须明确报告，不允许假装成功。
- 所有产物从 GitHub Release 发布，不把 exe、zip、dll、pdf 产物提交进源码仓库。

## 2. 分支和版本

建议:

```text
main/master        当前稳定源码
feature/v1.1-gui   GUI 框编辑
feature/v1.1-ocr   OCR 识别
feature/v1.1-batch 批量处理
feature/v1.1-security 安全验证
release/v1.1.0     发布候选
```

版本号:

- 开发版: `1.1.0-dev`
- 内测版: `1.1.0-beta.1`
- 候选版: `1.1.0-rc.1`
- 正式版: `1.1.0`

## 3. 任务拆分

### 3.1 M1: GUI 框编辑

目标:

- 框选后可拖拽、缩放、删除。
- 页面缩放、滚动、翻页体验优化。
- 处理完成后打开输出文件、打开输出目录。

任务:

- 新增 `src/pdf_guard/ui/box_editor.py`。
- 抽出 Canvas 坐标转换和命中测试。
- 为框增加唯一 ID。
- 增加选中状态和手柄绘制。
- 增加移动、缩放、删除事件。
- 增加右键菜单。
- 增加输出动作按钮。
- 增加页码跳转和缩放预设。
- 补充单元测试和手工 smoke test。

验收:

```powershell
py -3 -m pytest -q
py -3 -m pdf_guard
```

手工检查:

- 画 3 个框。
- 分别移动、缩放、删除。
- 翻页后返回，位置不变。
- 执行处理后，点击打开输出文件和输出目录。

### 3.2 M2: OCR 基础集成

目标:

- 引入 PaddleOCR provider。
- 扫描件页面可 OCR 出文本块。
- 手机号、身份证生成候选框。

任务:

- 新增 `src/pdf_guard/ocr/models.py`。
- 新增 `src/pdf_guard/ocr/provider.py`。
- 新增 `src/pdf_guard/ocr/paddle_provider.py`。
- 新增 `src/pdf_guard/ocr/preprocess.py`。
- 新增 `src/pdf_guard/ocr/detectors.py`。
- 增加 `requirements.ocr.lock.txt`。
- 增加 OCR 模型离线目录约定。
- GUI 增加“扫描件 OCR 识别”按钮。
- OCR 候选进入现有框列表。

验收:

- 清晰扫描件手机号可识别并定位。
- 清晰扫描件身份证号可识别并定位。
- OCR 框可人工调整。
- 不启用 OCR 时，基础功能不受影响。

### 3.3 M3: 姓名和地址候选识别

目标:

- 对姓名、地址做可复核候选识别。

任务:

- 实现关键词邻近块识别。
- 实现相邻 OCR block 合并。
- 增加姓名关键词表。
- 增加地址关键词表。
- GUI 候选列表显示识别理由。
- 默认将姓名、地址标记为待确认。

验收:

- `姓名: 张三`、`联系人: 李四` 可生成候选。
- `联系地址: xx省xx市xx区xx路xx号` 可生成候选。
- 误识别候选可以删除。

### 3.4 M4: 批量处理

目标:

- 多 PDF 连续处理。
- 单文件失败不影响批次。
- 输出总报告。

任务:

- 新增 `src/pdf_guard/batch/models.py`。
- 新增 `src/pdf_guard/batch/runner.py`。
- 新增 `src/pdf_guard/batch/report.py`。
- GUI 增加批量处理面板。
- 支持多选 PDF。
- 支持文件夹扫描。
- 支持取消。
- 每文件输出独立报告。
- 批次输出总报告。

验收:

- 10 个样本批量处理，至少 1 个故意损坏文件，批次仍继续。
- UI 状态准确显示成功、失败、取消。
- 总报告能定位失败文件和原因。

### 3.5 M5: 安全验证增强

目标:

- 输出后自动生成更强安全报告。

任务:

- 增强 `security.py` 的结构清理。
- 增强 `verify.py` 的文本规则复查。
- 增加 OCR 输出复查。
- 增加 metadata、XMP、附件、注释、链接、脚本检查。
- 增加 `PASS/WARN/FAIL` 风险等级。
- GUI 显示报告入口。

验收:

- 含 metadata 的样本输出后 metadata 被清理。
- 含链接和注释的样本输出后链接和注释被清理或报告。
- 输出中残留手机号时报告为 `FAIL`。
- 无法判断的隐藏结构报告为 `WARN`。

### 3.6 M6: 自动发布

目标:

- tag 触发 GitHub Actions 自动发布。

任务:

- 新增 `.github/workflows/release.yml`。
- 缓存 pip wheel。
- 安装依赖。
- 运行测试。
- 构建 standard portable。
- 构建 standard installer。
- 构建 ocrfull portable。
- 构建 ocrfull installer。
- 生成 SHA256。
- 创建 Release 并上传资产。

验收:

- 推送 `v1.1.0-rc.1` tag 后自动生成 prerelease。
- 推送 `v1.1.0` tag 后自动生成正式 Release。
- Release 页面包含 zip、exe、SHA256。

## 4. 本地开发环境

基础环境:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.lock.txt
.\.venv\Scripts\pip.exe install -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m pytest -q
```

OCR 开发环境:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.ocr.lock.txt
```

离线安装验证:

```powershell
.\.venv\Scripts\pip.exe install --no-index --find-links vendor\wheelhouse -r requirements.lock.txt
.\.venv\Scripts\pip.exe install --no-index --find-links vendor\wheelhouse-ocr -r requirements.ocr.lock.txt
```

注意:

- OCR 依赖锁定前必须在 Windows x64 真实环境跑通。
- 不允许运行时从网络下载 OCR 模型。
- 模型目录必须在打包脚本和运行时代码里显式指定。

## 5. 配置项

新增配置建议:

```toml
[ocr]
enabled = false
engine = "paddle"
dpi = 200
confidence_threshold = 0.65
cache_enabled = true
model_dir = "vendor/ocr_models/paddleocr"

[batch]
continue_on_error = true
recursive = false
ocr_enabled = false

[security]
sanitize_metadata = true
sanitize_bookmarks = true
sanitize_annotations = true
sanitize_links = true
sanitize_attachments = true
sanitize_javascript = true
verify_text = true
verify_ocr = false
```

## 6. 报告格式

每个文件报告:

```json
{
  "input": "input.pdf",
  "output": "input_guarded.pdf",
  "risk_level": "PASS",
  "pages": 10,
  "detected": 12,
  "redacted": 12,
  "text_hits_after_output": [],
  "ocr_hits_after_output": [],
  "structure_warnings": [],
  "permissions": {
    "encrypted": true,
    "copy_allowed": false,
    "modify_allowed": false
  }
}
```

批次总报告:

```json
{
  "total": 50,
  "success": 48,
  "failed": 2,
  "canceled": 0,
  "items": []
}
```

## 7. 回归测试清单

每轮开发必须检查:

- CLI `--help` 可用。
- GUI 可启动。
- 文本 PDF 脱敏可用。
- 图片 PDF 手动框选脱敏可用。
- 水印可用。
- 权限密码可用。
- 压平输出可用。
- 输出验证报告可用。
- Windows 便携版可启动。
- 安装版安装和卸载正常。

## 8. 预计开发顺序

推荐顺序:

1. GUI 框编辑。
2. 输出动作和页面体验。
3. PaddleOCR provider。
4. OCR 手机号、身份证。
5. OCR 姓名、地址。
6. 批量处理。
7. 安全验证增强。
8. GitHub Actions 发布。

原因:

- GUI 框编辑是 OCR 复核的前置能力。
- OCR 候选需要进入同一套框编辑模型。
- 批量处理依赖单文件流程稳定。
- 发布自动化适合在功能基本闭环后接入。

