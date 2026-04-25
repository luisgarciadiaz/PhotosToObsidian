"""Test which Ollama models support images — probe with a real PNG pixel."""
import base64
import requests
import sys
from pathlib import Path

if __name__ == "__main__":
    src_dir = Path(__file__).resolve().parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

from src import ollama_ocr


def test_vision_probe(timeout: int = 30) -> list[str]:
    base_url = "http://localhost:11434"

    print("Fetching model list...")
    resp = requests.get(f"{base_url}/api/tags", timeout=10)
    resp.raise_for_status()
    raw = [m["name"] for m in resp.json().get("models", [])]
    seen = set()
    models = []
    for m in raw:
        name = m.split(":")[0]
        if name not in seen:
            seen.add(name)
            models.append(name)
    print(f"Models: {models}\n")

    # 1x1 white PNG
    png_pixel = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01"
        b"\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    b64_img = base64.b64encode(png_pixel).decode()

    vision_ok = []
    text_only = []

    for model in models:
        print(f"Probing {model}...", end=" ", flush=True)
        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "describe this image in 3 words max",
                    "images": [b64_img],
                    "stream": False,
                },
                timeout=timeout,
            )
        except requests.exceptions.Timeout:
            print("TIMEOUT")
            text_only.append(model)
            continue
        except Exception as e:
            print(f"ERR {type(e).__name__}")
            text_only.append(model)
            continue

        if resp.status_code == 400:
            print("TEXT-ONLY (400)")
            text_only.append(model)
        elif resp.status_code == 200:
            text = resp.json().get("response", "").strip()
            print(f"VISION -> '{text}'")
            vision_ok.append(model)
        else:
            print(f"HTTP {resp.status_code}")
            text_only.append(model)

    return vision_ok


if __name__ == "__main__":
    print("=== Ollama Vision Probe ===\n")
    ok = test_vision_probe()
    print(f"\n=== Vision-capable models ===\n{ok}")
    print(f"\n{'PASS' if ok else 'FAIL (no vision models found)'}")
    exit(0 if ok else 1)