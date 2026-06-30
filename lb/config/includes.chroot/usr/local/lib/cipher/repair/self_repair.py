#!/usr/bin/env python3
"""CipherOS self-repair watchdog — monitors services and auto-restarts failures."""
import asyncio
import json
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.logger import setup_logger
from cipher.utils.config_loader import get

logger = setup_logger("self-repair")

WATCHED_SERVICES = [
    "cipher-ai-core", "cipher-voice", "cipher-screen-reader",
    "cipher-system-monitor", "ollama", "pipewire",
    "wireplumber", "NetworkManager",
]


def service_is_active(name: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() == "active"
    except Exception:
        return False


def restart_service(name: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "restart", name],
            capture_output=True, text=True, timeout=30
        )
        return r.returncode == 0
    except Exception:
        return False


async def repair_loop() -> None:
    check_interval = 30  # seconds
    restart_counts: dict[str, int] = {s: 0 for s in WATCHED_SERVICES}
    max_restarts = 5
    logger.info(f"Self-repair watchdog active — monitoring {len(WATCHED_SERVICES)} services.")

    while True:
        for svc in WATCHED_SERVICES:
            try:
                if not service_is_active(svc):
                    count = restart_counts.get(svc, 0)
                    if count >= max_restarts:
                        logger.error(f"{svc} has failed {count} times — giving up.")
                        continue
                    logger.warning(f"Service {svc} is not active — attempting restart…")
                    ok = await asyncio.to_thread(restart_service, svc)
                    if ok:
                        logger.info(f"Successfully restarted {svc}.")
                        restart_counts[svc] = 0
                    else:
                        restart_counts[svc] = count + 1
                        logger.error(f"Failed to restart {svc} (attempt {count+1}/{max_restarts}).")
                else:
                    if restart_counts.get(svc, 0) > 0:
                        restart_counts[svc] = 0
            except Exception as exc:
                logger.error(f"Watchdog error checking {svc}: {exc}")

        await asyncio.sleep(check_interval)


def main() -> None:
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    asyncio.run(repair_loop())


if __name__ == "__main__":
    main()
