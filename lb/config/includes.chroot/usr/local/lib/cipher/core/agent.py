#!/usr/bin/env python3
"""CipherOS ReAct agent — plans and executes multi-step tool chains."""
import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncIterator

from .tool_registry import ToolRegistry
from .context_manager import ContextManager

logger = logging.getLogger(__name__)


class CipherAgent:
    """ReAct-pattern agent with tool execution loop."""

    THINK_MARKER = "<think>"
    ACT_MARKER   = "<act>"
    OBS_MARKER   = "<observe>"
    DONE_MARKER  = "<done>"

    def __init__(
        self,
        registry: ToolRegistry,
        context: ContextManager,
        ollama_client: Any,
        model: str = "llama3.1:8b",
        max_steps: int = 25,
        step_timeout: float = 30.0,
    ) -> None:
        self.registry = registry
        self.context = context
        self.ollama = ollama_client
        self.model = model
        self.max_steps = max_steps
        self.step_timeout = step_timeout
        self._running = False

    async def run(self, user_input: str) -> AsyncIterator[dict]:
        """Execute the ReAct loop and yield step events."""
        self._running = True
        self.context.add_user(user_input)

        # Inject tool descriptions
        tool_desc = self.registry.describe()
        messages = self.context.get_messages()
        messages.insert(1, {
            "role": "system",
            "content": (
                f"{tool_desc}\n\n"
                "To use a tool, respond with JSON:\n"
                '{"action": "tool_name", "args": {...}}\n'
                "When the task is complete, respond with plain text (no JSON)."
            )
        })

        for step in range(self.max_steps):
            if not self._running:
                break

            try:
                response = await asyncio.wait_for(
                    self._llm_call(messages),
                    timeout=self.step_timeout
                )
            except asyncio.TimeoutError:
                yield {"type": "error", "message": "Step timed out"}
                break

            # Try to parse as tool call
            tool_call = self._parse_tool_call(response)
            if tool_call:
                tool_name = tool_call.get("action", "")
                tool_args = tool_call.get("args", {})

                yield {"type": "thinking", "step": step, "tool": tool_name, "args": tool_args}

                tool = self.registry.get(tool_name)
                if tool:
                    try:
                        result = await asyncio.wait_for(
                            tool.run(**tool_args),
                            timeout=self.step_timeout
                        )
                        obs = json.dumps(result) if not isinstance(result, str) else result
                    except asyncio.TimeoutError:
                        obs = f"Tool {tool_name} timed out"
                    except Exception as exc:
                        obs = f"Tool error: {exc}"
                else:
                    obs = f"Unknown tool: {tool_name}"

                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"[Observation] {obs}"})
                self.context.add_tool_result(tool_name, obs)

                yield {"type": "observation", "tool": tool_name, "result": obs}
            else:
                # Final answer
                self.context.add_assistant(response)
                yield {"type": "final", "response": response}
                break

        self._running = False

    async def _llm_call(self, messages: list[dict]) -> str:
        response = await asyncio.to_thread(
            self.ollama.chat,
            model=self.model,
            messages=messages,
            options={"temperature": 0.7, "num_predict": 2048},
        )
        return response["message"]["content"].strip()

    def _parse_tool_call(self, text: str) -> dict | None:
        """Try to extract JSON tool call from model response."""
        # Direct JSON
        text = text.strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if "action" in data:
                    return data
            except json.JSONDecodeError:
                pass

        # JSON in code block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if "action" in data:
                    return data
            except json.JSONDecodeError:
                pass

        # Inline JSON
        match = re.search(r'\{[^{}]*"action"[^{}]*\}', text)
        if match:
            try:
                data = json.loads(match.group(0))
                if "action" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return None

    def stop(self) -> None:
        self._running = False
