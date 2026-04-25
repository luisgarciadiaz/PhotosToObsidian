from pathlib import Path
from src import ocr

files = sorted(Path(".").glob("*.PNG"))[:5]
for f in files:
    try:
        result = ocr.extract(f, language="eng+spa", confidence_threshold=30)
        print(f"=== {f.name} === Success={result.success} Conf={result.confidence:.1f}")
        print(result.text[:300] if result.text else "(empty)")
        print()
    except Exception as e:
        print(f"=== {f.name} === ERROR: {e}")