from __future__ import annotations

__version__ = "0.1.0"

import sys
import logging
import traceback
from pathlib import Path
from tkinter import (
    BooleanVar,
    Checkbutton,
    Entry,
    Label,
    scrolledtext,
    Spinbox,
    StringVar,
    Tk,
    ttk,
)
from tkinter.filedialog import askdirectory

if __name__ == "__main__":
    src_dir = Path(__file__).resolve().parent
    if src_dir.parent not in sys.path:
        sys.path.insert(0, str(src_dir.parent))

import threading

from src import config, db, ollama_ocr, processor


_log_file = Path(__file__).resolve().parent.parent / "photos_to_obsidian.log"
logger = logging.getLogger(__name__)


def _setup_style() -> None:
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass

    s.configure("Run.TButton", padding=(14, 6), font=("Segoe UI", 9, "bold"))
    s.configure("Action.TButton", padding=(10, 4))

    s.map(
        "Run.TButton",
        background=[("active", "#217346"), ("!active", "#107c10")],
        foreground=[("!active", "white"), ("active", "white")],
    )
    s.map(
        "Stop.TButton",
        background=[("active", "#c62828"), ("!active", "#d32f2f")],
        foreground=[("!active", "white"), ("active", "white")],
    )


def _row(parent, label_text: str, row: int):
    lbl = Label(parent, text=label_text, font=("Segoe UI", 9), anchor="w", width=16)
    lbl.pack(in_=parent, side="left", padx=(0, 4), pady=3)
    return lbl


