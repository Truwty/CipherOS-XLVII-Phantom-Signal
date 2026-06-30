#!/usr/bin/env python3
"""CipherOS silent language detection and memory."""
from pathlib import Path
import os

_LANG_FILE = Path(os.environ.get("HOME", "/home/cipher")) / ".local/share/cipher/identity/language"

VOICE_MODELS: dict[str, str] = {
    "en": "/usr/local/share/cipher/piper-models/en_US-hfc_female-medium.onnx",
    "en_GB": "/usr/local/share/cipher/piper-models/en_GB-jenny_dioco-medium.onnx",
    "fr": "/usr/local/share/cipher/piper-models/en_US-hfc_female-medium.onnx",
    "de": "/usr/local/share/cipher/piper-models/en_US-hfc_female-medium.onnx",
    "es": "/usr/local/share/cipher/piper-models/en_US-hfc_female-medium.onnx",
}


def detect_language(text: str) -> str:
    """Detect language from text, fallback to saved preference."""
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return load_language_preference()


def save_language_preference(lang: str) -> None:
    """Save language silently to disk."""
    try:
        _LANG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LANG_FILE.write_text(lang.strip())
    except Exception:
        pass


def load_language_preference() -> str:
    """Load saved language preference."""
    try:
        return _LANG_FILE.read_text().strip() or "en"
    except Exception:
        return "en"


def get_tts_model_for_language(lang: str) -> str:
    """Return the best TTS model path for a language code."""
    return VOICE_MODELS.get(lang, VOICE_MODELS["en"])
