# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project initialization with Tkinter GUI.
- SQLite tracking database for processed files.
- Integration with Tesseract OCR via `pytesseract`.
- Fallback processing via local Ollama vision model (`llava`).
- Markdown note builder compatible with Obsidian.
- File manager to rename processed images to `.tobedeleted`.

## [0.1.0] - Initial Development Phase
- Core modules planned and scaffolded (`config.py`, `scanner.py`, `ocr.py`, `db.py`, `gui.py`, `ollama_ocr.py`, `note_builder.py`, `file_manager.py`).
