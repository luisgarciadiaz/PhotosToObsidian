# PhotosToObsidian

Turn your photo scans into Obsidian notes automatically.

## What it does

1. Watches a folder for image files (JPG, PNG, WEBP, TIFF, BMP).
2. Reads the text in each image using OCR.
3. Creates a Markdown note in your Obsidian vault with the extracted text.
4. Renames the processed image to `photo.jpg.tobedeleted` so you know it's done.
5. If an image fails to parse twice, it automatically tries a local AI vision model via **Ollama** as a fallback.
6. Keeps a full history of every attempt in a local SQLite database.

---

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.10+ | 3.11+ recommended |
| Tesseract OCR | [Download installer](https://github.com/UB-Mannheim/tesseract/wiki) |
| Ollama *(optional)* | Required only for the AI fallback — [ollama.com](https://ollama.com) |
| A vision model *(optional)* | e.g. `ollama pull llava` |

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/luisgarciadiaz/PhotosToObsidian.git
cd PhotosToObsidian

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Tesseract (Windows)
# Download and run the installer from:
# https://github.com/UB-Mannheim/tesseract/wiki
# By default it installs to C:\Program Files\Tesseract-OCR\
# Add it to PATH with PowerShell (run as Admin if needed):

# TEMPORARY (current session only):
$env:PATH += ";C:\Program Files\Tesseract-OCR"

# PERMANENT (adds to User PATH):
[Environment]::SetEnvironmentVariable(
    "PATH",
    [Environment]::GetEnvironmentVariable("PATH", "User") + ";C:\Program Files\Tesseract-OCR",
    "User"
)

# Verify:
tesseract --version
```

---

## Usage

```bash
python photos_to_obsidian.py
```

This opens the GUI. From there:

1. **Settings tab** — set your source image folder and your Obsidian vault inbox folder, then click **Save**.
2. **AI / Models tab** — if you have Ollama installed, pick the vision model (e.g. `llava`). The status indicator will show whether Ollama is reachable.
3. Click **Run** — progress is shown in the log area at the bottom.

---

## How the fallback works

| Attempt | Engine used |
|---|---|
| 1st and 2nd try | Tesseract OCR |
| 3rd try onward | Ollama vision model (only if Ollama is installed and running) |

If neither engine can extract text, the image is left untouched and marked as `failed` in the database. You can see the full history in the **History tab**.

---

## Output

- Markdown notes are written to the Obsidian vault folder you configure.
- Each note is named `YYYY-MM-DD_<image-stem>.md`.
- Successfully processed images are renamed to `<original-name>.tobedeleted`.

**Example note:**

```markdown
---
tags: [photo-import]
date: 2026-04-25
source_image: receipt_001.jpg
ocr_confidence: 91.2
ocr_engine: tesseract
---

# receipt_001

![[receipt_001.jpg]]

## Extracted Text

Total: $42.00
Thank you for your purchase.
```

---

## Configuration

Edit `config.toml` directly, or use the Settings tab in the GUI:

```toml
[paths]
source_folder  = "C:/Users/you/Pictures/ToProcess"
obsidian_vault = "C:/Users/you/ObsidianVault/Inbox"

[ocr]
language             = "eng"   # e.g. "eng+spa" for English + Spanish
confidence_threshold = 30

[note]
tag         = "photo-import"
embed_image = true

[ollama]
model    = "llava"
base_url = "http://localhost:11434"
timeout  = 60
```

---

## Database

All processing attempts are stored in `photos_to_obsidian.db` (SQLite, created automatically).
You can view the history directly in the **History tab** of the GUI.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
