"""Test OCR extraction on a generated image."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from src import ocr

text = "Hello World\n123 ABC"

img = Image.new("RGB", (400, 80), color="white")
draw = ImageDraw.Draw(img)
draw.text((10, 10), text, fill="black")

test_img = Path("test_ocr.png")
img.save(test_img)
print(f"Test image written: {test_img}")

try:
    result = ocr.extract(test_img, language="eng", confidence_threshold=0)
    print(f"Text: {result.text!r}")
    print(f"Confidence: {result.confidence:.1f}%")
    print(f"Success: {result.success}")
    if result.text.strip() == text:
        print("PASS")
    else:
        print("FAIL — text mismatch")
        sys.exit(1)
except ocr.TesseractNotFoundError as e:
    print(f"FAIL — {e}")
    sys.exit(1)
finally:
    test_img.unlink(missing_ok=True)