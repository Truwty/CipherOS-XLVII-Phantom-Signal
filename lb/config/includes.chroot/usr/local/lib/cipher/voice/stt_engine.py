#!/usr/bin/env python3
"""CipherOS STT engine — faster-whisper with VAD."""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.config_loader import get_voice_config
from cipher.utils.lang_detect import save_language_preference

logger = logging.getLogger(__name__)


class STTEngine:
    def __init__(self) -> None:
        cfg = get_voice_config().get("stt", {})
        self.model_size  = cfg.get("model", "small")
        self.device      = cfg.get("device", "auto")
        self.compute     = cfg.get("compute_type", "int8")
        self.language    = cfg.get("language", "auto") or None
        self.beam_size   = cfg.get("beam_size", 5)
        self.sample_rate = cfg.get("sample_rate", 16000)
        self._model: "WhisperModel | None" = None  # type: ignore

    def _load_model(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel
        device = "cpu" if self.device == "auto" else self.device
        logger.info(f"Loading Whisper model '{self.model_size}' on {device}…")
        self._model = WhisperModel(
            self.model_size, device=device, compute_type=self.compute
        )
        logger.info("Whisper model ready.")

    async def transcribe(self, audio_data: bytes | str) -> str:
        """Transcribe audio bytes or file path to text."""
        await asyncio.to_thread(self._load_model)
        assert self._model

        def _run() -> str:
            import tempfile, wave, struct
            if isinstance(audio_data, bytes):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    with wave.open(f, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(self.sample_rate)
                        wf.writeframes(audio_data)
                    audio_path = f.name
            else:
                audio_path = audio_data

            lang = self.language if self.language and self.language != "auto" else None
            segments, info = self._model.transcribe(
                audio_path, language=lang, beam_size=self.beam_size, vad_filter=True
            )
            text = " ".join(seg.text for seg in segments).strip()
            detected_lang = info.language
            if detected_lang and detected_lang != "en":
                save_language_preference(detected_lang)
            return text

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:
            logger.error(f"Transcription error: {exc}")
            return ""
