# PhotosToObsidian — Agent Notes

> Developer memos, architectural decisions, and pending tasks for AI agents working on this codebase.

---

## Project Overview

**PhotosToObsidian** is a Python desktop tool that:
1. Scans a folder for image files.
2. Extracts text via **Tesseract OCR** (primary) or a local **Ollama vision model** (fallback after 2 failures).
3. Writes an **Obsidian-compatible Markdown** note for each successfully parsed image.
4. Renames the source image to `<name>.ext.tobedeleted` on success.
5. Tracks all attempts in a local **SQLite** database.
6. Provides a **Tkinter GUI** for configuration and history review.

---

## Architecture

```
photos_to_obsidian.py   ← Entry point, launches GUI
src/
  config.py             ← Load/save config.toml (tomllib + tomli-w)
  scanner.py            ← Find eligible images in source folder
  ocr.py                ← Tesseract OCR wrapper (pytesseract)
  ollama_ocr.py         ← Ollama REST API fallback (requests)
  db.py                 ← SQLite tracking layer (sqlite3 stdlib)
  note_builder.py       ← Build and write .md files
  file_manager.py       ← Rename processed images to .tobedeleted
  processor.py          ← Orchestration loop (runs in background thread)
  gui.py                ← Tkinter GUI (3 tabs: Settings, AI/Models, History)
```

### Key Data Flow

```
GUI Run → processor.run() [thread]
  → scanner → [images]
  → db.get_tries() → choose engine (Tesseract / Ollama)
  → ocr / ollama_ocr → OCRResult
  → note_builder → .md file
  → file_manager → rename to .tobedeleted
  → db.upsert_attempt()
  → GUI callback (progress log update)
```

---

## Configuration

All user settings live in `config.toml` (auto-created with defaults on first run).
The GUI writes back to this file on Save — never edit in code directly.

Sections:
- `[paths]` — source folder, obsidian vault
- `[ocr]` — language, confidence threshold
- `[note]` — tags, embed image toggle, date format
- `[ollama]` — model name, base URL, timeout

---

## Database

File: `photos_to_obsidian.db` (SQLite, next to `config.toml`)
Table: `processed_files`

| Column | Notes |
|---|---|
| `file_name` | Basename |
| `file_path` | Absolute path at time of attempt |
| `status` | `success` \| `failed` \| `pending` |
| `tries` | Incremented every attempt |
| `last_tried_at` | ISO-8601 |
| `note_path` | Path to generated `.md` (NULL if failed) |
| `ocr_engine_used` | `tesseract` \| `ollama` |

---

## Ollama Fallback Rules

- Triggered when `tries >= 2` AND `shutil.which("ollama") is not None`.
- Calls `POST /api/generate` on `localhost:11434` with the configured model (default `llava`).
- `confidence` is always `0.0` for Ollama responses (no score exposed by API).
- If Ollama is unreachable, log a warning and increment tries — **do not crash**.

---

## Rename Convention

Successful image: `photo.jpg` → `photo.jpg.tobedeleted`

The scanner **skips** any file ending in `.tobedeleted` to avoid reprocessing.

---

## Pending Tasks / Roadmap

- [ ] `v0.1.0` — Initial implementation of all modules + GUI.
- [ ] Tesseract binary path override in Settings (for non-standard installs).
- [ ] Support for subdirectory scanning toggle in GUI.
- [ ] Export history to CSV from the History tab.
- [ ] Dry-run / preview mode (`--dry-run` CLI flag).
- [ ] Multi-language OCR auto-detect.
- [ ] Cloud OCR stubs (Google Vision, Azure) — marked `NotImplementedError` for now.

---

## Developer Notes

- **Threading**: `processor.run()` must always run in a `threading.Thread` (daemon=True). Never call it from the main GUI thread or the UI will freeze.
- **No external DB libs**: Use stdlib `sqlite3` only. No SQLAlchemy, no ORMs.
- **No web server**: The Ollama call uses `requests` with a configurable timeout. Do not use `asyncio` for this.
- **Tkinter only**: No PyQt, no wxPython. Keep the GUI dependency footprint minimal.
- **Config persistence**: Use `tomli-w` for writing TOML. Never write TOML manually with string templates.

---

## Changelog

See `CHANGELOG.md` for version history.

---

## Version

Current: `0.0.0` (pre-implementation)
