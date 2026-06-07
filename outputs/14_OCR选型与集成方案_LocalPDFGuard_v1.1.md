# OCR 选型与集成方案: LocalPDFGuard v1.1

版本: v1.1  
日期: 2026-06-07  
结论: v1.1 主推 PaddleOCR，本地集成；保留 Umi-OCR 适配接口；不建议把 Tesseract 作为中文扫描件主引擎。

## 1. 选型结论

推荐路线:

1. v1.1 默认 OCR 引擎选择 PaddleOCR。
2. 设计 `OcrProvider` 抽象层，避免业务代码绑定具体 OCR 产品。
3. 首版只落地 PaddleOCR CPU 本地包。
4. Umi-OCR 作为可选外部适配器放到 v1.2 或 v1.1 后续小版本。
5. Tesseract 只作为备选实验项，不作为中文敏感信息识别主路线。

## 2. 为什么推荐 PaddleOCR

PaddleOCR 更适合作为本工具的内嵌 OCR 底座:

- 中文 OCR 能力强，适合手机号、身份证、姓名、地址这类中文办公材料。
- Python 集成路径直接，适合当前 Python + PyMuPDF 架构。
- 可以完全本地运行。
- 支持文本块坐标输出，便于把识别结果转换成 PDF 脱敏框。
- 社区和文档活跃，适合后续持续升级。
- 可做批量任务，不依赖外部 GUI 软件是否启动。

已核对的公开信息:

- PaddleOCR 官方仓库定位为 OCR 和文档智能工具，支持 PDF/图片转结构化数据，支持 100+ 语言，并在 README 中说明 PP-OCRv5 支持中英日等混合文本识别。
- PaddleOCR 公开更新记录显示 2026-05-28 发布 3.6.0。

参考:

- https://github.com/PaddlePaddle/PaddleOCR

## 3. Umi-OCR 的定位

Umi-OCR 很适合普通用户直接使用，也适合作为后续可选外部 OCR 服务:

- Windows 本地离线体验好。
- 自带 GUI。
- 支持截图 OCR、批量 OCR、PDF 文档识别。
- 支持命令行和 HTTP 接口。
- 底层可使用 PaddleOCR-json、RapidOCR-json。
- MIT 许可，集成限制相对友好。

但 v1.1 不建议把 Umi-OCR 作为主内嵌底座，原因是:

- 它本身是完整 GUI 应用，嵌入到我们的 PyInstaller 工具中会让部署链路更复杂。
- 自动化调用需要管理外部进程、端口、接口兼容性和用户机器上的运行状态。
- 我们需要的是“页面图片进、文字块和坐标出”的可控 SDK 形态，PaddleOCR 更直接。

建议:

- v1.1 先写好 `UmiOcrProvider` 接口预留。
- 后续如果用户已经安装 Umi-OCR，可以通过 HTTP 或命令行适配。
- 适配器只作为可选引擎，不影响主程序离线运行。

参考:

- https://github.com/hiroi-sora/Umi-OCR

## 4. 为什么不主推 Tesseract

Tesseract 是成熟 OCR 引擎，但不适合本项目 v1.1 的主 OCR 路线:

- 中文复杂版面、身份证、合同扫描件场景下，调参和预处理成本偏高。
- Python 侧通常还要额外处理安装包、语言包、路径配置。
- 对本项目最关键的中文坐标候选识别，PaddleOCR 更省开发成本。

Tesseract 可保留为后续实验选项，适合英文文档或极轻量部署场景。

参考:

- https://github.com/tesseract-ocr/tesseract

## 5. v1.1 OCR 能力边界

v1.1 OCR 不做“自动无确认脱敏”，只做候选识别。

必须支持:

- 扫描件手机号识别。
- 扫描件身份证号识别。
- 扫描件姓名候选识别。
- 扫描件地址候选识别。
- OCR 候选框显示、确认、修改、删除。
- OCR 结果参与输出安全报告。

不承诺:

- 手写体高准确率。
- 模糊、倾斜、压缩严重扫描件高准确率。
- 姓名和地址 100% 自动识别。
- 仅凭权限密码实现绝对防复制。

## 6. 技术集成设计

新增目录建议:

