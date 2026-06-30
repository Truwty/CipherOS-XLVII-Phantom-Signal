#!/usr/bin/env python3
"""CipherOS wake word detector using openWakeWord."""
import asyncio
import logging
import sys
from typing import Callable

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.config_loader import get_voice_config

logger = logging.getLogger(__name__)


class WakeWordDetector:
    def __init__(self, on_wake: Callable) -> None:
        cfg = get_voice_config().get("wake_word", {})
        self.enabled     = cfg.get("enabled", True)
        self.sensitivity = cfg.get("sensitivity", 0.7)
        self.on_wake     = on_wake
        self._running    = False
        self._model: "Model | None" = None  # type: ignore

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from openwakeword.model import Model
            self._model = Model(
                wakeword_models=["hey_cipher"],
                enable_speex_noise_suppression=False,
            )
            logger.info("Wake word model loaded.")
        except Exception:
            try:
                from openwakeword.model import Model
                self._model = Model(inference_framework="onnx")
                logger.info("Wake word model loaded (fallback).")
            except Exception as exc:
                logger.warning(f"Wake word model unavailable: {exc}")
                self._model = None

    async def run(self) -> None:
        if not self.enabled:
            return
        await asyncio.to_thread(self._load_model)
        self._running = True

        import pyaudio
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=16000, channels=1, format=pyaudio.paInt16,
            input=True, frames_per_buffer=1280,
        )
        logger.info("Wake word detection active — listening for 'Cipher'…")
        try:
            while self._running:
                try:
                    chunk = await asyncio.to_thread(stream.read, 1280, exception_on_overflow=False)
                    if self._model:
                        import numpy as np
                        audio_np = np.frombuffer(chunk, dtype=np.int16)
                        pred = self._model.predict(audio_np)
                        for model_name, score in pred.items():
                            if score >= self.sensitivity:
                                logger.info(f"Wake word detected! score={score:.2f}")
                                await self._trigger_wake()
                                await asyncio.sleep(2)  # debounce
                    else:
                        await asyncio.sleep(0.1)
                except OSError:
                    await asyncio.sleep(0.05)
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    async def _trigger_wake(self) -> None:
        try:
            sound = get_voice_config().get("wake_word", {}).get("activation_sound", "")
            if sound:
                import subprocess
                subprocess.Popen(["aplay", sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        if asyncio.iscoroutinefunction(self.on_wake):
            await self.on_wake()
        else:
            self.on_wake()

    def stop(self) -> None:
        self._running = False
