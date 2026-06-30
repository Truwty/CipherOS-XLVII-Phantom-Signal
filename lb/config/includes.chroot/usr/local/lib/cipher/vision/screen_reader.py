#!/usr/bin/env python3
"""CipherOS background screen reader — periodic OCR → /tmp/cipher_screen_text.txt."""
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.logger import setup_logger

logger = setup_logger("screen-reader")
OUTPUT_FILE = Path("/tmp/cipher_screen_text.txt")
INTERVAL = 8.0  # seconds between captures


async def capture_and_ocr() -> str:
    """Grab screen with grim, OCR with tesseract, return text."""
    import tempfile, subprocess, os
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    try:
        wayland = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
        result = await asyncio.create_subprocess_exec(
            "grim", "-t", "png", tmp.name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env={**os.environ, "WAYLAND_DISPLAY": wayland},
        )
        await asyncio.wait_for(result.wait(), timeout=10)

        ocr = await asyncio.create_subprocess_exec(
            "tesseract", tmp.name, "stdout", "--psm", "6",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(ocr.communicate(), timeout=30)
        text = stdout.decode(errors="replace").strip()
        return text[:10000]  # cap at 10k chars
    except asyncio.TimeoutError:
        logger.warning("Screen capture/OCR timed out.")
        return ""
    except Exception as exc:
        logger.error(f"Screen capture error: {exc}")
        return ""
    finally:
        Path(tmp.name).unlink(missing_ok=True)


async def screen_reader_loop() -> None:
    logger.info("Screen reader daemon started.")
    while True:
        try:
            text = await capture_and_ocr()
            if text:
                OUTPUT_FILE.write_text(text)
                logger.debug(f"Screen text updated: {len(text)} chars")
        except Exception as exc:
            logger.error(f"Screen reader loop error: {exc}")
        await asyncio.sleep(INTERVAL)


def main() -> None:
    def _shutdown(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGTERM, _shutdown)
    asyncio.run(screen_reader_loop())


if __name__ == "__main__":
    main()
