from __future__ import annotations

import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from ..batch.runner import BatchOptions, BatchRunner
from ..models import PermissionOptions, ProcessOptions, RedactionBox, WatermarkOptions
from ..ocr.detectors import detect_ocr_redaction_boxes
from ..ocr.provider import get_default_ocr_provider
from ..pdf_core import detect_redactions, render_page_image
from ..pipeline import process_pdf, process_report_to_dict
from ..rules import selected_rules
from .coordinates import canvas_to_pdf_rect, pdf_to_canvas_rect

HANDLE_SIZE = 8
MIN_BOX_POINTS = 4
ZOOM_PRESETS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)


class LocalPDFGuardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("LocalPDFGuard v1.1")
        self.geometry("1280x820")
        self.minsize(1060, 680)

        self.input_path: Path | None = None
        self.preview_path: Path | None = None
        self.last_output_path: Path | None = None
        self.last_report_path: Path | None = None
        self.page_index = 0
        self.page_count = 0
        self.zoom = 1.0
        self.page_size: tuple[float, float] = (0, 0)
        self.boxes: list[RedactionBox] = []
        self.detections = []
        self._photo = None
        self._box_seq = 0
        self._active_box_id: str | None = None
        self._drag_mode: str | None = None
        self._drag_start: tuple[float, float] | None = None
        self._drag_original_rect: tuple[float, float, float, float] | None = None
        self._draw_rect_id: int | None = None
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
        self.verify_ocr_var = tk.BooleanVar(value=False)
        self.allow_print_var = tk.BooleanVar(value=False)
        self.allow_copy_var = tk.BooleanVar(value=False)
        self.allow_modify_var = tk.BooleanVar(value=False)
        self.page_jump_var = tk.StringVar(value="1")
        self.zoom_var = tk.StringVar(value="100%")
        self.batch_recursive_var = tk.BooleanVar(value=False)
        self.batch_ocr_var = tk.BooleanVar(value=False)

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=8)
        root.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root, width=300)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
        center = ttk.Frame(root)
        center.grid(row=0, column=1, sticky="nsew")
        right = ttk.Frame(root, width=320)
        right.grid(row=0, column=2, sticky="nse", padx=(8, 0))

        self._build_left(left)
        self._build_center(center)
        self._build_right(right)

    def _build_left(self, parent: ttk.Frame) -> None:
        ttk.Button(parent, text="打开 PDF", command=self.open_pdf).grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(parent, text="打开密码").grid(row=1, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.open_password_var, show="*").grid(row=2, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(parent, text="自动规则").grid(row=3, column=0, sticky="w")
        ttk.Checkbutton(parent, text="手机号", variable=self.mobile_var).grid(row=4, column=0, sticky="w")
        ttk.Checkbutton(parent, text="身份证", variable=self.id_card_var).grid(row=5, column=0, sticky="w")
        ttk.Checkbutton(parent, text="邮箱", variable=self.email_var).grid(row=6, column=0, sticky="w")
        ttk.Checkbutton(parent, text="银行卡", variable=self.bank_card_var).grid(row=7, column=0, sticky="w")
        ttk.Checkbutton(parent, text="统一社会信用代码", variable=self.uscc_var).grid(row=8, column=0, sticky="w")
        ttk.Label(parent, text="关键词，逗号分隔").grid(row=9, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(parent, textvariable=self.keyword_var).grid(row=10, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(parent, text="文本规则识别", command=self.auto_detect).grid(row=11, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(parent, text="扫描件 OCR 识别", command=self.ocr_detect).grid(row=12, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(parent, text="水印").grid(row=13, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.watermark_var).grid(row=14, column=0, sticky="ew", pady=(0, 8))
        ttk.Checkbutton(parent, text="安全压平输出", variable=self.flatten_var).grid(row=15, column=0, sticky="w")
        ttk.Checkbutton(parent, text="输出后 OCR 复查", variable=self.verify_ocr_var).grid(row=16, column=0, sticky="w", pady=(0, 12))

        ttk.Label(parent, text="权限密码").grid(row=17, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.owner_password_var, show="*").grid(row=18, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(parent, text="打开密码，可留空").grid(row=19, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.user_password_var, show="*").grid(row=20, column=0, sticky="ew", pady=(0, 8))
        ttk.Checkbutton(parent, text="允许打印", variable=self.allow_print_var).grid(row=21, column=0, sticky="w")
        ttk.Checkbutton(parent, text="允许复制", variable=self.allow_copy_var).grid(row=22, column=0, sticky="w")
        ttk.Checkbutton(parent, text="允许修改", variable=self.allow_modify_var).grid(row=23, column=0, sticky="w")

        ttk.Label(parent, text="输出文件").grid(row=24, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(parent, textvariable=self.output_var).grid(row=25, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(parent, text="选择输出", command=self.choose_output).grid(row=26, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(parent, text="执行处理", command=self.run_process).grid(row=27, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(parent, text="批量处理", command=self.run_batch_dialog).grid(row=28, column=0, sticky="ew")
        parent.columnconfigure(0, weight=1)

    def _build_center(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(toolbar, text="首页", command=self.first_page).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(toolbar, text="上一页", command=self.prev_page).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(toolbar, text="下一页", command=self.next_page).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(toolbar, text="末页", command=self.last_page).grid(row=0, column=3, padx=(0, 8))
        ttk.Entry(toolbar, width=5, textvariable=self.page_jump_var).grid(row=0, column=4, padx=(0, 4))
        ttk.Button(toolbar, text="跳转", command=self.jump_page).grid(row=0, column=5, padx=(0, 12))
        ttk.Button(toolbar, text="适合宽度", command=self.fit_width).grid(row=0, column=6, padx=(0, 4))
        ttk.Button(toolbar, text="适合整页", command=self.fit_page).grid(row=0, column=7, padx=(0, 4))
        ttk.Combobox(toolbar, width=7, textvariable=self.zoom_var, values=[f"{int(z * 100)}%" for z in ZOOM_PRESETS], state="readonly").grid(row=0, column=8, padx=(0, 4))
        ttk.Button(toolbar, text="应用缩放", command=self.apply_zoom_combo).grid(row=0, column=9, padx=(0, 12))
        self.page_label = ttk.Label(toolbar, text="0 / 0")
        self.page_label.grid(row=0, column=10, sticky="w")

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
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_mouse_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mouse_wheel)
        self.bind("<Delete>", lambda event: self.delete_selected_box())

        ttk.Label(parent, textvariable=self.status_var).grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def _build_right(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="脱敏区域").grid(row=0, column=0, sticky="w")
        self.box_list = tk.Listbox(parent, height=18, width=40)
        self.box_list.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        self.box_list.bind("<<ListboxSelect>>", self._on_box_list_select)
        ttk.Button(parent, text="删除选中", command=self.delete_selected_box).grid(row=2, column=0, sticky="ew", pady=(0, 8))

        output_buttons = ttk.Frame(parent)
        output_buttons.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        output_buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(output_buttons, text="打开输出文件", command=self.open_output_file).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(output_buttons, text="打开输出目录", command=self.open_output_dir).grid(row=0, column=1, sticky="ew")
        ttk.Button(parent, text="打开处理报告", command=self.open_report_file).grid(row=4, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(parent, text="处理报告").grid(row=5, column=0, sticky="w")
        self.report_text = tk.Text(parent, height=18, width=40)
        self.report_text.grid(row=6, column=0, sticky="nsew")
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(6, weight=1)

    def open_pdf(self) -> None:
        path = filedialog.askopenfilename(title="选择 PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self.input_path = Path(path)
        self.preview_path = self.input_path
        self.last_output_path = None
        self.last_report_path = None
        default_output = self.input_path.with_name(f"{self.input_path.stem}_guarded.pdf")
        self.output_var.set(str(default_output))
        self.page_index = 0
        self.boxes.clear()
        self.detections = []
        self._active_box_id = None
        self.render_current_page()

    def choose_output(self) -> None:
        path = filedialog.asksaveasfilename(title="输出 PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            self.output_var.set(path)

    def auto_detect(self) -> None:
        if not self.input_path:
            messagebox.showwarning("提示", "请先选择 PDF")
            return
        try:
            detections, boxes = detect_redactions(self.input_path, self._selected_rules(), self._keywords(), self._open_password())
        except Exception as exc:
            messagebox.showerror("自动识别失败", str(exc))
            return
        self.detections = detections
        self.boxes = [self._with_box_id(box) for box in boxes]
        self._active_box_id = self.boxes[0].id if self.boxes else None
        self._refresh_box_list()
        self.render_current_page()
        self.status_var.set(f"文本规则识别完成：{len(boxes)} 个可定位区域，{len(detections)} 个候选")

    def ocr_detect(self) -> None:
        if not self.input_path:
            messagebox.showwarning("提示", "请先选择 PDF")
            return
        provider = get_default_ocr_provider()
        if not provider.is_available():
            messagebox.showwarning("OCR 不可用", "当前版本未内置 PaddleOCR。请使用 OCR Full 版或在开发环境安装 OCR 依赖。")
            return
        try:
            candidates, boxes = detect_ocr_redaction_boxes(self.input_path, provider, self._open_password())
        except Exception as exc:
            messagebox.showerror("OCR 识别失败", str(exc))
            return
        self.boxes.extend(self._with_box_id(box) for box in boxes)
        if boxes:
            self._active_box_id = self.boxes[-len(boxes)].id
        self._refresh_box_list()
        self.render_current_page()
        self.status_var.set(f"OCR 识别完成：{len(candidates)} 个候选。姓名和地址请人工复核。")

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
            verify_ocr=self.verify_ocr_var.get(),
            permissions=PermissionOptions(
                allow_print=self.allow_print_var.get(),
                allow_copy=self.allow_copy_var.get(),
                allow_modify=self.allow_modify_var.get(),
            ),
        )
        try:
            report = process_pdf(options, self._selected_rules(), self._keywords())
            payload = process_report_to_dict(report)
            report_path = options.output_path.with_suffix(".report.json")
            report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            payload["report_path"] = str(report_path)
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
            self.last_output_path = output_path
            self.last_report_path = Path(payload["report_path"])
            self.preview_path = output_path
            self.page_index = min(self.page_index, max(int(payload["pages"]) - 1, 0))
            self.boxes.clear()
            self._active_box_id = None
            self._refresh_box_list()
            self.render_current_page()
            risk = payload["verification"]["risk_level"]
            self.status_var.set(f"处理完成，当前预览为输出 PDF，风险等级：{risk}")
            self.report_text.delete("1.0", tk.END)
            self.report_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))
            messagebox.showinfo("完成", "PDF 处理完成")
        elif kind == "batch_ok":
            self.last_output_path = Path(payload["output_dir"])
            self.last_report_path = self.last_output_path / "batch.report.json"
            self.status_var.set(f"批量完成：成功 {payload['success']}，失败 {payload['failed']}，取消 {payload['canceled']}")
            self.report_text.delete("1.0", tk.END)
            self.report_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))
            messagebox.showinfo("批量完成", "批量处理完成")
        else:
            self.status_var.set("处理失败")
            messagebox.showerror("处理失败", str(payload))
        self.after(150, self._poll_worker)

    def run_batch_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("批量处理")
        dialog.transient(self)
        dialog.grab_set()
        mode_var = tk.StringVar(value="files")
        recursive_var = tk.BooleanVar(value=False)
        enable_ocr_var = tk.BooleanVar(value=False)
        result: dict[str, object] = {}

        ttk.Radiobutton(dialog, text="选择多个 PDF 文件", variable=mode_var, value="files").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        ttk.Radiobutton(dialog, text="选择 PDF 文件夹", variable=mode_var, value="folder").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        ttk.Checkbutton(dialog, text="递归扫描子文件夹", variable=recursive_var).grid(row=2, column=0, sticky="w", padx=12, pady=4)
        ttk.Checkbutton(dialog, text="启用 OCR 批量识别", variable=enable_ocr_var).grid(row=3, column=0, sticky="w", padx=12, pady=4)

        def submit() -> None:
            result["mode"] = mode_var.get()
            result["recursive"] = recursive_var.get()
            result["enable_ocr"] = enable_ocr_var.get()
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        buttons = ttk.Frame(dialog)
        buttons.grid(row=4, column=0, sticky="ew", padx=12, pady=12)
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(buttons, text="继续", command=submit).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="取消", command=cancel).grid(row=0, column=1, sticky="ew")
        self.wait_window(dialog)
        if not result:
            return
        if result["mode"] == "files":
            paths = filedialog.askopenfilenames(title="选择多个 PDF", filetypes=[("PDF", "*.pdf")])
            if not paths:
                return
            inputs = [Path(path) for path in paths]
        else:
            folder = filedialog.askdirectory(title="选择 PDF 文件夹")
            if not folder:
                return
            inputs = [Path(folder)]
        output_dir = filedialog.askdirectory(title="选择批量输出目录")
        if not output_dir:
            return
        if not self.owner_password_var.get().strip():
            messagebox.showwarning("提示", "请先设置权限密码")
            return
        self.status_var.set("批量处理中...")
        thread = threading.Thread(
            target=self._batch_worker,
            args=(inputs, Path(output_dir), bool(result["recursive"]), bool(result["enable_ocr"])),
            daemon=True,
        )
        thread.start()

    def _batch_worker(self, inputs: list[Path], output_dir: Path, recursive: bool, enable_ocr: bool) -> None:
        process_options = ProcessOptions(
            input_path=Path("__batch_placeholder__.pdf"),
            output_path=output_dir / "__batch_placeholder__.pdf",
            open_password=self._open_password(),
            owner_password=self.owner_password_var.get().strip(),
            user_password=self.user_password_var.get(),
            boxes=[],
            watermark=WatermarkOptions(text=self.watermark_var.get()),
            flatten=self.flatten_var.get(),
            flatten_dpi=200,
            verify_ocr=self.verify_ocr_var.get(),
            permissions=PermissionOptions(
                allow_print=self.allow_print_var.get(),
                allow_copy=self.allow_copy_var.get(),
                allow_modify=self.allow_modify_var.get(),
            ),
        )
        options = BatchOptions(
            input_paths=inputs,
            output_dir=output_dir,
            process_options=process_options,
            rules=self._selected_rules(),
            keywords=self._keywords(),
            recursive=recursive,
            enable_ocr=enable_ocr,
            continue_on_error=True,
        )
        try:
            report = BatchRunner(options).run()
            payload = {
                "total": report.total,
                "success": report.success,
                "failed": report.failed,
                "canceled": report.canceled,
                "output_dir": str(output_dir),
            }
            self._worker_queue.put(("batch_ok", payload))
        except Exception as exc:
            self._worker_queue.put(("error", str(exc)))

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
        self.page_jump_var.set(str(self.page_index + 1))
        self.zoom_var.set(f"{int(round(self.zoom * 100))}%")
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self.canvas.configure(scrollregion=(0, 0, image.width, image.height))
        self.page_label.configure(text=f"{self.page_index + 1} / {self.page_count}")
        self._draw_boxes()

    def _draw_boxes(self) -> None:
        for box in self.boxes:
            if box.page_index != self.page_index:
                continue
            x0, y0, x1, y1 = pdf_to_canvas_rect(box.rect, self.zoom)
            color = "#d62728" if box.source == "auto" else ("#ff7f0e" if box.source == "ocr" else "#1f77b4")
            width = 3 if box.id == self._active_box_id else 2
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=width, tags=("box", box.id))
            if box.id == self._active_box_id:
                for hx, hy in self._handle_points((x0, y0, x1, y1)).values():
                    half = HANDLE_SIZE / 2
                    self.canvas.create_rectangle(hx - half, hy - half, hx + half, hy + half, fill="#ffffff", outline="#111111", tags=("handle", box.id))

    def _on_mouse_down(self, event) -> None:
        if not self.preview_path or self.preview_path != self.input_path:
            return
        point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        hit = self._hit_test(point)
        self._drag_start = point
        self._drag_mode = None
        self._drag_original_rect = None
        if hit:
            box_id, mode = hit
            self._active_box_id = box_id
            self._drag_mode = mode
            box = self._find_box(box_id)
            self._drag_original_rect = box.rect if box else None
            self._refresh_box_list()
            self.render_current_page()
            return
        self._active_box_id = None
        if self._draw_rect_id:
            self.canvas.delete(self._draw_rect_id)
        x, y = point
        self._draw_rect_id = self.canvas.create_rectangle(x, y, x, y, outline="#1f77b4", width=2, dash=(4, 3))

    def _on_mouse_drag(self, event) -> None:
        if self._drag_start is None:
            return
        point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if self._drag_mode and self._active_box_id and self._drag_original_rect:
            self._update_active_box(point)
            self.render_current_page()
            return
        if self._draw_rect_id is not None:
            x0, y0 = self._drag_start
            x1, y1 = point
            self.canvas.coords(self._draw_rect_id, x0, y0, x1, y1)

    def _on_mouse_up(self, event) -> None:
        if self._drag_start is None:
            return
        point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if self._drag_mode:
            self._drag_start = None
            self._drag_mode = None
            self._drag_original_rect = None
            self._refresh_box_list()
            self.render_current_page()
            return
        rect = canvas_to_pdf_rect(self._drag_start, point, self.zoom)
        self._drag_start = None
        if self._draw_rect_id:
            self.canvas.delete(self._draw_rect_id)
            self._draw_rect_id = None
        if abs(rect[2] - rect[0]) < MIN_BOX_POINTS or abs(rect[3] - rect[1]) < MIN_BOX_POINTS:
            self.render_current_page()
            return
        box = self._with_box_id(
            RedactionBox(
                page_index=self.page_index,
                rect=self._clamp_rect(rect),
                source="manual",
                category="manual",
                label="手动框选",
            )
        )
        self.boxes.append(box)
        self._active_box_id = box.id
        self._refresh_box_list()
        self.render_current_page()

    def _on_right_click(self, event) -> None:
        hit = self._hit_test((self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)))
        if hit:
            self._active_box_id = hit[0]
            self._refresh_box_list()
            self.render_current_page()
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="删除选中框", command=self.delete_selected_box)
        menu.tk_popup(event.x_root, event.y_root)

    def _on_mouse_wheel(self, event) -> None:
        self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def _on_shift_mouse_wheel(self, event) -> None:
        self.canvas.xview_scroll(-1 * int(event.delta / 120), "units")

    def _on_ctrl_mouse_wheel(self, event) -> None:
        factor = 1.1 if event.delta > 0 else 0.9
        self.set_zoom(self.zoom * factor)

    def _on_box_list_select(self, event) -> None:
        selection = self.box_list.curselection()
        if not selection:
            return
        visible_boxes = self._listed_boxes()
        index = selection[0]
        if 0 <= index < len(visible_boxes):
            self._active_box_id = visible_boxes[index].id
            self.page_index = visible_boxes[index].page_index
            self.render_current_page()

    def delete_selected_box(self) -> None:
        if not self._active_box_id:
            selection = self.box_list.curselection()
            listed = self._listed_boxes()
            if selection and 0 <= selection[0] < len(listed):
                self._active_box_id = listed[selection[0]].id
        if not self._active_box_id:
            return
        self.boxes = [box for box in self.boxes if box.id != self._active_box_id]
        self._active_box_id = None
        self._refresh_box_list()
        self.render_current_page()

    def first_page(self) -> None:
        if self.page_count:
            self.page_index = 0
            self.render_current_page()

    def prev_page(self) -> None:
        if self.page_index > 0:
            self.page_index -= 1
            self.render_current_page()

    def next_page(self) -> None:
        if self.page_index + 1 < self.page_count:
            self.page_index += 1
            self.render_current_page()

    def last_page(self) -> None:
        if self.page_count:
            self.page_index = self.page_count - 1
            self.render_current_page()

    def jump_page(self) -> None:
        try:
            page = int(self.page_jump_var.get())
        except ValueError:
            return
        if self.page_count:
            self.page_index = max(0, min(self.page_count - 1, page - 1))
            self.render_current_page()

    def apply_zoom_combo(self) -> None:
        value = self.zoom_var.get().strip().rstrip("%")
        try:
            self.set_zoom(float(value) / 100.0)
        except ValueError:
            pass

    def set_zoom(self, value: float) -> None:
        self.zoom = max(0.25, min(3.0, value))
        self.render_current_page()

    def fit_width(self) -> None:
        if not self.page_size:
            return
        width = self.page_size[0]
        canvas_width = max(self.canvas.winfo_width() - 24, 100)
        self.set_zoom(canvas_width / width)

    def fit_page(self) -> None:
        if not self.page_size:
            return
        width, height = self.page_size
        canvas_width = max(self.canvas.winfo_width() - 24, 100)
        canvas_height = max(self.canvas.winfo_height() - 24, 100)
        self.set_zoom(min(canvas_width / width, canvas_height / height))

    def open_output_file(self) -> None:
        if self.last_output_path and self.last_output_path.is_file():
            os.startfile(self.last_output_path)
        else:
            messagebox.showinfo("提示", "还没有可打开的输出文件")

    def open_output_dir(self) -> None:
        target = self.last_output_path.parent if self.last_output_path else (Path(self.output_var.get()).parent if self.output_var.get() else None)
        if target and target.exists():
            os.startfile(target)
        else:
            messagebox.showinfo("提示", "还没有可打开的输出目录")

    def open_report_file(self) -> None:
        if self.last_report_path and self.last_report_path.exists():
            os.startfile(self.last_report_path)
        else:
            messagebox.showinfo("提示", "还没有可打开的处理报告")

    def _update_active_box(self, point: tuple[float, float]) -> None:
        if not self._active_box_id or not self._drag_start or not self._drag_original_rect or not self._drag_mode:
            return
        dx = (point[0] - self._drag_start[0]) / self.zoom
        dy = (point[1] - self._drag_start[1]) / self.zoom
        x0, y0, x1, y1 = self._drag_original_rect
        mode = self._drag_mode
        if mode == "move":
            rect = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
        else:
            left, top, right, bottom = x0, y0, x1, y1
            if "w" in mode:
                left += dx
            if "e" in mode:
                right += dx
            if "n" in mode:
                top += dy
            if "s" in mode:
                bottom += dy
            rect = _normalize_rect((left, top, right, bottom))
        rect = self._clamp_rect(rect)
        self.boxes = [_replace_box_rect(box, rect) if box.id == self._active_box_id else box for box in self.boxes]

    def _hit_test(self, point: tuple[float, float]) -> tuple[str, str] | None:
        x, y = point
        for box in reversed(self.boxes):
            if box.page_index != self.page_index:
                continue
            rect_canvas = pdf_to_canvas_rect(box.rect, self.zoom)
            for name, handle_point in self._handle_points(rect_canvas).items():
                hx, hy = handle_point
                if abs(x - hx) <= HANDLE_SIZE and abs(y - hy) <= HANDLE_SIZE:
                    return box.id, name
            x0, y0, x1, y1 = rect_canvas
            if x0 <= x <= x1 and y0 <= y <= y1:
                return box.id, "move"
        return None

    def _handle_points(self, rect: tuple[float, float, float, float]) -> dict[str, tuple[float, float]]:
        x0, y0, x1, y1 = rect
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2
        return {
            "nw": (x0, y0),
            "n": (mx, y0),
            "ne": (x1, y0),
            "e": (x1, my),
            "se": (x1, y1),
            "s": (mx, y1),
            "sw": (x0, y1),
            "w": (x0, my),
        }

    def _clamp_rect(self, rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        x0, y0, x1, y1 = _normalize_rect(rect)
        page_width, page_height = self.page_size
        x0 = max(0, min(page_width, x0))
        x1 = max(0, min(page_width, x1))
        y0 = max(0, min(page_height, y0))
        y1 = max(0, min(page_height, y1))
        if x1 - x0 < MIN_BOX_POINTS:
            x1 = min(page_width, x0 + MIN_BOX_POINTS)
        if y1 - y0 < MIN_BOX_POINTS:
            y1 = min(page_height, y0 + MIN_BOX_POINTS)
        return (x0, y0, x1, y1)

    def _with_box_id(self, box: RedactionBox) -> RedactionBox:
        if box.id:
            return box
        self._box_seq += 1
        return RedactionBox(
            page_index=box.page_index,
            rect=box.rect,
            source=box.source,
            category=box.category,
            label=box.label,
            confidence=box.confidence,
            id=f"box-{self._box_seq}",
            confirmed=box.confirmed,
        )

    def _find_box(self, box_id: str) -> RedactionBox | None:
        return next((box for box in self.boxes if box.id == box_id), None)

    def _listed_boxes(self) -> list[RedactionBox]:
        return list(self.boxes)

    def _refresh_box_list(self) -> None:
        self.box_list.delete(0, tk.END)
        for index, box in enumerate(self._listed_boxes(), start=1):
            marker = "*" if box.id == self._active_box_id else " "
            confirm = "已确认" if box.confirmed else "待确认"
            self.box_list.insert(tk.END, f"{marker}{index}. 第 {box.page_index + 1} 页 {box.category} {box.source} {confirm} {box.confidence:.2f}")

    def _selected_rules(self):
        return selected_rules(
            redact_mobile=self.mobile_var.get(),
            redact_id_card=self.id_card_var.get(),
            redact_email=self.email_var.get(),
            redact_bank_card=self.bank_card_var.get(),
            redact_uscc=self.uscc_var.get(),
        )

    def _keywords(self) -> list[str]:
        return [part.strip() for part in self.keyword_var.get().replace("，", ",").split(",") if part.strip()]

    def _open_password(self) -> str | None:
        value = self.open_password_var.get()
        return value if value else None


def _normalize_rect(rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = rect
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _replace_box_rect(box: RedactionBox, rect: tuple[float, float, float, float]) -> RedactionBox:
    return RedactionBox(
        page_index=box.page_index,
        rect=rect,
        source=box.source,
        category=box.category,
        label=box.label,
        confidence=box.confidence,
        id=box.id,
        confirmed=box.confirmed,
    )


def main() -> int:
    app = LocalPDFGuardApp()
    app.mainloop()
    return 0
