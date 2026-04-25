from __future__ import annotations

from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def scan_for_images(source_folder: Path) -> list[Path]:
    if not source_folder.exists() or not source_folder.is_dir():
        return []

    images = []
    for file_path in source_folder.iterdir():
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        if file_path.name.endswith(".tobedeleted"):
            continue

        images.append(file_path)

    return sorted(images)