```text
src/pdf_guard/ocr/
  __init__.py
  provider.py
  paddle_provider.py
  umi_provider.py
  models.py
  preprocess.py
  detectors.py
  cache.py
```

核心模型:

```python
from dataclasses import dataclass

@dataclass
class OcrBlock:
    page_index: int
    text: str
    bbox_px: tuple[float, float, float, float]
    confidence: float
    engine: str

@dataclass
class OcrPageInput:
    page_index: int
    image_path: str
    image_width: int
    image_height: int
    pdf_width: float
    pdf_height: float
    render_dpi: int

class OcrProvider:
    name: str

    def is_available(self) -> bool:
        raise NotImplementedError

    def recognize_page(self, page: OcrPageInput) -> list[OcrBlock]:
        raise NotImplementedError
```

OCR 到 PDF 坐标转换:

```text
pdf_x = image_x / image_width * pdf_width
pdf_y = image_y / image_height * pdf_height
```

注意:

- PyMuPDF 渲染页图时必须记录 DPI、像素宽高、PDF point 宽高。
- 坐标转换必须通过同一个渲染矩阵验证。
- 页面旋转必须统一处理，否则框会错位。

## 7. 敏感信息识别策略

### 7.1 手机号

规则:

- 正则识别 `1[3-9]\d{9}`。
- 允许中间存在空格、短横线。
- OCR 常见错误纠正: `O` 视为 `0`，`I/l` 视为 `1`，仅在数字上下文内启用。

默认策略:

- 置信度高于阈值时默认勾选。
- 仍允许用户取消。

### 7.2 身份证号

规则:

- 18 位身份证号。
- 支持末位 `X/x`。
- 校验出生日期。
- 校验行政区划前两位的基本范围。
- 可加入校验码算法。

默认策略:

- 通过校验码时默认高风险。
- 默认勾选并提示复核。

### 7.3 姓名

姓名自动识别误判高，v1.1 用启发式，不上复杂模型。

候选来源:

- `姓名`、`联系人`、`法定代表人`、`经办人`、`签字` 等关键词附近。
- 身份证字段中 `姓名:` 后的短中文文本。
- 表格中字段名右侧或下方的 2 到 4 个中文字符。

默认策略:

- 默认不直接高置信处理。
- 进入“姓名候选”列表，由用户确认。

### 7.4 地址

地址识别同样使用启发式。

候选来源:

- `地址`、`住址`、`联系地址`、`注册地址`、`户籍地址`、`通讯地址` 等关键词附近。
- 包含省、市、区、县、镇、街道、路、号、室等连续文本。

默认策略:

- 默认进入待确认列表。
- 长地址可自动合并相邻 OCR 文本块。

## 8. 离线依赖策略

v1.1 建议拆成两种发行包:

| 包 | 内容 | 适用 |
|---|---|---|
| Standard | 不含 OCR 模型，仅含 v0.1.0 能力和 GUI 优化 | 体积小，普通文本 PDF |
| OCR Full | 含 PaddleOCR CPU 依赖和模型 | 扫描件脱敏 |

原因:

- PaddleOCR 及模型会显著增加体积。
- 有些用户只处理文本 PDF，不需要 OCR。
- 两个包都必须离线可运行。

离线打包要求:

- `vendor/wheelhouse` 保存 Python wheel。
- `vendor/ocr_models/paddleocr` 保存模型文件。
- `requirements.ocr.lock.txt` 锁定 OCR 依赖。
- Release 上传 Standard 和 OCR Full 两种包。
- 首次运行不得联网下载模型。

## 9. 性能策略

- 默认 OCR DPI: 200。
- 高精度 OCR DPI: 300。
- 批量 OCR 并发默认 1，避免内存暴涨。
- 支持 OCR 结果缓存，文档未变化时复用。
- 超大页面自动降采样并提示。

## 10. 验收样本

至少准备以下样本:

- 文本型 PDF，含手机号、身份证、邮箱。
- 扫描件 PDF，含手机号、身份证。
- 身份证复印件扫描 PDF。
- 合同扫描 PDF，含姓名和地址。
- 模糊扫描 PDF。
- 横向页面 PDF。
- 多页混合 PDF，部分文本层、部分扫描页。

