"""Basic Tesseract connectivity test."""
from pathlib import Path

from src import ocr

path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")

if ocr.check_tesseract():
    print(f"OK — Tesseract found at: {path}")
else:
    print(f"FAIL — Tesseract NOT found at: {path}")
    print("Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    exit(1)