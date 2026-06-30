#!/usr/bin/env python3
"""CipherOS conversation context manager — maintains rolling chat history."""
import json
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Deque


@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    tokens: int = 0


class ContextManager:
    """Manages rolling conversation history with token budget."""

    def __init__(
        self,
        max_tokens: int = 6000,
        max_messages: int = 40,
        session_file: Path | None = None,
    ) -> None:
        self._max_tokens = max_tokens
        self._max_messages = max_messages
        self._history: Deque[Message] = deque(maxlen=max_messages)
        self._system_prompt = self._build_system_prompt()
        self._session_file = session_file

    def _build_system_prompt(self) -> str:
        return (
            "You are CipherOS, an intelligent AI integrated into a Kali Linux desktop system. "
            "You have access to the user's screen, voice, and full system control through a set of tools. "
            "You reason step-by-step and execute tools to complete tasks. "
            "Be concise, precise, and actionable. When you detect the user's language, match it. "
            "You remember past interactions and build on them. "
            "Security context: this is a professional penetration-testing environment."
        )

    def add_user(self, content: str) -> None:
        self._history.append(Message(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        self._history.append(Message(role="assistant", content=content))

    def add_tool_result(self, tool_name: str, result: str) -> None:
        self._history.append(
            Message(role="tool", content=f"[{tool_name}] {result}")
        )

    def get_messages(self) -> list[dict]:
        """Return messages in Ollama API format."""
        msgs = [{"role": "system", "content": self._system_prompt}]
        for m in self._history:
            role = "user" if m.role == "tool" else m.role
            msgs.append({"role": role, "content": m.content})
        return msgs

    def clear(self) -> None:
        self._history.clear()

    def save_session(self) -> None:
        if not self._session_file:
            return
        try:
            self._session_file.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(m) for m in self._history]
            self._session_file.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def load_session(self) -> None:
        if not self._session_file or not self._session_file.exists():
            return
        try:
            data = json.loads(self._session_file.read_text())
            for m in data[-self._max_messages:]:
                self._history.append(Message(**m))
        except Exception:
            pass

    @property
    def history(self) -> list[Message]:
        return list(self._history)

    def inject_context(self, label: str, content: str) -> None:
        """Inject retrieved memory as system-level context."""
        self._history.appendleft(
            Message(role="system", content=f"[Memory: {label}] {content}")
        )
