from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from ..models import PermissionOptions, ProcessOptions, RedactionBox, WatermarkOptions
from ..pdf_core import detect_redactions, render_page_image
from ..pipeline import process_pdf
from ..rules import selected_rules
from .coordinates import canvas_to_pdf_rect, pdf_to_canvas_rect


class LocalPDFGuardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Local PDF Guard")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.input_path: Path | None = None
        self.preview_path: Path | None = None
        self.page_index = 0
        self.page_count = 0
        self.zoom = 1.2
        self.page_size: tuple[float, float] = (0, 0)
        self.boxes: list[RedactionBox] = []
        self.detections = []
        self._photo = None
        self._drag_start: tuple[float, float] | None = None
        self._drag_rect_id: int | None = None
        self._worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_vars()
        self._build_layout()
        self.after(150, self._poll_worker)

    def _build_vars(self) -> None:
        self.open_password_var = tk.StringVar()
        self.owner_password_var = tk.StringVar(value="owner-pass")
        self.user_password_var = tk.StringVar()
        self.watermark_var = tk.StringVar(value="内部资料 禁止外传")
        self.output_var = tk.StringVar()
        self.status_var = tk.StringVar(value="请选择 PDF")
        self.keyword_var = tk.StringVar()
        self.mobile_var = tk.BooleanVar(value=True)
        self.id_card_var = tk.BooleanVar(value=True)
        self.email_var = tk.BooleanVar(value=True)
        self.bank_card_var = tk.BooleanVar(value=False)
        self.uscc_var = tk.BooleanVar(value=False)
        self.flatten_var = tk.BooleanVar(value=False)
        self.allow_print_var = tk.BooleanVar(value=False)
        self.allow_copy_var = tk.BooleanVar(value=False)
        self.allow_modify_var = tk.BooleanVar(value=False)

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=8)
        root.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root, width=290)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
        center = ttk.Frame(root)
        center.grid(row=0, column=1, sticky="nsew")
        right = ttk.Frame(root, width=290)
        right.grid(row=0, column=2, sticky="nse", padx=(8, 0))

        self._build_left(left)
        self._build_center(center)
        self._build_right(right)

    def _build_left(self, parent: ttk.Frame) -> None:
        ttk.Button(parent, text="打开 PDF", command=self.open_pdf).grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(parent, text="打开密码").grid(row=1, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.open_password_var, show="*").grid(row=2, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(parent, text="规则").grid(row=3, column=0, sticky="w")
        ttk.Checkbutton(parent, text="手机号", variable=self.mobile_var).grid(row=4, column=0, sticky="w")
        ttk.Checkbutton(parent, text="身份证", variable=self.id_card_var).grid(row=5, column=0, sticky="w")
        ttk.Checkbutton(parent, text="邮箱", variable=self.email_var).grid(row=6, column=0, sticky="w")
        ttk.Checkbutton(parent, text="银行卡", variable=self.bank_card_var).grid(row=7, column=0, sticky="w")
        ttk.Checkbutton(parent, text="统一社会信用代码", variable=self.uscc_var).grid(row=8, column=0, sticky="w")
        ttk.Label(parent, text="关键词，逗号分隔").grid(row=9, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(parent, textvariable=self.keyword_var).grid(row=10, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(parent, text="自动识别", command=self.auto_detect).grid(row=11, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(parent, text="水印").grid(row=12, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.watermark_var).grid(row=13, column=0, sticky="ew", pady=(0, 8))
        ttk.Checkbutton(parent, text="安全压平输出", variable=self.flatten_var).grid(row=14, column=0, sticky="w", pady=(0, 12))

        ttk.Label(parent, text="权限密码").grid(row=15, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.owner_password_var, show="*").grid(row=16, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(parent, text="打开密码，可留空").grid(row=17, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.user_password_var, show="*").grid(row=18, column=0, sticky="ew", pady=(0, 8))
        ttk.Checkbutton(parent, text="允许打印", variable=self.allow_print_var).grid(row=19, column=0, sticky="w")
        ttk.Checkbutton(parent, text="允许复制", variable=self.allow_copy_var).grid(row=20, column=0, sticky="w")
        ttk.Checkbutton(parent, text="允许修改", variable=self.allow_modify_var).grid(row=21, column=0, sticky="w")

        ttk.Label(parent, text="输出文件").grid(row=22, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(parent, textvariable=self.output_var).grid(row=23, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(parent, text="选择输出", command=self.choose_output).grid(row=24, column=0, sticky="ew", pady=(0, 12))
        ttk.Button(parent, text="执行处理", command=self.run_process).grid(row=25, column=0, sticky="ew")
        parent.columnconfigure(0, weight=1)

    def _build_center(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(toolbar, text="上一页", command=self.prev_page).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(toolbar, text="下一页", command=self.next_page).grid(row=0, column=1, padx=(0, 12))
        ttk.Button(toolbar, text="缩小", command=lambda: self.set_zoom(self.zoom - 0.2)).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(toolbar, text="放大", command=lambda: self.set_zoom(self.zoom + 0.2)).grid(row=0, column=3, padx=(0, 12))
        self.page_label = ttk.Label(toolbar, text="0 / 0")
        self.page_label.grid(row=0, column=4, sticky="w")

        canvas_frame = ttk.Frame(parent)
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="#f3f3f3", highlightthickness=1, highlightbackground="#c8c8c8")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        ttk.Label(parent, textvariable=self.status_var).grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def _build_right(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="脱敏区域").grid(row=0, column=0, sticky="w")
        self.box_list = tk.Listbox(parent, height=22, width=36)
        self.box_list.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        ttk.Button(parent, text="删除选中", command=self.delete_selected_box).grid(row=2, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(parent, text="处理报告").grid(row=3, column=0, sticky="w")
        self.report_text = tk.Text(parent, height=16, width=36)
        self.report_text.grid(row=4, column=0, sticky="nsew")
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)

    def open_pdf(self) -> None:
        path = filedialog.askopenfilename(title="选择 PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self.input_path = Path(path)
        self.preview_path = self.input_path
        default_output = self.input_path.with_name(f"{self.input_path.stem}_guarded.pdf")
        self.output_var.set(str(default_output))
        self.page_index = 0
        self.boxes.clear()
        self.detections = []
        self.render_current_page()

    def choose_output(self) -> None:
        path = filedialog.asksaveasfilename(title="输出 PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            self.output_var.set(path)

    def auto_detect(self) -> None:
        if not self.input_path:
            messagebox.showwarning("提示", "请先选择 PDF")
            return
        rules = self._selected_rules()
        keywords = self._keywords()
        try:
            detections, boxes = detect_redactions(self.input_path, rules, keywords, self._open_password())
        except Exception as exc:
            messagebox.showerror("自动识别失败", str(exc))
            return
        self.detections = detections
        self.boxes = boxes
        self._refresh_box_list()
        self.render_current_page()
        self.status_var.set(f"自动识别完成：{len(boxes)} 个可定位区域，{len(detections)} 个候选")

    def run_process(self) -> None:
        if not self.input_path:
            messagebox.showwarning("提示", "请先选择 PDF")
            return
        if not self.output_var.get().strip():
            messagebox.showwarning("提示", "请选择输出文件")
            return
        if not self.owner_password_var.get().strip():
            messagebox.showwarning("提示", "请设置权限密码")
            return
        self.status_var.set("正在处理...")
        self.report_text.delete("1.0", tk.END)
        thread = threading.Thread(target=self._process_worker, daemon=True)
        thread.start()

    def _process_worker(self) -> None:
        rules = self._selected_rules()
        keywords = self._keywords()
        options = ProcessOptions(
            input_path=self.input_path,
            output_path=Path(self.output_var.get()),
            open_password=self._open_password(),
            owner_password=self.owner_password_var.get().strip(),
            user_password=self.user_password_var.get(),
            boxes=list(self.boxes),
            watermark=WatermarkOptions(text=self.watermark_var.get()),
            flatten=self.flatten_var.get(),
            flatten_dpi=200,
            permissions=PermissionOptions(
                allow_print=self.allow_print_var.get(),
                allow_copy=self.allow_copy_var.get(),
                allow_modify=self.allow_modify_var.get(),
            ),
        )
        try:
            report = process_pdf(options, rules, keywords)
            payload = {
                "output_path": str(report.output_path),
                "pages": report.pages,
                "redaction_count": report.redaction_count,
                "watermark_applied": report.watermark_applied,
                "flattened": report.flattened,
                "encrypted": report.encrypted,
                "verification_passed": report.verification.passed,
                "residual_hits": report.verification.residual_hits,
                "notes": report.verification.notes,
            }
            self._worker_queue.put(("ok", payload))
        except Exception as exc:
            self._worker_queue.put(("error", str(exc)))

    def _poll_worker(self) -> None:
        try:
            kind, payload = self._worker_queue.get_nowait()
        except queue.Empty:
            self.after(150, self._poll_worker)
            return

        if kind == "ok":
            output_path = Path(payload["output_path"])
            self.preview_path = output_path
            self.page_index = min(self.page_index, max(int(payload["pages"]) - 1, 0))
            self.boxes.clear()
            self._refresh_box_list()
            self.render_current_page()
            self.status_var.set("处理完成，当前预览为输出 PDF")
            self.report_text.delete("1.0", tk.END)
            self.report_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))
            messagebox.showinfo("完成", "PDF 处理完成")
        else:
            self.status_var.set("处理失败")
            messagebox.showerror("处理失败", str(payload))
        self.after(150, self._poll_worker)

    def render_current_page(self) -> None:
        if not self.preview_path:
            return
        try:
            password = self.user_password_var.get() if self.preview_path != self.input_path else self._open_password()
            image, page_size, page_count = render_page_image(self.preview_path, self.page_index, self.zoom, password)
        except Exception as exc:
            messagebox.showerror("预览失败", str(exc))
            return
        self.page_size = page_size
        self.page_count = page_count
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self.canvas.configure(scrollregion=(0, 0, image.width, image.height))
        self.page_label.configure(text=f"{self.page_index + 1} / {self.page_count}")
        self._draw_boxes()

    def _draw_boxes(self) -> None:
        for index, box in enumerate(self.boxes):
            if box.page_index != self.page_index:
                continue
            x0, y0, x1, y1 = pdf_to_canvas_rect(box.rect, self.zoom)
            color = "#d62728" if box.source == "auto" else "#1f77b4"
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2, tags=("box", f"box-{index}"))

    def _on_mouse_down(self, event) -> None:
        if not self.input_path:
            return
        self._drag_start = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if self._drag_rect_id:
            self.canvas.delete(self._drag_rect_id)
        x, y = self._drag_start
        self._drag_rect_id = self.canvas.create_rectangle(x, y, x, y, outline="#1f77b4", width=2, dash=(4, 3))

    def _on_mouse_drag(self, event) -> None:
        if self._drag_start is None or self._drag_rect_id is None:
            return
        x0, y0 = self._drag_start
        x1, y1 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self._drag_rect_id, x0, y0, x1, y1)

    def _on_mouse_up(self, event) -> None:
        if self._drag_start is None:
            return
        end = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        rect = canvas_to_pdf_rect(self._drag_start, end, self.zoom)
        self._drag_start = None
        if self._drag_rect_id:
            self.canvas.delete(self._drag_rect_id)
            self._drag_rect_id = None
        if abs(rect[2] - rect[0]) < 3 or abs(rect[3] - rect[1]) < 3:
            return
        self.boxes.append(
            RedactionBox(
                page_index=self.page_index,
                rect=rect,
                source="manual",
                category="manual",
                label="手动框选",
            )
        )
        self._refresh_box_list()
        self.render_current_page()

    def delete_selected_box(self) -> None:
        selection = self.box_list.curselection()
        if not selection:
            return
        index = selection[0]
        if 0 <= index < len(self.boxes):
            del self.boxes[index]
            self._refresh_box_list()
            self.render_current_page()

    def prev_page(self) -> None:
        if self.page_index > 0:
            self.page_index -= 1
            self.render_current_page()

    def next_page(self) -> None:
        if self.page_index + 1 < self.page_count:
            self.page_index += 1
            self.render_current_page()

    def set_zoom(self, value: float) -> None:
        self.zoom = max(0.4, min(3.0, value))
        self.render_current_page()

    def _refresh_box_list(self) -> None:
        self.box_list.delete(0, tk.END)
        for index, box in enumerate(self.boxes, start=1):
            self.box_list.insert(tk.END, f"{index}. 第 {box.page_index + 1} 页 {box.category} {box.source}")

    def _selected_rules(self):
        return selected_rules(
            redact_mobile=self.mobile_var.get(),
            redact_id_card=self.id_card_var.get(),
            redact_email=self.email_var.get(),
            redact_bank_card=self.bank_card_var.get(),
            redact_uscc=self.uscc_var.get(),
        )

    def _keywords(self) -> list[str]:
        return [part.strip() for part in self.keyword_var.get().split(",") if part.strip()]

    def _open_password(self) -> str | None:
        value = self.open_password_var.get()
        return value if value else None


def main() -> int:
    app = LocalPDFGuardApp()
    app.mainloop()
    return 0
