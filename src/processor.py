from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from src import config, db, file_manager, note_builder, ollama_ocr, ocr, scanner


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
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

    def _emit(self, message: str) -> None:
        self.status_callback(message)

    def run(self) -> dict:
        db.init_db()

        images = scanner.scan_for_images(self.source_folder)
        if not images:
            self._emit("No images found to process.")
            return {"processed": 0, "failed": 0, "skipped": 0}

        results = {"processed": 0, "failed": 0, "skipped": len(images)}
        self._emit(f"Found {len(images)} image(s) to process.")

        for image_path in images:
            tries = db.get_tries(image_path)
            self._emit(f"Processing: {image_path.name} (try #{tries + 1})")

            use_ollama = tries >= 2 and ollama_ocr.ollama_available()

            if use_ollama:
                self._emit(f"  Using Ollama fallback for {image_path.name}")
                result = ollama_ocr.extract(
                    image_path,
                    model=self.ollama_model,
                    base_url=self.ollama_base_url,
                    timeout=self.ollama_timeout,
                )
            else:
                try:
                    result = ocr.extract(
                        image_path,
                        language=self.ocr_language,
                        confidence_threshold=self.ocr_confidence_threshold,
                    )
                except ocr.TesseractNotFoundError as e:
                    self._emit(f"  ERROR: {e}")
                    result = ocr.OCRResult(
                        text="",
                        confidence=0.0,
                        success=False,
                        engine="tesseract",
                    )

            if result.success:
                self._emit(f"  OCR succeeded ({result.engine}, conf={result.confidence:.1f})")
                note_path = note_builder.write_note(
                    image_path,
                    result,
                    self.obsidian_vault,
                    tag=self.note_tag,
                    embed_image=self.note_embed_image,
                    date_format=self.note_date_format,
                )

                if note_path:
                    file_manager.mark_as_deleted(image_path)
                    db.upsert_attempt(
                        image_path,
                        status="success",
                        engine=result.engine,
                        note_path=note_path,
                    )
                    self._emit(f"  Note written: {note_path.name}")
                    self._emit(f"  Renamed to: {image_path.name}.tobedeleted")
                    results["processed"] += 1
                    results["skipped"] -= 1
                else:
                    db.upsert_attempt(
                        image_path,
                        status="failed",
                        engine=result.engine,
                    )
                    self._emit("  ERROR: Failed to write note")
                    results["failed"] += 1
                    results["skipped"] -= 1
            else:
                self._emit(f"  OCR failed ({result.engine})")
                db.upsert_attempt(
                    image_path,
                    status="failed",
                    engine=result.engine,
                )
                results["failed"] += 1
                results["skipped"] -= 1

        self._emit(
            f"Done. Processed: {results['processed']}, "
            f"Failed: {results['failed']}, "
            f"Skipped: {results['skipped']}"
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