from __future__ import annotations

__version__ = "0.1.0"

import threading
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
    VERTICAL,
    W,
)
from tkinter.filedialog import askdirectory
from tkinter.ttk import Frame as TtkFrame
from tkinter.ttk import Scrollbar as TtkScrollbar

from src import config, db, ollama_ocr, processor


class GUI:
    def __init__(self):
        self.root = Tk()
        self.root.title(f"PhotosToObsidian v{__version__}")

        self.cfg = config.load_config()

        self._create_toolbar()
        self._create_notebook()
        self._create_tabs()
        self._create_status_bar()

        self._populate_from_config()

    def _create_toolbar(self) -> None:
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side="top", fill="x")

        self.run_btn = ttk.Button(
            toolbar,
            text="Run",
            command=self._on_run,
        )
        self.run_btn.pack(side="left", padx=5, pady=5)

    def _create_notebook(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

    def _create_tabs(self) -> None:
        self.notebook.add(self._create_settings_tab(), text="Settings")
        self.notebook.add(self._create_models_tab(), text="AI / Models")
        self.notebook.add(self._create_history_tab(), text="History")

    def _create_settings_tab(self) -> TtkFrame:
        tab = ttk.Frame(self.notebook)
        inner = ttk.Frame(tab)
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        row = 0

        Label(inner, text="Source Folder:").grid(row=row, column=0, sticky=W, pady=5)
        self.source_folder_var = StringVar()
        Entry(inner, textvariable=self.source_folder_var, width=50).grid(row=row, column=1, sticky=W, pady=5)
        ttk.Button(inner, text="Browse...", command=self._browse_source_folder).grid(row=row, column=2, padx=5, pady=5)

        row += 1

        Label(inner, text="Obsidian Vault:").grid(row=row, column=0, sticky=W, pady=5)
        self.obsidian_vault_var = StringVar()
        Entry(inner, textvariable=self.obsidian_vault_var, width=50).grid(row=row, column=1, sticky=W, pady=5)
        ttk.Button(inner, text="Browse...", command=self._browse_obsidian_vault).grid(row=row, column=2, padx=5, pady=5)

        row += 1

        Label(inner, text="OCR Language:").grid(row=row, column=0, sticky=W, pady=5)
        self.ocr_language_var = StringVar()
        Entry(inner, textvariable=self.ocr_language_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        Label(inner, text='e.g. "eng+spa"').grid(row=row, column=2, sticky=W, padx=5)

        row += 1

        Label(inner, text="Confidence Threshold:").grid(row=row, column=0, sticky=W, pady=5)
        self.confidence_var = StringVar()
        Spinbox(inner, from_=0, to=100, textvariable=self.confidence_var, width=18).grid(row=row, column=1, sticky=W, pady=5)
        Label(inner, text="%").grid(row=row, column=2, sticky=W, padx=5)

        row += 1

        Label(inner, text="Options:").grid(row=row, column=0, sticky=W, pady=5)
        self.embed_image_var = BooleanVar()
        Checkbutton(inner, text="Embed image in note (![[...]])", variable=self.embed_image_var).grid(row=row, column=1, columnspan=2, sticky=W, pady=5)

        row += 1

        ttk.Button(inner, text="Save Settings", command=self._save_settings).grid(row=row, column=0, columnspan=3, pady=15)

        return tab

    def _create_models_tab(self) -> TtkFrame:
        tab = ttk.Frame(self.notebook)
        inner = ttk.Frame(tab)
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        row = 0

        Label(inner, text="Ollama Base URL:").grid(row=row, column=0, sticky=W, pady=5)
        self.ollama_base_url_var = StringVar()
        Entry(inner, textvariable=self.ollama_base_url_var, width=40).grid(row=row, column=1, sticky=W, pady=5)

        row += 1

        Label(inner, text="Ollama Model:").grid(row=row, column=0, sticky=W, pady=5)
        self.ollama_model_var = StringVar()
        Entry(inner, textvariable=self.ollama_model_var, width=30).grid(row=row, column=1, sticky=W, pady=5)
        ttk.Button(inner, text="Refresh Models", command=self._refresh_models).grid(row=row, column=2, padx=5, pady=5)

        row += 1

        Label(inner, text="Timeout (seconds):").grid(row=row, column=0, sticky=W, pady=5)
        self.ollama_timeout_var = StringVar()
        Spinbox(inner, from_=10, to=300, textvariable=self.ollama_timeout_var, width=18).grid(row=row, column=1, sticky=W, pady=5)

        row += 1

        self.ollama_status_label = Label(inner, text="Ollama status: checking...", fg="gray")
        self.ollama_status_label.grid(row=row, column=0, columnspan=3, sticky=W, pady=10)

        row += 1

        ttk.Button(inner, text="Save Ollama Settings", command=self._save_ollama_settings).grid(row=row, column=0, columnspan=3, pady=10)

        self._check_ollama_status()

        return tab

    def _create_history_tab(self) -> TtkFrame:
        tab = ttk.Frame(self.notebook)
        inner = ttk.Frame(tab)
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("file_name", "status", "tries", "engine", "last_tried", "note_path")

        tree_scroll = TtkScrollbar(inner, orient=VERTICAL)
        self.history_tree = ttk.Treeview(
            inner,
            columns=columns,
            show="headings",
            height=15,
            yscrollcommand=tree_scroll.set,
        )
        tree_scroll.config(command=self.history_tree.yview)

        self.history_tree.heading("file_name", text="Filename")
        self.history_tree.heading("status", text="Status")
        self.history_tree.heading("tries", text="Tries")
        self.history_tree.heading("engine", text="Engine")
        self.history_tree.heading("last_tried", text="Last Tried")
        self.history_tree.heading("note_path", text="Note Path")

        self.history_tree.column("file_name", width=150)
        self.history_tree.column("status", width=80)
        self.history_tree.column("tries", width=50)
        self.history_tree.column("engine", width=80)
        self.history_tree.column("last_tried", width=150)
        self.history_tree.column("note_path", width=200)

        self.history_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        btn_frame = ttk.Frame(inner)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="Refresh", command=self._refresh_history).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Success Records", command=self._clear_history).pack(side="left", padx=5)

        return tab

    def _create_status_bar(self) -> None:
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side="bottom", fill="x")

        self.progress_log = scrolledtext.ScrolledText(
            status_frame,
            height=8,
            wrap="word",
            state="disabled",
            font=("Courier New", 9),
        )
        self.progress_log.pack(fill="both", expand=True, padx=5, pady=5)

        self.status_label = Label(
            status_frame,
            text="Ready",
            anchor=W,
            font=("Segoe UI", 9),
        )
        self.status_label.pack(fill="x", padx=5, pady=(0, 5))

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
            self._log(f"Error saving settings: {e}")

    def _save_ollama_settings(self) -> None:
        try:
            self.cfg.ollama_base_url = self.ollama_base_url_var.get()
            self.cfg.ollama_model = self.ollama_model_var.get()
            self.cfg.ollama_timeout = int(self.ollama_timeout_var.get())

            config.save_config(self.cfg)
            self._log("Ollama settings saved.")
        except Exception as e:
            self._log(f"Error saving Ollama settings: {e}")

    def _refresh_models(self) -> None:
        self._log("Checking available Ollama models...")
        models = ollama_ocr.get_available_models(base_url=self.ollama_base_url_var.get())
        if models:
            self.ollama_model_var.set(models[0])
            self._log(f"Found models: {', '.join(models)}")
        else:
            self._log("No models found or Ollama not reachable.")

    def _check_ollama_status(self) -> None:
        if ollama_ocr.ollama_available():
            self.ollama_status_label.config(text="Ollama: Found on PATH", fg="green")
        else:
            self.ollama_status_label.config(text="Ollama: Not found on PATH", fg="red")

    def _refresh_history(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        records = db.get_all_records()
        for record in records:
            self.history_tree.insert(
                "",
                "end",
                values=(
                    record.get("file_name", ""),
                    record.get("status", ""),
                    record.get("tries", ""),
                    record.get("ocr_engine_used", ""),
                    record.get("last_tried_at", ""),
                    record.get("note_path", ""),
                ),
            )

    def _clear_history(self) -> None:
        db.clear_success_records()
        self._refresh_history()
        self._log("Cleared all successful records.")

    def _on_run(self) -> None:
        self.cfg.source_folder = Path(self.source_folder_var.get())
        self.cfg.obsidian_vault = Path(self.obsidian_vault_var.get())
        self.cfg.ocr_language = self.ocr_language_var.get()
        self.cfg.ocr_confidence_threshold = int(self.confidence_var.get())
        self.cfg.note_embed_image = bool(self.embed_image_var.get())
        self.cfg.ollama_base_url = self.ollama_base_url_var.get()
        self.cfg.ollama_model = self.ollama_model_var.get()
        self.cfg.ollama_timeout = int(self.ollama_timeout_var.get())

        self.run_btn.config(state="disabled")
        self._log("Starting processing...")

        thread = threading.Thread(target=self._run_processor, daemon=True)
        thread.start()

    def _run_processor(self) -> None:
        try:
            def status_callback(msg: str) -> None:
                self.root.after(0, self._log, msg)

            result = processor.run(self.cfg, status_callback=status_callback)

            self.root.after(0, self._update_status_bar, result)
            self.root.after(0, self._refresh_history)
        except Exception as e:
            self.root.after(0, self._log, f"Error: {e}")
        finally:
            self.root.after(0, self.run_btn.config, {"state": "normal"})

    def _update_status_bar(self, result: dict) -> None:
        self.status_label.config(
            text=(
                f"Last run: Processed={result['processed']}, "
                f"Failed={result['failed']}, "
                f"Skipped={result['skipped']}"
            )
        )

    def _log(self, message: str) -> None:
        self.progress_log.config(state="normal")
        self.progress_log.insert("end", message + "\n")
        self.progress_log.see("end")
        self.progress_log.config(state="disabled")

    def run(self) -> None:
        self.root.mainloop()