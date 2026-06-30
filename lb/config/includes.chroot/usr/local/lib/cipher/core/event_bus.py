#!/usr/bin/env python3
"""CipherOS event bus — async pub/sub."""
import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable) -> None:
        self._subs[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable) -> None:
        try:
            self._subs[event].remove(handler)
        except ValueError:
            pass

    async def publish(self, event: str, data: Any = None) -> None:
        for handler in list(self._subs.get(event, []) + self._subs.get("*", [])):
            try:
                result = handler(event, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error(f"EventBus error [{event}]: {exc}")

    def publish_sync(self, event: str, data: Any = None) -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.publish(event, data))
            else:
                loop.run_until_complete(self.publish(event, data))
        except RuntimeError:
            asyncio.run(self.publish(event, data))


_bus: EventBus | None = None

def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
