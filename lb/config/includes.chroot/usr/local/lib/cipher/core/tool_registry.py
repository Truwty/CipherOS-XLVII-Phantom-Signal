#!/usr/bin/env python3
"""CipherOS tool registry — manages all agent tools."""
import asyncio
import inspect
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class Tool:
    def __init__(self, name: str, description: str, fn: Callable, schema: dict | None = None):
        self.name = name
        self.description = description
        self.fn = fn
        self.schema = schema or {}

    async def run(self, **kwargs: Any) -> Any:
        try:
            if inspect.iscoroutinefunction(self.fn):
                return await self.fn(**kwargs)
            else:
                return await asyncio.to_thread(self.fn, **kwargs)
        except Exception as exc:
            logger.error(f"Tool {self.name} error: {exc}")
            return {"error": str(exc)}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, description: str, schema: dict | None = None):
        """Decorator to register a tool function."""
        def decorator(fn: Callable) -> Callable:
            self._tools[name] = Tool(name, description, fn, schema)
            return fn
        return decorator

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def tool_definitions(self) -> list[dict]:
        """Return tool list in Ollama function-calling format."""
        defs = []
        for t in self._tools.values():
            defs.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.schema or {"type": "object", "properties": {}},
                },
            })
        return defs

    def describe(self) -> str:
        """Plain-text tool list for system prompt injection."""
        lines = ["Available tools:"]
        for t in self._tools.values():
            lines.append(f"  - {t.name}: {t.description}")
        return "\n".join(lines)
