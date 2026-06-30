#!/usr/bin/env python3
"""CipherOS voice daemon — VAD → STT → AI core → TTS pipeline."""
import asyncio
import json
import logging
import signal
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.logger import setup_logger
from cipher.utils.config_loader import get_voice_config
from cipher.voice.stt_engine import STTEngine
from cipher.voice.tts_engine import TTSEngine
from cipher.voice.wake_word import WakeWordDetector

logger = setup_logger("cipher-voice")
AI_SOCKET = "/tmp/cipher_ai.sock"


async def query_ai_core(text: str) -> str:
    """Send text to AI core via socket and get response."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(AI_SOCKET), timeout=5.0
        )
        payload = json.dumps({"command": "chat", "text": text}).encode()
        writer.write(payload)
        await writer.drain()
        data = await asyncio.wait_for(reader.read(65536), timeout=60.0)
        writer.close()
        response = json.loads(data.decode())
        return response.get("response", "I could not process that.")
    except FileNotFoundError:
        return "AI core is not running."
    except asyncio.TimeoutError:
        return "The AI core timed out."
    except Exception as exc:
        logger.error(f"AI socket error: {exc}")
        return "Connection to AI core failed."


class VoicePipeline:
    def __init__(self) -> None:
        self.cfg      = get_voice_config()
        self.stt      = STTEngine()
        self.tts      = TTSEngine()
        self.wake     = WakeWordDetector(on_wake=self._on_wake)
        self._active  = False
        self._running = False
        self._listen_task: asyncio.Task | None = None

    async def _on_wake(self) -> None:
        logger.info("Wake word triggered — starting push-to-talk capture.")
        await self.listen_once()

    async def listen_once(self) -> None:
        """Capture a single utterance, transcribe, query AI, and speak response."""
        if self._active:
            logger.debug("Already listening — ignoring duplicate wake.")
            return
        self._active = True
        try:
            audio = await self._capture_utterance()
            if not audio:
                logger.info("No speech detected in capture window.")
                return

            transcript = await self.stt.transcribe(audio)
            if not transcript or len(transcript.strip()) < 3:
                logger.info("Empty transcript — ignoring.")
                return

            logger.info(f"Heard: {transcript}")
            response = await query_ai_core(transcript)
            logger.info(f"Response: {response[:80]}")
            await self.tts.speak_sentences(response)
        except Exception as exc:
            logger.error(f"Pipeline error: {exc}")
        finally:
            self._active = False

    async def _capture_utterance(self) -> bytes | None:
        """Record until silence detected (VAD-based)."""
        cfg = self.cfg.get("stt", {})
        silence_timeout   = cfg.get("silence_timeout", 1.2)
        min_duration      = cfg.get("min_speech_duration", 0.3)
        sample_rate       = cfg.get("sample_rate", 16000)
        chunk_size        = cfg.get("chunk_size", 1024)
        vad_sensitivity   = cfg.get("vad_sensitivity", 0.6)
        listen_timeout    = self.cfg.get("wake_word", {}).get("listen_timeout", 10.0)

        try:
            import pyaudio
            import webrtcvad
        except ImportError:
            logger.error("pyaudio or webrtcvad not installed.")
            return None

        vad = webrtcvad.Vad()
        vad.set_mode(int(vad_sensitivity * 3))

        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=sample_rate, channels=1, format=pyaudio.paInt16,
            input=True, frames_per_buffer=chunk_size,
        )

        frames: list[bytes] = []
        silent_chunks = 0
        speaking = False
        max_silent = int(silence_timeout * sample_rate / chunk_size)
        deadline = time.monotonic() + listen_timeout

        logger.debug("Listening for speech…")
        try:
            while time.monotonic() < deadline:
                chunk = await asyncio.to_thread(
                    stream.read, chunk_size, exception_on_overflow=False
                )
                # VAD expects 10/20/30ms frames at 8/16/32 kHz
                frame_30ms = chunk[:int(sample_rate * 0.03 * 2)]
                try:
                    is_speech = vad.is_speech(frame_30ms, sample_rate)
                except Exception:
                    is_speech = False

                if is_speech:
                    speaking = True
                    silent_chunks = 0
                    frames.append(chunk)
                elif speaking:
                    frames.append(chunk)
                    silent_chunks += 1
                    if silent_chunks >= max_silent:
                        break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        if not speaking:
            return None
        duration = len(frames) * chunk_size / sample_rate
        if duration < min_duration:
            return None
        return b"".join(frames)

    async def run(self) -> None:
        self._running = True
        logger.info("Voice pipeline starting…")
        wake_task = asyncio.create_task(self.wake.run())

        # Also listen on push-to-talk socket
        socket_path = "/tmp/cipher_voice.sock"
        Path(socket_path).unlink(missing_ok=True)
        server = await asyncio.start_unix_server(
            self._handle_ptt_client, path=socket_path
        )
        import os
        os.chmod(socket_path, 0o600)

        logger.info("Voice pipeline ready. Wake word active.")
        try:
            async with server:
                await asyncio.gather(server.serve_forever(), wake_task)
        except asyncio.CancelledError:
            pass
        finally:
            self.wake.stop()
            logger.info("Voice pipeline stopped.")

    async def _handle_ptt_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle push-to-talk trigger from CLI or keyboard shortcut."""
        try:
            data = await asyncio.wait_for(reader.read(256), timeout=2.0)
            cmd = data.decode().strip()
            if cmd == "trigger":
                asyncio.create_task(self.listen_once())
                writer.write(b'{"ok":true}')
            elif cmd == "speak":
                text = (await reader.read(4096)).decode()
                await self.tts.speak(text)
                writer.write(b'{"ok":true}')
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()


def main() -> None:
    pipeline = VoicePipeline()

    def _shutdown(sig, frame):
        logger.info("Shutting down voice pipeline…")
        asyncio.get_event_loop().stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    asyncio.run(pipeline.run())


if __name__ == "__main__":
    main()
