from __future__ import annotations

from pathlib import Path


def mark_as_deleted(image_path: Path) -> Path:
    new_name = Path(str(image_path) + ".tobedeleted")
    image_path.rename(new_name)
    return new_name