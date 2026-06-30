#!/usr/bin/env python3
"""CipherOS TTS engine — Piper neural TTS with streaming sentence output."""
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.config_loader import get_voice_config
from cipher.utils.lang_detect import get_tts_model_for_language

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self) -> None:
        cfg = get_voice_config()
        self.model     = cfg.get("tts", {}).get("model", "/usr/local/share/cipher/piper-models/en_US-hfc_female-medium.onnx")
        self.speed     = cfg.get("tts", {}).get("speed", 1.1)
        self.volume    = cfg.get("tts", {}).get("volume", 0.85)
        self._speaking = False
        self._proc: subprocess.Popen | None = None

    def set_language(self, lang: str) -> None:
        model = get_tts_model_for_language(lang)
        if Path(model).exists():
            self.model = model
            logger.info(f"TTS model switched to {model}")

    async def speak(self, text: str) -> None:
        if not text.strip():
            return
        self._speaking = True
        logger.debug(f"Speaking: {text[:60]}")
        try:
            length_scale = str(round(1.0 / max(0.5, self.speed), 3))
            piper = await asyncio.create_subprocess_exec(
                "piper", "--model", self.model, "--output_raw",
                "--length_scale", length_scale,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            aplay = await asyncio.create_subprocess_exec(
                "aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            raw_audio, _ = await piper.communicate(input=text.encode())
            await aplay.communicate(input=raw_audio)
        except FileNotFoundError:
            logger.error("piper or aplay not found. TTS unavailable.")
        except Exception as exc:
            logger.error(f"TTS error: {exc}")
        finally:
            self._speaking = False

    async def speak_sentences(self, text: str) -> None:
        """Stream-speak: split on sentence endings for lower latency."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        for sentence in sentences:
            if sentence.strip():
                await self.speak(sentence.strip())

    def stop(self) -> None:
        self._speaking = False
        try:
            subprocess.run(["pkill", "-f", "aplay"], capture_output=True)
        except Exception:
            pass

    @property
    def is_speaking(self) -> bool:
        return self._speaking
