from __future__ import annotations

from pathlib import Path

import fitz


def main() -> int:
    output = Path("work/sample_sensitive.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "Local PDF Guard 测试文件", fontsize=18)
    page.insert_text((72, 150), "手机号：13812345678", fontsize=14)
    page.insert_text((72, 180), "身份证：110101199001011234", fontsize=14)
    page.insert_text((72, 210), "邮箱：demo@example.com", fontsize=14)
    page.insert_text((72, 240), "项目代号：Alpha", fontsize=14)
    doc.save(output)
    doc.close()
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

