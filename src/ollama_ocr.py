from __future__ import annotations

import base64
import shutil
from dataclasses import dataclass
from pathlib import Path

import requests

from src.ocr import OCRResult


def ollama_available() -> bool:
    return shutil.which("ollama") is not None


def extract(
    image_path: Path,
    model: str = "llava",
    base_url: str = "http://localhost:11434",
    timeout: int = 60,
) -> OCRResult:
    if not ollama_available():
        return OCRResult(
            text="",
            confidence=0.0,
            success=False,
            engine="ollama",
        )

    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return OCRResult(
            text="",
            confidence=0.0,
            success=False,
            engine="ollama",
        )

    prompt = (
        "Extract all text visible in this image. Return only the raw text, no commentary."
    )

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_data],
        "stream": False,
    }

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return OCRResult(
            text="",
            confidence=0.0,
            success=False,
            engine="ollama",
        )

    try:
        result_data = response.json()
        text = result_data.get("response", "").strip()
    except Exception:
        text = ""

    success = len(text) > 0

    return OCRResult(
        text=text,
        confidence=0.0,
        success=success,
        engine="ollama",
    )


def get_available_models(
    base_url: str = "http://localhost:11434",
    timeout: int = 10,
) -> list[str]:
    if not ollama_available():
        return []

    try:
        response = requests.get(
            f"{base_url}/api/tags",
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    try:
        data = response.json()
        models = data.get("models", [])
        names = [m.get("name", "").split(":")[0] for m in models if m.get("name")]
    except Exception:
        return []

    image_probe = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()

    vision = []
    for name in names:
        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={"model": name, "prompt": "is this an image?", "images": [image_probe], "stream": False},
                timeout=timeout,
            )
            if resp.status_code != 400:
                vision.append(name)
        except requests.exceptions.RequestException:
            pass

    return vision