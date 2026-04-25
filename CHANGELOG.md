# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-25

### Added
- Tkinter GUI with 3 tabs: Settings, AI/Models, History.
- SQLite tracking database (`photos_to_obsidian.db`) for all processing attempts.
- Tesseract OCR integration via `pytesseract` with confidence scoring.
- Ollama vision model fallback (triggered after 2 Tesseract failures).
- Vision model probe — filters Ollama models to only show vision-capable ones.
- Obsidian-compatible Markdown note builder with YAML frontmatter.
- File renamer — appends `.tobedeleted` to processed images.
- Stop button to interrupt processing mid-run.
- Progress log (dark terminal theme) with per-image status.
- Color-coded history table (green = success, red = failed).
- Preview panel in Settings tab with dark terminal styling.
- `photos_to_obsidian.log` file logging every step with full tracebacks.
- Auto-detection of Tesseract binary at common install paths (`C:\Program Files\Tesseract-OCR`).
- `TESSDATA_PREFIX` auto-set for non-PATH Tesseract installs.
- `eng.traineddata` auto-download helper (permission denied falls back to user instructions).

### Fixed
- `ttk.Frame` `padding=` not supported on Python 3.13 — switched to nested frame + `pack(padx, pady)`.
- `shutil.which("tesseract")` fails when not on PATH — searches common install paths and sets `pytesseract.tesseract_cmd` directly.
- `TESSDATA_PREFIX` pointing to parent dir instead of `tessdata` — now points to `tessdata` folder.
- Conditional `try/except` relative import chain for running `src/gui.py` directly — added `sys.path` guard for `__main__`.
- `__future__` import not first in `gui.py` — moved to line 1.
- Processor loop broken try/except/finally block — rewritten cleanly.

### Changed
- Ollama model selector changed from text entry to readonly Combobox (only vision models shown).
- GUI restyled with dark toolbar, green Run button, section headers, and dark terminal log area.
- Settings tab split into two columns: form on left, preview on right.

## [0.0.1] - Initial Development Phase

- Core modules scaffolded: `config.py`, `scanner.py`, `ocr.py`, `db.py`, `gui.py`, `ollama_ocr.py`, `note_builder.py`, `file_manager.py`, `processor.py`.
- `config.toml` with default paths and settings.
- `requirements.txt` with all Python dependencies.