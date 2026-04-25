from __future__ import annotations

import logging
import sys
import threading
import traceback
from pathlib import Path
from typing import Callable, Optional

if __name__ == "__main__":
    src_dir = Path(__file__).resolve().parent
    if src_dir.parent not in sys.path:
        sys.path.insert(0, str(src_dir.parent))

from src import config, db, file_manager, note_builder, ollama_ocr, ocr, scanner


log_dir = Path(__file__).resolve().parent.parent
_log_file = log_dir / "photos_to_obsidian.log"

_file_handler = logging.FileHandler(_log_file, encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[_file_handler],
)
logger = logging.getLogger(__name__)


class Processor:
    def __init__(
        self,
        source_folder: Path,
        obsidian_vault: Path,
        ocr_language: str,
        ocr_confidence_threshold: int,
        note_tag: str,
        note_embed_image: bool,
        note_date_format: str,
        ollama_model: str,
        ollama_base_url: str,
        ollama_timeout: int,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.source_folder = source_folder
        self.obsidian_vault = obsidian_vault
        self.ocr_language = ocr_language
        self.ocr_confidence_threshold = ocr_confidence_threshold
        self.note_tag = note_tag
        self.note_embed_image = note_embed_image
        self.note_date_format = note_date_format
        self.ollama_model = ollama_model
        self.ollama_base_url = ollama_base_url
        self.ollama_timeout = ollama_timeout
        self.status_callback = status_callback or (lambda msg: logger.info(msg))
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def _is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def _emit(self, message: str) -> None:
        logger.info(message)
        self.status_callback(message)

    def _trace(self, step: str, exc: Exception) -> None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self._emit(f"  [{step}] {type(exc).__name__}: {exc}")
        for line in tb.splitlines():
            self._emit(f"    {line}")

    def run(self) -> dict:
        db.init_db()

        images = scanner.scan_for_images(self.source_folder)
        if not images:
            self._emit("No images found to process.")
            return {"processed": 0, "failed": 0, "skipped": 0}

        results = {"processed": 0, "failed": 0, "skipped": len(images)}
        self._emit(f"Found {len(images)} image(s) to process.")

        for image_path in images:
            if self._is_stopped():
                self._emit("Processing stopped by user.")
                break
            self._emit(f"Processing: {image_path.name}")
            try:
                tries = db.get_tries(image_path)
            except Exception as e:
                self._trace("db.get_tries", e)
                tries = 0
            self._emit(f"  Try #{tries + 1}")

            use_ollama = tries >= 2 and ollama_ocr.ollama_available()

            try:
                if use_ollama:
                    self._emit(f"  Engine: Ollama ({self.ollama_model})")
                    result = ollama_ocr.extract(
                        image_path,
                        model=self.ollama_model,
                        base_url=self.ollama_base_url,
                        timeout=self.ollama_timeout,
                    )
                else:
                    self._emit(f"  Engine: Tesseract ({self.ocr_language})")
                    result = ocr.extract(
                        image_path,
                        language=self.ocr_language,
                        confidence_threshold=self.ocr_confidence_threshold,
                    )
            except Exception as e:
                self._trace("ocr.extract", e)
                result = ocr.OCRResult(
                    text="",
                    confidence=0.0,
                    success=False,
                    engine="ollama" if use_ollama else "tesseract",
                )

            if result.success:
                self._emit(f"  OCR succeeded (conf={result.confidence:.1f})")
                try:
                    note_path = note_builder.write_note(
                        image_path,
                        result,
                        self.obsidian_vault,
                        tag=self.note_tag,
                        embed_image=self.note_embed_image,
                        date_format=self.note_date_format,
                    )
                except Exception as e:
                    self._trace("note_builder.write_note", e)
                    note_path = None

                if note_path:
                    try:
                        file_manager.mark_as_deleted(image_path)
                    except Exception as e:
                        self._trace("file_manager.mark_as_deleted", e)
                        self._emit(f"  WARNING: rename failed — file kept at {image_path}")

                    try:
                        db.upsert_attempt(
                            image_path,
                            status="success",
                            engine=result.engine,
                            note_path=note_path,
                        )
                    except Exception as e:
                        self._trace("db.upsert_attempt", e)

                    self._emit(f"  Note: {note_path.name}")
                    self._emit(f"  Renamed: {image_path.name}.tobedeleted")
                    results["processed"] += 1
                    results["skipped"] -= 1
                else:
                    try:
                        db.upsert_attempt(
                            image_path,
                            status="failed",
                            engine=result.engine,
                        )
                    except Exception as e:
                        self._trace("db.upsert_attempt", e)
                    self._emit("  ERROR: failed to write note")
                    results["failed"] += 1
                    results["skipped"] -= 1
            else:
                self._emit(f"  OCR failed ({result.engine})")
                try:
                    db.upsert_attempt(
                        image_path,
                        status="failed",
                        engine=result.engine,
                    )
                except Exception as e:
                    self._trace("db.upsert_attempt", e)
                results["failed"] += 1
                results["skipped"] -= 1

        self._emit(
            f"Done. Processed={results['processed']}, "
            f"Failed={results['failed']}, "
            f"Skipped={results['skipped']}"
        )

        return results


def run(cfg: config.Config, status_callback: Optional[Callable[[str], None]] = None) -> dict:
    processor = Processor(
        source_folder=cfg.source_folder,
        obsidian_vault=cfg.obsidian_vault,
        ocr_language=cfg.ocr_language,
        ocr_confidence_threshold=cfg.ocr_confidence_threshold,
        note_tag=cfg.note_tag,
        note_embed_image=cfg.note_embed_image,
        note_date_format=cfg.note_date_format,
        ollama_model=cfg.ollama_model,
        ollama_base_url=cfg.ollama_base_url,
        ollama_timeout=cfg.ollama_timeout,
        status_callback=status_callback,
    )
    return processor.run()