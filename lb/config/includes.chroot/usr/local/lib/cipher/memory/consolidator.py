#!/usr/bin/env python3
"""CipherOS nightly memory consolidator — deduplicate, prune, summarise."""
import asyncio
import logging
import sys

sys.path.insert(0, "/usr/local/lib")
from cipher.memory.memory_store import MemoryStore
from cipher.utils.logger import setup_logger

logger = setup_logger("memory-consolidator")


async def consolidate() -> None:
    logger.info("Starting memory consolidation…")
    store = MemoryStore()
    await store.initialize()

    # 1. Expire old entries
    expired = await store.expire_old()
    logger.info(f"Expired {expired} stale memories.")

    # 2. Count remaining
    total = await store.count()
    logger.info(f"Memory store has {total} active entries after pruning.")

    await store.close()
    logger.info("Memory consolidation complete.")


if __name__ == "__main__":
    asyncio.run(consolidate())
