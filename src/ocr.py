from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image


@dataclass
class OCRResult:
    text: str
    confidence: float
    success: bool
    engine: str


class TesseractNotFoundError(EnvironmentError):
    pass


def check_tesseract() -> bool:
    return shutil.which("tesseract") is not None


def extract(
    image_path: Path,
    language: str = "eng",
    confidence_threshold: int = 30,
) -> OCRResult:
    if not check_tesseract():
        raise TesseractNotFoundError(
            "Tesseract binary not found. Please install Tesseract and add it to PATH."
        )

    try:
        image = Image.open(image_path)
    except Exception:
        return OCRResult(text="", confidence=0.0, success=False, engine="tesseract")

    try:
        data = pytesseract.image_to_data(
            image, lang=language, output_type=pytesseract.Output.DICT
        )
    except Exception:
        return OCRResult(text="", confidence=0.0, success=False, engine="tesseract")

    words = data.get("words", [])
    confidences = data.get("conf", [])

    valid_confidences = [
        conf for conf in confidences if conf != -1
    ]

    mean_confidence = (
        sum(valid_confidences) / len(valid_confidences)
        if valid_confidences
        else 0.0
    )

    text = pytesseract.image_to_string(image, lang=language)
    text = text.strip()

    success = (
        mean_confidence >= confidence_threshold
        and len(text) > 0
    )

    return OCRResult(
        text=text,
        confidence=mean_confidence,
        success=success,
        engine="tesseract",
    )