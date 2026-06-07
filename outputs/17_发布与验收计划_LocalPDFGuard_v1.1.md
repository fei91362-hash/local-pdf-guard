# 发布与验收计划: LocalPDFGuard v1.1

版本: v1.1  
日期: 2026-06-07  
目标: 定义 v1.1 从开发到 GitHub Release 的完整验收和发布流程。

## 1. 发布产物

v1.1 建议发布 4 个主产物:

```text
LocalPDFGuard-1.1.0-standard-portable-win64.zip
LocalPDFGuard-1.1.0-standard-setup-win64.exe
LocalPDFGuard-1.1.0-ocrfull-portable-win64.zip
LocalPDFGuard-1.1.0-ocrfull-setup-win64.exe
```

附加产物:

```text
SHA256SUMS.txt
release-notes-v1.1.0.md
```

## 2. Standard 与 OCR Full 区别

| 版本 | 包含 OCR | 适用场景 |
|---|---:|---|
| Standard | 否 | 文本型 PDF、水印、权限、手动框选 |
| OCR Full | 是 | 扫描件 PDF、图片型 PDF 自动候选识别 |

两个版本都必须:

- 无需安装 Python。
- 无需安装 pip。
- 无需联网下载依赖。
- 不修改源 PDF。
- 输出新 PDF 和报告。

## 3. GitHub Actions 流程

新增 workflow:

```text
.github/workflows/release.yml
```

触发条件:

```yaml
on:
  push:
    tags:
      - "v*"
```

流程阶段:

1. Checkout。
2. 设置 Python。
3. 安装基础依赖。
4. 安装测试依赖。
5. 运行单元测试。
6. 构建 Standard 便携版。
7. 构建 Standard 安装版。
8. 安装 OCR 依赖和复制 OCR 模型。
9. 构建 OCR Full 便携版。
10. 构建 OCR Full 安装版。
11. 生成 SHA256。
12. 创建 Release。
13. 上传资产。

## 4. 依赖锁定验收

必须存在:

```text
requirements.lock.txt
requirements-dev.lock.txt
requirements.full.lock.txt
requirements.ocr.lock.txt
```

OCR Full 必须存在:

```text
vendor/wheelhouse-ocr/
vendor/ocr_models/paddleocr/
```

验收要求:

- 在干净 Windows 机器上断网运行 OCR Full，不发生模型下载请求。
- Standard 包不包含大型 OCR 模型。
- OCR Full 包可以识别本地扫描件样本。

## 5. 功能验收

### 5.1 GUI

| 项目 | 标准 |
|---|---|
| 框选 | 可新建框 |
| 选中 | 点击已有框可选中 |
| 拖拽 | 选中框可移动 |
| 缩放 | 角点和边缘可调整大小 |
| 删除 | Delete 和右键菜单可删除 |
| 缩放页面 | 预设缩放和 Ctrl+滚轮可用 |
| 滚动 | 纵向、横向滚动可用 |
| 翻页 | 首页、上一页、下一页、末页、页码跳转可用 |
| 输出动作 | 可打开输出文件、输出目录、报告 |

### 5.2 OCR

| 项目 | 标准 |
|---|---|
| 本地运行 | 不依赖云服务 |
| 手机号 | 清晰扫描件可生成候选框 |
| 身份证 | 清晰扫描件可生成候选框 |
| 姓名 | 关键词附近姓名可生成待确认候选 |
| 地址 | 关键词附近地址可生成待确认候选 |
| 人工复核 | OCR 框可删除、移动、缩放 |
| 报告 | OCR 命中写入处理报告 |

### 5.3 批量

| 项目 | 标准 |
|---|---|
| 多选文件 | 可一次选择多个 PDF |
| 文件夹 | 可选择文件夹扫描 PDF |
| 递归 | 可开关递归扫描 |
| 失败继续 | 单个文件失败不影响批次 |
| 取消 | 可取消未开始的后续文件 |
| 总报告 | 生成批次报告 |

### 5.4 安全

| 项目 | 标准 |
|---|---|
| 文本复查 | 输出 PDF 文本层不残留已知敏感规则 |
| OCR 复查 | 启用后可对输出页 OCR 检查 |
| 元数据 | metadata 和 XMP 被清理 |
| 结构清理 | 附件、注释、链接、脚本被清理或报告 |
| 权限 | 禁止复制、禁止修改等权限位可验证 |
| 风险等级 | 输出 PASS/WARN/FAIL |

## 6. 样本集

建议建立:

```text
tests/fixtures/v1_1/
  text_sensitive.pdf
  scan_mobile_id.pdf
  scan_name_address.pdf
  mixed_text_scan.pdf
  rotated_pages.pdf
  metadata_links_annotations.pdf
  damaged.pdf
```

样本不应提交真实敏感数据。必须使用合成数据。

## 7. 发布前命令

本地发布前:

```powershell
py -3 -m pytest -q
py -3 -m pdf_guard --help
.\scripts\build_portable_gui.ps1
.\scripts\build_installer.ps1
```

OCR Full 发布前:

```powershell
.\scripts\build_portable_gui_ocrfull.ps1
.\scripts\build_installer_ocrfull.ps1
```

SHA256:

```powershell
Get-FileHash outputs\LocalPDFGuard-1.1.0-*.zip -Algorithm SHA256
Get-FileHash outputs\LocalPDFGuard-1.1.0-*.exe -Algorithm SHA256
```

## 8. Release 说明模板

```markdown
# LocalPDFGuard v1.1.0

## 新增

- GUI 框选区域支持拖拽、缩放、删除。
- 处理完成后可打开输出文件和输出目录。
- 页面缩放、滚动、翻页体验优化。
- OCR Full 版本支持本地 OCR 候选识别。
- 支持批量处理 PDF。
- 增强输出安全验证和风险报告。
- GitHub Actions 自动构建和发布。

## 下载

- Standard Portable: LocalPDFGuard-1.1.0-standard-portable-win64.zip
- Standard Installer: LocalPDFGuard-1.1.0-standard-setup-win64.exe
- OCR Full Portable: LocalPDFGuard-1.1.0-ocrfull-portable-win64.zip
- OCR Full Installer: LocalPDFGuard-1.1.0-ocrfull-setup-win64.exe

## 校验

请使用 SHA256SUMS.txt 校验下载文件。
```

## 9. 发布判定

满足以下条件才允许发布正式 v1.1.0:

- 所有自动测试通过。
- GUI 手工 smoke test 通过。
- OCR 样本验收通过。
- 批量处理样本验收通过。
- 安全报告验收通过。
- Standard 和 OCR Full 在干净 Windows 机器离线可运行。
- Release 资产和 SHA256 完整。

