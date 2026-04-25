from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass
class OCRResult:
    text: str
    confidence: float
    success: bool
    engine: str


class TesseractNotFoundError(EnvironmentError):
    pass


def check_tesseract(search_paths: Optional[list[str]] = None) -> bool:
    if shutil.which("tesseract"):
        return True

    if search_paths is None:
        search_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files\Tesseract\tesseract.exe",
            r"C:\tesseract\tesseract.exe",
        ]

    for path in search_paths:
        if Path(path).exists():
            return True

    return False


TESSERACT_CMD: Optional[str] = None


def _init_tesseract_cmd() -> None:
    global TESSERACT_CMD
    if TESSERACT_CMD is not None:
        return

    import os
    import pytesseract

    tesseract_exe = shutil.which("tesseract")
    if not tesseract_exe:
        search = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files\Tesseract\tesseract.exe",
            r"C:\tesseract\tesseract.exe",
        ]
        for path in search:
            if Path(path).exists():
                tesseract_exe = path
                tessdata = Path(path).parent / "tessdata"
                if tessdata.exists():
                    os.environ["TESSDATA_PREFIX"] = str(tessdata)
                break
        else:
            tesseract_exe = "tesseract"

    TESSERACT_CMD = tesseract_exe
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def _install_language(lang: str) -> bool:
    import os
    import urllib.request

    tesseract_dir = Path(TESSERACT_CMD).parent
    tessdata_dir = tesseract_dir / "tessdata"
    dest = tessdata_dir / f"{lang}.traineddata"

    if dest.exists():
        return True

    url = f"https://github.com/tesseract-ocr/tessdata/raw/main/{lang}.traineddata"
    user_dir = Path(os.environ.get("USERPROFILE", "~"))
    temp_path = user_dir / f"{lang}.traineddata"

    try:
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, str(temp_path))
        dest.write_bytes(temp_path.read_bytes())
        temp_path.unlink(missing_ok=True)
        return True
    except PermissionError:
        print(f"PERMISSION DENIED — run this in Admin PowerShell:")
        print(f"  Copy-Item {temp_path} {dest}")
        return False
    except Exception:
        return False


def extract(
    image_path: Path,
    language: str = "eng",
    confidence_threshold: int = 30,
) -> OCRResult:
    _init_tesseract_cmd()
    if not check_tesseract():
        raise TesseractNotFoundError(
            "Tesseract binary not found. Install from:\n"
            "  https://github.com/UB-Mannheim/tesseract/wiki\n"
            "Then add its folder to PATH, e.g.:\n"
            "  $env:PATH += ';C:\\Program Files\\Tesseract-OCR'"
        )

    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

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