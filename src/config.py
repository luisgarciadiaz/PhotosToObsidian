from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomllib as tomllib

import tomli_w


@dataclass
class Config:
    source_folder: Path = Path()
    obsidian_vault: Path = Path()
    ocr_language: str = "eng"
    ocr_confidence_threshold: int = 30
    note_tag: str = "photo-import"
    note_date_format: str = "%Y-%m-%d"
    ollama_model: str = "llava"
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 60


def get_config_dir() -> Path:
    return Path(__file__).parent.parent


def load_config(config_path: Optional[Path] = None) -> Config:
    if config_path is None:
        config_path = get_config_dir() / "config.toml"

    config = Config()

    if not config_path.exists():
        return config

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    _load_paths(config, data)
    _load_ocr(config, data)
    _load_note(config, data)
    _load_ollama(config, data)

    return config


def _load_paths(config: Config, data: dict) -> None:
    if "paths" not in data:
        return
    paths = data["paths"]
    if "source_folder" in paths:
        config.source_folder = Path(paths["source_folder"])
    if "obsidian_vault" in paths:
        config.obsidian_vault = Path(paths["obsidian_vault"])


def _load_ocr(config: Config, data: dict) -> None:
    if "ocr" not in data:
        return
    ocr = data["ocr"]
    if "language" in ocr:
        config.ocr_language = ocr["language"]
    if "confidence_threshold" in ocr:
        config.ocr_confidence_threshold = ocr["confidence_threshold"]


def _load_note(config: Config, data: dict) -> None:
    if "note" not in data:
        return
    note = data["note"]
    if "tag" in note:
        config.note_tag = note["tag"]
    if "date_format" in note:
        config.note_date_format = note["date_format"]


def _load_ollama(config: Config, data: dict) -> None:
    if "ollama" not in data:
        return
    ollama = data["ollama"]
    if "model" in ollama:
        config.ollama_model = ollama["model"]
    if "base_url" in ollama:
        config.ollama_base_url = ollama["base_url"]
    if "timeout" in ollama:
        config.ollama_timeout = ollama["timeout"]


def save_config(config: Config, config_path: Optional[Path] = None) -> None:
    if config_path is None:
        config_path = get_config_dir() / "config.toml"

    data = {
        "paths": {
            "source_folder": str(config.source_folder),
            "obsidian_vault": str(config.obsidian_vault),
        },
        "ocr": {
            "language": config.ocr_language,
            "confidence_threshold": config.ocr_confidence_threshold,
        },
        "note": {
            "tag": config.note_tag,
            "date_format": config.note_date_format,
        },
        "ollama": {
            "model": config.ollama_model,
            "base_url": config.ollama_base_url,
            "timeout": config.ollama_timeout,
        },
    }

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)
