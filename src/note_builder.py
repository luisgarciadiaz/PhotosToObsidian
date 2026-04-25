from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from src.ocr import OCRResult


def write_note(
    image_path: Path,
    ocr_result: OCRResult,
    obsidian_vault: Path,
    tag: str = "photo-import",
    date_format: str = "%Y-%m-%d",
) -> Optional[Path]:
    if not obsidian_vault.exists():
        try:
            obsidian_vault.mkdir(parents=True, exist_ok=True)
        except Exception:
            return None

    date_str = datetime.now().strftime(date_format)
    stem = image_path.stem

    base_name = f"{date_str}_{stem}.md"
    note_path = obsidian_vault / base_name

    counter = 1
    while note_path.exists():
        base_name = f"{date_str}_{stem}_{counter}.md"
        note_path = obsidian_vault / base_name
        counter += 1

    image_name = image_path.name
    confidence_str = f"{ocr_result.confidence:.1f}"

    content_lines = [
        "---",
        f"tags: [{tag}]",
        f"date: {date_str}",
        f"source_image: {image_name}",
        f"ocr_confidence: {confidence_str}",
        f"ocr_engine: {ocr_result.engine}",
        "---",
        "",
        f"# {stem}",
        "",
        "## Extracted Text",
        "",
        ocr_result.text,
    ]

    content = "\n".join(content_lines)

    try:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(content)
        return note_path
    except Exception:
        return None