class SectionHeader(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        sep = ttk.Separator(self)
        sep.pack(fill="x", pady=(0, 4))
        self.pack(fill="x")


class SettingsTab(ttk.Frame):
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui

        col = ttk.Frame(self)
        col.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)

        row = ttk.Frame(col)
        row.pack(fill="x")
        SectionHeader(row)
        ttk.Label(col, text="Source Folder", font=("Segoe UI", 9, "bold")).pack(
            in_=row, anchor="w", pady=(2, 0)
        )

        src_row = ttk.Frame(col)
        src_row.pack(fill="x", pady=2)
        gui.source_folder_var = StringVar()
        ttk.Entry(
            src_row, textvariable=gui.source_folder_var, font=("Segoe UI", 9), width=38
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(src_row, text="Browse", command=gui._browse_source_folder).pack(side="left", padx=(4, 0))

        vault_row = ttk.Frame(col)
        vault_row.pack(fill="x", pady=2)
        ttk.Label(col, text="Obsidian Vault", font=("Segoe UI", 9, "bold")).pack(
            in_=vault_row, anchor="w", pady=(8, 0)
        )

        vault_entry_row = ttk.Frame(col)
        vault_entry_row.pack(fill="x", pady=2)
        gui.obsidian_vault_var = StringVar()
        ttk.Entry(
            vault_entry_row, textvariable=gui.obsidian_vault_var, font=("Segoe UI", 9), width=38
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(vault_entry_row, text="Browse", command=gui._browse_obsidian_vault).pack(
            side="left", padx=(4, 0)
        )

        ttk.Label(col, text="OCR Language", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        lang_row = ttk.Frame(col)
        lang_row.pack(fill="x", pady=2)
        gui.ocr_language_var = StringVar()
        ttk.Entry(
            lang_row, textvariable=gui.ocr_language_var, font=("Segoe UI", 9), width=18
        ).pack(side="left")
        ttk.Label(
            lang_row, text='e.g. "eng+spa"', font=("Segoe UI", 8), foreground="#888"
        ).pack(side="left", padx=(6, 0))

        ttk.Label(col, text="Confidence Threshold", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 0)
        )
        conf_row = ttk.Frame(col)
        conf_row.pack(fill="x", pady=2)
        gui.confidence_var = StringVar()
        Spinbox(
            conf_row, from_=0, to=100, textvariable=gui.confidence_var, width=19,
            font=("Segoe UI", 9)
        ).pack(side="left")
        ttk.Label(conf_row, text="%  (0–100)", font=("Segoe UI", 8), foreground="#888").pack(
            side="left", padx=(6, 0)
        )

        gui.embed_image_var = BooleanVar()
        Checkbutton(
            col,
            text="Embed image in note (![[...]])",
            variable=gui.embed_image_var,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(8, 0))

        ttk.Separator(col, orient="horizontal").pack(fill="x", pady=(8, 0))
        ttk.Button(
            col,
            text="Save Settings",
            style="Action.TButton",
            command=gui._save_settings,
        ).pack(pady=(4, 0))

        preview_col = ttk.Frame(self)
        preview_col.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        ttk.Label(
            preview_col,
            text="Preview",
            font=("Segoe UI", 9, "bold"),
            foreground="#555",
        ).pack(anchor="w", pady=(0, 6))

        prev_sep = ttk.Separator(preview_col, orient="horizontal")
        prev_sep.pack(fill="x", pady=(0, 8))

        gui.preview_text = scrolledtext.ScrolledText(
            preview_col,
            height=18,
            wrap="word",
            state="disabled",
            font=("Cascadia Code", 9),
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="#d4d4d4",
            relief="flat",
            borderwidth=0,
        )
        gui.preview_text.pack(fill="both", expand=True)


class ModelsTab(ttk.Frame):
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui

        body = ttk.Frame(self)
        body.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        SectionHeader(body)
        ttk.Label(body, text="Ollama Base URL", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(2, 0)
        )

        url_row = ttk.Frame(body)
        url_row.pack(fill="x", pady=2)
        gui.ollama_base_url_var = StringVar()
        ttk.Entry(
            url_row, textvariable=gui.ollama_base_url_var, width=40,
            font=("Segoe UI", 9)
        ).pack(side="left", fill="x", expand=True)

        ttk.Label(body, text="Timeout (seconds)", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 0)
        )
        timeout_row = ttk.Frame(body)
        timeout_row.pack(fill="x", pady=2)
        gui.ollama_timeout_var = StringVar()
        Spinbox(
            timeout_row, from_=10, to=300, textvariable=gui.ollama_timeout_var,
            width=18, font=("Segoe UI", 9)
        ).pack(side="left")
        ttk.Label(timeout_row, text="sec", font=("Segoe UI", 8), foreground="#888").pack(
            side="left", padx=(6, 0)
        )

        SectionHeader(body)
        ttk.Label(body, text="Vision Model", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(2, 0)
        )

        model_row = ttk.Frame(body)
        model_row.pack(fill="x", pady=2)
        gui.ollama_model_var = StringVar()
        gui.ollama_model_combo = ttk.Combobox(
            model_row,
            textvariable=gui.ollama_model_var,
            width=36,
            font=("Segoe UI", 9),
            state="readonly",
        )
        gui.ollama_model_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(model_row, text="Refresh", command=gui._refresh_models).pack(
            side="left", padx=(4, 0)
        )

        ttk.Label(body, text="Status", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 0)
        )
        gui.ollama_status_label = ttk.Label(
            body, text="checking...", font=("Segoe UI", 9)
        )
        gui.ollama_status_label.pack(anchor="w")

        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=(8, 0))
        btn_row = ttk.Frame(body)
        btn_row.pack(pady=(4, 0))
        ttk.Button(
            btn_row, text="Save Ollama Settings", style="Action.TButton",
            command=gui._save_ollama_settings
        ).pack()


class HistoryTab(ttk.Frame):
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        btn_row = ttk.Frame(body)
        btn_row.pack(fill="x", pady=(0, 6))
        ttk.Button(
            btn_row, text="Refresh", style="Action.TButton", command=gui._refresh_history
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            btn_row, text="Clear Success", style="Action.TButton",
            command=gui._clear_history
        ).pack(side="left", padx=(0, 4))

        col_row = ttk.Frame(body)
        col_row.pack(fill="both", expand=True)

        columns = ("file_name", "status", "tries", "engine", "last_tried")
        gui.history_tree = ttk.Treeview(
            col_row,
            columns=columns,
            show="headings",
            height=20,
            style="Treeview",
        )

        gui.history_tree.heading("file_name", text="Filename")
        gui.history_tree.heading("status", text="Status")
        gui.history_tree.heading("tries", text="Tries")
        gui.history_tree.heading("engine", text="Engine")
        gui.history_tree.heading("last_tried", text="Last Tried")

        gui.history_tree.column("file_name", width=180)
        gui.history_tree.column("status", width=80)
        gui.history_tree.column("tries", width=50)
        gui.history_tree.column("engine", width=90)
        gui.history_tree.column("last_tried", width=170)

        gui.history_tree.tag_configure("success", background="#e8f5e9")
        gui.history_tree.tag_configure("failed", background="#ffebee")

        vsb = ttk.Scrollbar(col_row, orient="vertical", command=gui.history_tree.yview)
        gui.history_tree.configure(yscrollcommand=vsb.set)

        gui.history_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")


