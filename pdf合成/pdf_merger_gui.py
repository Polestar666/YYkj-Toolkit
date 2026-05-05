from __future__ import annotations

from importlib import import_module
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def _load_pdf_backend() -> tuple[type | None, type | None]:
    try:
        module = import_module("pypdf")
    except ImportError:
        return None, None
    return getattr(module, "PdfReader", None), getattr(module, "PdfWriter", None)


def _load_dnd_backend() -> tuple[str | None, type | None]:
    try:
        module = import_module("tkinterdnd2")
    except ImportError:
        return None, None
    return getattr(module, "DND_FILES", None), getattr(module, "TkinterDnD", None)


PdfReader, PdfWriter = _load_pdf_backend()
DND_FILES, TkinterDnD = _load_dnd_backend()


class PDFMergerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF 合并工具")
        self.root.geometry("760x520")
        self.root.minsize(680, 480)

        self.files: list[Path] = []
        self.output_path = tk.StringVar()
        self.status_text = tk.StringVar()

        self._build_ui()
        self._set_ready_status()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        title = ttk.Label(container, text="PDF 合并工具", font=("Microsoft YaHei UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            container,
            text="支持拖拽添加 PDF、选择单个文件、选择文件夹批量导入。",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(6, 12))

        content = ttk.Frame(container)
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(content, text="待合并文件", padding=12)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)

        tip_text = "可将 PDF 文件直接拖拽到下方列表中。"
        if not self._drag_drop_enabled:
            tip_text = "当前未启用拖拽：请安装 tkinterdnd2（pip install tkinterdnd2）后重启。"

        tip_label = ttk.Label(list_frame, text=tip_text, foreground="#666666")
        tip_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            activestyle="dotbox",
            font=("Microsoft YaHei UI", 10),
        )
        self.file_listbox.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        action_frame = ttk.Frame(content, padding=(12, 0, 0, 0))
        action_frame.grid(row=0, column=1, sticky="ns")

        buttons = [
            ("添加文件", self.add_files),
            ("选择文件夹", self.add_folder),
            ("上移", self.move_up),
            ("下移", self.move_down),
            ("移除选中", self.remove_selected),
            ("清空列表", self.clear_files),
        ]

        for row, (text, command) in enumerate(buttons):
            ttk.Button(action_frame, text=text, command=command, width=14).grid(
                row=row,
                column=0,
                sticky="ew",
                pady=(0, 8),
            )

        output_frame = ttk.LabelFrame(container, text="输出文件", padding=12)
        output_frame.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        output_frame.columnconfigure(0, weight=1)

        output_entry = ttk.Entry(output_frame, textvariable=self.output_path)
        output_entry.grid(row=0, column=0, sticky="ew")

        ttk.Button(output_frame, text="选择保存位置", command=self.choose_output).grid(
            row=0,
            column=1,
            padx=(10, 0),
        )

        bottom_frame = ttk.Frame(container)
        bottom_frame.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        bottom_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_text, foreground="#1f4f82")
        self.status_label.grid(row=0, column=0, sticky="w")

        ttk.Button(bottom_frame, text="开始合并", command=self.merge_pdfs).grid(row=0, column=1, padx=(10, 0))

        if self._drag_drop_enabled:
            self._register_drop_target()

    @property
    def _drag_drop_enabled(self) -> bool:
        return TkinterDnD is not None and DND_FILES is not None

    def _set_ready_status(self) -> None:
        merge_dep = "已检测到 pypdf" if PdfWriter is not None else "未检测到 pypdf（合并前请先安装）"
        drag_dep = "拖拽可用" if self._drag_drop_enabled else "拖拽未启用"
        self.status_text.set(f"{merge_dep}；{drag_dep}。当前文件数：{len(self.files)}")

    def _refresh_listbox(self) -> None:
        self.file_listbox.delete(0, tk.END)
        for index, file_path in enumerate(self.files, start=1):
            self.file_listbox.insert(tk.END, f"{index:02d}. {file_path}")
        self._set_ready_status()

    def _add_paths(self, paths: list[Path]) -> None:
        added_count = 0
        existing = {path.resolve() for path in self.files}
        for path in paths:
            if not path.exists() or path.suffix.lower() != ".pdf":
                continue
            resolved = path.resolve()
            if resolved in existing:
                continue
            self.files.append(path)
            existing.add(resolved)
            added_count += 1

        self._refresh_listbox()
        if added_count:
            self.status_text.set(f"已添加 {added_count} 个 PDF。当前文件数：{len(self.files)}")
        else:
            self.status_text.set("没有新增 PDF 文件。")

    def add_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf")],
        )
        if not selected:
            return
        self._add_paths([Path(item) for item in selected])

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择包含 PDF 的文件夹")
        if not folder:
            return

        pdfs = sorted(Path(folder).glob("*.pdf"), key=lambda item: item.name.lower())
        self._add_paths(pdfs)

    def remove_selected(self) -> None:
        selected = list(self.file_listbox.curselection())
        if not selected:
            return

        for index in reversed(selected):
            self.files.pop(index)
        self._refresh_listbox()
        self.status_text.set(f"已移除 {len(selected)} 个文件。当前文件数：{len(self.files)}")

    def clear_files(self) -> None:
        if not self.files:
            return
        self.files.clear()
        self._refresh_listbox()
        self.status_text.set("文件列表已清空。")

    def move_up(self) -> None:
        selected = list(self.file_listbox.curselection())
        if not selected or selected[0] == 0:
            return

        for index in selected:
            self.files[index - 1], self.files[index] = self.files[index], self.files[index - 1]
        self._refresh_listbox()
        for index in [item - 1 for item in selected]:
            self.file_listbox.selection_set(index)
        self.status_text.set("已上移选中文件。")

    def move_down(self) -> None:
        selected = list(self.file_listbox.curselection())
        if not selected or selected[-1] == len(self.files) - 1:
            return

        for index in reversed(selected):
            self.files[index + 1], self.files[index] = self.files[index], self.files[index + 1]
        self._refresh_listbox()
        for index in [item + 1 for item in selected]:
            self.file_listbox.selection_set(index)
        self.status_text.set("已下移选中文件。")

    def choose_output(self) -> None:
        output = filedialog.asksaveasfilename(
            title="保存合并后的 PDF",
            defaultextension=".pdf",
            filetypes=[("PDF 文件", "*.pdf")],
            initialfile="merged.pdf",
        )
        if not output:
            return
        self.output_path.set(output)
        self.status_text.set(f"输出文件：{output}")

    def merge_pdfs(self) -> None:
        if PdfWriter is None or PdfReader is None:
            messagebox.showerror(
                "缺少依赖",
                "当前环境未安装 pypdf，无法执行合并。\n请先运行：pip install pypdf",
            )
            return

        if not self.files:
            messagebox.showwarning("没有文件", "请先添加至少一个 PDF 文件。")
            return

        output = self.output_path.get().strip()
        if not output:
            suggested = self._default_output_path()
            self.output_path.set(str(suggested))
            output = str(suggested)

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        writer = PdfWriter()
        try:
            for file_path in self.files:
                reader = PdfReader(str(file_path))
                for page in reader.pages:
                    writer.add_page(page)

            with output_path.open("wb") as target:
                writer.write(target)
        except Exception as exc:
            messagebox.showerror("合并失败", f"处理 PDF 时出错：\n{exc}")
            self.status_text.set("合并失败，请检查文件是否损坏或被占用。")
            return

        messagebox.showinfo("合并完成", f"PDF 已成功合并到：\n{output_path}")
        self.status_text.set(f"合并完成：{output_path}")

    def _default_output_path(self) -> Path:
        first_file = self.files[0]
        return first_file.with_name(f"{first_file.stem}_merged.pdf")

    def _register_drop_target(self) -> None:
        register = getattr(self.file_listbox, "drop_target_register", None)
        bind = getattr(self.file_listbox, "dnd_bind", None)
        if callable(register) and callable(bind) and DND_FILES is not None:
            register(DND_FILES)
            bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event: object) -> None:
        data = getattr(event, "data", "")
        if not isinstance(data, str) or not data:
            return
        dropped = [Path(item) for item in self.root.tk.splitlist(data)]
        self._add_paths(dropped)


def create_root() -> tk.Tk:
    if TkinterDnD is not None:
        return TkinterDnD.Tk()
    return tk.Tk()


def main() -> None:
    root = create_root()
    app = PDFMergerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
