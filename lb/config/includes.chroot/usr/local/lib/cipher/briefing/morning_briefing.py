#!/usr/bin/env python3
"""CipherOS morning briefing — daily AI-generated audio/text briefing."""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.logger import setup_logger
from cipher.search.search_engine import SearchEngine

logger = setup_logger("morning-briefing")
AI_SOCKET = "/tmp/cipher_ai.sock"


async def query_ai(text: str) -> str:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(AI_SOCKET), timeout=5.0
        )
        writer.write(json.dumps({"command": "chat", "text": text}).encode())
        await writer.drain()
        data = await asyncio.wait_for(reader.read(65536), timeout=60.0)
        writer.close()
        return json.loads(data.decode()).get("response", "")
    except Exception as exc:
        logger.error(f"AI query failed: {exc}")
        return ""


async def speak(text: str) -> None:
    import subprocess
    proc = subprocess.Popen(["piper-speak", text],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc.wait()


async def generate_briefing() -> str:
    now = datetime.now()
    search = SearchEngine()

    # Gather: top headlines, weather text summary, date context
    news_task   = asyncio.create_task(search.search("world news today", "news"))
    news = await news_task
    headlines = "; ".join(
        r.get("title", "") for r in news.get("results", [])[:5] if r.get("title")
    )

    prompt = (
        f"Today is {now.strftime('%A, %B %d %Y')} at {now.strftime('%H:%M')}. "
        f"Recent headlines: {headlines}. "
        "Please give a concise morning briefing in 4-6 spoken sentences covering: "
        "the date and day, key world news, anything to be aware of today, "
        "and a motivational closing line. Keep it natural and conversational."
    )
    return await query_ai(prompt)


async def run(auto: bool = False) -> None:
    logger.info("Generating morning briefing…")
    text = await generate_briefing()
    if not text:
        text = f"Good morning. It is {datetime.now().strftime('%A, %B %d')}. Have a productive day."

    # Save briefing
    brief_dir = Path.home() / ".local/share/cipher/briefings"
    brief_dir.mkdir(parents=True, exist_ok=True)
    fname = brief_dir / f"{datetime.now().strftime('%Y-%m-%d')}.txt"
    fname.write_text(text)
    logger.info(f"Briefing saved: {fname}")

    if auto:
        await speak(text)
    else:
        print(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true",
                        help="Speak the briefing (for systemd timer)")
    args = parser.parse_args()
    asyncio.run(run(auto=args.auto))


if __name__ == "__main__":
    main()