class GUI:
    def __init__(self):
        self.root = Tk()
        self.root.title(f"PhotosToObsidian v{__version__}")

        _setup_style()
        style = ttk.Style()

        self.cfg = config.load_config()
        self._processor = None

        header = ttk.Frame(self.root, height=36)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        ttk.Label(
            header, text="PhotosToObsidian", font=("Segoe UI", 13, "bold"), foreground="#107c10"
        ).pack(side="left", padx=10, pady=6)

        ttk.Label(
            header, text=f"v{__version__}", font=("Segoe UI", 8), foreground="#aaa"
        ).pack(side="left", pady=10)

        ttk.Separator(header, orient="horizontal").pack(side="bottom", fill="x")

        toolbar = ttk.Frame(header)
        toolbar.pack(side="right", padx=8, pady=4)

        self.run_btn = ttk.Button(
            toolbar, text="▶  Run", style="Run.TButton", command=self._on_run
        )
        self.run_btn.pack(side="left", padx=(0, 4))

        self.stop_btn = ttk.Button(
            toolbar, text="■  Stop", style="Stop.TButton", command=self._on_stop, state="disabled"
        )
        self.stop_btn.pack(side="left")

        ttk.Separator(header, orient="horizontal").pack(side="bottom", fill="x")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=5)

        self.settings_tab = SettingsTab(self.notebook, self)
        self.notebook.add(self.settings_tab, text="Settings")

        self.models_tab = ModelsTab(self.notebook, self)
        self.notebook.add(self.models_tab, text="AI / Models")

        self.history_tab = HistoryTab(self.notebook, self)
        self.notebook.add(self.history_tab, text="History")

        status_frame = ttk.Frame(self.root)
        status_frame.pack(side="bottom", fill="x", padx=8, pady=(0, 5))

        ttk.Separator(status_frame).pack(side="top", fill="x")

        self.progress_log = scrolledtext.ScrolledText(
            status_frame,
            height=7,
            wrap="word",
            state="disabled",
            font=("Cascadia Code", 9),
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="#d4d4d4",
            relief="flat",
            borderwidth=0,
        )
        self.progress_log.pack(fill="both", expand=True, pady=(4, 0))

        self.stats_label = ttk.Label(
            status_frame, text="Ready  —  no run yet", font=("Segoe UI", 8), foreground="#777"
        )
        self.stats_label.pack(anchor="e", padx=2, pady=(0, 2))

        self._populate_from_config()
        self._refresh_history()
        self._check_ollama_status()

    def _populate_from_config(self) -> None:
        self.source_folder_var.set(str(self.cfg.source_folder))
        self.obsidian_vault_var.set(str(self.cfg.obsidian_vault))
        self.ocr_language_var.set(self.cfg.ocr_language)
        self.confidence_var.set(str(self.cfg.ocr_confidence_threshold))
        self.embed_image_var.set(self.cfg.note_embed_image)
        self.ollama_base_url_var.set(self.cfg.ollama_base_url)
        self.ollama_model_var.set(self.cfg.ollama_model)
        self.ollama_timeout_var.set(str(self.cfg.ollama_timeout))

    def _browse_source_folder(self) -> None:
        path = askdirectory(title="Select Source Folder")
        if path:
            self.source_folder_var.set(path)

    def _browse_obsidian_vault(self) -> None:
        path = askdirectory(title="Select Obsidian Vault")
        if path:
            self.obsidian_vault_var.set(path)

    def _save_settings(self) -> None:
        try:
            self.cfg.source_folder = Path(self.source_folder_var.get())
            self.cfg.obsidian_vault = Path(self.obsidian_vault_var.get())
            self.cfg.ocr_language = self.ocr_language_var.get()
            self.cfg.ocr_confidence_threshold = int(self.confidence_var.get())
            self.cfg.note_embed_image = bool(self.embed_image_var.get())

            config.save_config(self.cfg)
            self._log("Settings saved.")
        except Exception as e:
            self._log(f"Error: {e}")

    def _save_ollama_settings(self) -> None:
        try:
            self.cfg.ollama_base_url = self.ollama_base_url_var.get()
            self.cfg.ollama_model = self.ollama_model_var.get()
            self.cfg.ollama_timeout = int(self.ollama_timeout_var.get())

            config.save_config(self.cfg)
            self._log("Ollama settings saved.")
        except Exception as e:
            self._log(f"Error: {e}")

    def _refresh_models(self) -> None:
        self._log("Checking Ollama models...")
        models = ollama_ocr.get_available_models(base_url=self.ollama_base_url_var.get())
        if models:
            self.ollama_model_combo["values"] = models
            if self.ollama_model_var.get() not in models:
                self.ollama_model_var.set(models[0])
            self._log(f"Vision models: {', '.join(models)}")
        else:
            self.ollama_model_combo["values"] = []
            self._log("No vision models. Try: ollama pull llava")

    def _check_ollama_status(self) -> None:
        if ollama_ocr.ollama_available():
            self.ollama_status_label.configure(text="✓  Ollama found on PATH", foreground="#2e7d32")
        else:
            self.ollama_status_label.configure(text="✗  Ollama not found", foreground="#c62828")

    def _refresh_history(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        records = db.get_all_records()
        for record in records:
            status = record.get("status", "")
            tags = [status] if status in ("success", "failed") else []
            self.history_tree.insert(
                "",
                "end",
                tags=tags,
                values=(
                    record.get("file_name", ""),
                    status,
                    record.get("tries", ""),
                    record.get("ocr_engine_used", ""),
                    record.get("last_tried_at", ""),
                ),
            )

    def _clear_history(self) -> None:
        db.clear_success_records()
        self._refresh_history()
        self._log("Cleared success records.")

    def _on_run(self) -> None:
        self.cfg.source_folder = Path(self.source_folder_var.get())
        self.cfg.obsidian_vault = Path(self.obsidian_vault_var.get())
        self.cfg.ocr_language = self.ocr_language_var.get()
        self.cfg.ocr_confidence_threshold = int(self.confidence_var.get())
        self.cfg.note_embed_image = bool(self.embed_image_var.get())
        self.cfg.ollama_base_url = self.ollama_base_url_var.get()
        self.cfg.ollama_model = self.ollama_model_var.get()
        self.cfg.ollama_timeout = int(self.ollama_timeout_var.get())

        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._log("Starting...")

        thread = threading.Thread(target=self._run_processor, daemon=True)
        thread.start()

    def _on_stop(self) -> None:
        if self._processor is not None:
            self._processor.stop()
            self._log("Stop requested...")

    def _run_processor(self) -> None:
        try:
            def status_callback(msg: str) -> None:
                self.root.after(0, self._log, msg)

            self._processor = processor.Processor(
                source_folder=self.cfg.source_folder,
                obsidian_vault=self.cfg.obsidian_vault,
                ocr_language=self.cfg.ocr_language,
                ocr_confidence_threshold=self.cfg.ocr_confidence_threshold,
                note_tag=self.cfg.note_tag,
                note_embed_image=self.cfg.note_embed_image,
                note_date_format=self.cfg.note_date_format,
                ollama_model=self.cfg.ollama_model,
                ollama_base_url=self.cfg.ollama_base_url,
                ollama_timeout=self.cfg.ollama_timeout,
                status_callback=status_callback,
            )

            result = self._processor.run()
            self.root.after(0, self._update_stats, result)
            self.root.after(0, self._refresh_history)
        except Exception as e:
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            self.root.after(0, self._log, f"Error: {e}")
            for line in tb.splitlines():
                logger.error(line)
        finally:
            self.root.after(0, self.run_btn.configure, {"state": "normal"})
            self.root.after(0, self.stop_btn.configure, {"state": "disabled"})
            self._processor = None

    def _update_stats(self, result: dict) -> None:
        p = result["processed"]
        f = result["failed"]
        s = result["skipped"]
        fg = "#4caf50" if f == 0 else "#ff9800"
        self.stats_label.configure(
            text=f"Processed={p}  Failed={f}  Pending={s}", foreground=fg
        )

    def _log(self, message: str) -> None:
        self.progress_log.configure(state="normal")
        self.progress_log.insert("end", f">  {message}\n")
        self.progress_log.see("end")
        self.progress_log.configure(state="disabled")

    def run(self) -> None:
        self.root.mainloop()