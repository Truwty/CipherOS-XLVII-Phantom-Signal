#!/usr/bin/env python3
"""CipherOS AI Core — main daemon process.
Connects all subsystems: agent, voice, screen-reader, memory, HUD.
"""
import asyncio
import json
import logging
import os
import signal
import socket
import sys
import time
from pathlib import Path
from typing import Any

import ollama

# Internal imports
sys.path.insert(0, "/usr/local/lib")
from cipher.utils.config_loader import load_config, get
from cipher.utils.logger import setup_logger
from cipher.core.context_manager import ContextManager
from cipher.core.tool_registry import ToolRegistry
from cipher.core.agent import CipherAgent
from cipher.memory.memory_store import MemoryStore
from cipher.hud.hud_server import HUDServer
from cipher.control.system_control import SystemControl
from cipher.search.search_engine import SearchEngine

logger = setup_logger("ai-core")

# ── Systemd notify ────────────────────────────────────────────────────────────
def sd_notify(state: str) -> None:
    sock_path = os.environ.get("NOTIFY_SOCKET", "")
    if not sock_path:
        return
    try:
        path = sock_path.lstrip("@")
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.connect(path)
            s.sendall(state.encode())
    except Exception:
        pass


class AICore:
    def __init__(self) -> None:
        load_config()
        self.model       = get("ai.primary_model", "llama3.1:8b")
        self.fast_model  = get("ai.fast_model", "phi3:mini")
        self.ollama      = ollama.Client(host=get("ai.ollama_endpoint", "http://127.0.0.1:11434"))
        self.context     = ContextManager(
            max_tokens=get("ai.context_window", 8192),
            session_file=Path.home() / ".local/share/cipher/sessions/current.json",
        )
        self.registry    = ToolRegistry()
        self.memory      = MemoryStore()
        self.hud         = HUDServer()
        self.control     = SystemControl()
        self.search      = SearchEngine()
        self.agent       = CipherAgent(
            registry=self.registry,
            context=self.context,
            ollama_client=self.ollama,
            model=self.model,
            max_steps=get("agent.max_planning_steps", 25),
        )
        self._running    = True
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all agent tools."""

        @self.registry.register("bash", "Execute a bash command in a sandboxed shell",
            schema={"type":"object","properties":{"command":{"type":"string","description":"Shell command to run"}},"required":["command"]})
        async def bash(command: str) -> dict:
            import asyncio, subprocess
            try:
                proc = await asyncio.create_subprocess_shell(
                    command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                return {"stdout": stdout.decode()[:4000], "stderr": stderr.decode()[:1000], "returncode": proc.returncode}
            except asyncio.TimeoutError:
                return {"error": "Command timed out after 30s"}

        @self.registry.register("read_file", "Read a file from disk",
            schema={"type":"object","properties":{"path":{"type":"string"}},"required":["path"]})
        async def read_file(path: str) -> dict:
            try:
                content = Path(path).read_text(errors="replace")
                return {"content": content[:8000], "truncated": len(content) > 8000}
            except Exception as e:
                return {"error": str(e)}

        @self.registry.register("write_file", "Write content to a file",
            schema={"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]})
        async def write_file(path: str, content: str) -> dict:
            try:
                p = Path(path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
                return {"success": True, "path": str(p)}
            except Exception as e:
                return {"error": str(e)}

        @self.registry.register("list_dir", "List directory contents",
            schema={"type":"object","properties":{"path":{"type":"string"}},"required":["path"]})
        async def list_dir(path: str) -> dict:
            try:
                entries = []
                for entry in Path(path).iterdir():
                    entries.append({"name": entry.name, "type": "dir" if entry.is_dir() else "file",
                                    "size": entry.stat().st_size if entry.is_file() else 0})
                return {"entries": entries[:100]}
            except Exception as e:
                return {"error": str(e)}

        @self.registry.register("web_search", "Search the web using DuckDuckGo",
            schema={"type":"object","properties":{"query":{"type":"string"},"mode":{"type":"string","enum":["search","news","research","price","compare"]}},"required":["query"]})
        async def web_search(query: str, mode: str = "search") -> dict:
            return await self.search.search(query, mode)

        @self.registry.register("open_app", "Open an application by name",
            schema={"type":"object","properties":{"app":{"type":"string"}},"required":["app"]})
        async def open_app(app: str) -> dict:
            return await self.control.launch_app(app)

        @self.registry.register("take_screenshot", "Capture the current screen",
            schema={"type":"object","properties":{"region":{"type":"string","description":"Optional: 'full' or 'selection'"}}})
        async def take_screenshot(region: str = "full") -> dict:
            return await self.control.take_screenshot(region)

        @self.registry.register("type_text", "Type text into the focused window",
            schema={"type":"object","properties":{"text":{"type":"string"}},"required":["text"]})
        async def type_text(text: str) -> dict:
            return await self.control.type_text(text)

        @self.registry.register("move_mouse", "Move mouse to screen coordinates",
            schema={"type":"object","properties":{"x":{"type":"integer"},"y":{"type":"integer"}},"required":["x","y"]})
        async def move_mouse(x: int, y: int) -> dict:
            return await self.control.move_mouse(x, y)

        @self.registry.register("click", "Click at coordinates",
            schema={"type":"object","properties":{"x":{"type":"integer"},"y":{"type":"integer"},"button":{"type":"string","enum":["left","right","middle"]}},"required":["x","y"]})
        async def click(x: int, y: int, button: str = "left") -> dict:
            return await self.control.click(x, y, button)

        @self.registry.register("memory_store", "Save information to long-term memory",
            schema={"type":"object","properties":{"content":{"type":"string"},"category":{"type":"string"}},"required":["content"]})
        async def memory_store_tool(content: str, category: str = "facts") -> dict:
            await self.memory.add(content, category=category)
            return {"stored": True}

        @self.registry.register("memory_recall", "Recall relevant memories",
            schema={"type":"object","properties":{"query":{"type":"string"}},"required":["query"]})
        async def memory_recall(query: str) -> dict:
            results = await self.memory.search(query)
            return {"memories": [r["content"] for r in results[:10]]}

        @self.registry.register("get_clipboard", "Get clipboard contents",
            schema={"type":"object","properties":{}})
        async def get_clipboard() -> dict:
            return await self.control.get_clipboard()

        @self.registry.register("set_clipboard", "Set clipboard text",
            schema={"type":"object","properties":{"text":{"type":"string"}},"required":["text"]})
        async def set_clipboard(text: str) -> dict:
            return await self.control.set_clipboard(text)

        @self.registry.register("key_press", "Simulate keyboard shortcut",
            schema={"type":"object","properties":{"keys":{"type":"string","description":"e.g. ctrl+c, super+return"}},"required":["keys"]})
        async def key_press(keys: str) -> dict:
            return await self.control.key_press(keys)

        @self.registry.register("get_system_info", "Get CPU, RAM, disk, network info",
            schema={"type":"object","properties":{}})
        async def get_system_info() -> dict:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "ram_percent": psutil.virtual_memory().percent,
                "ram_gb": round(psutil.virtual_memory().used / 1e9, 2),
                "disk_percent": psutil.disk_usage("/").percent,
                "load_avg": list(os.getloadavg()),
            }

        @self.registry.register("read_screen", "Get OCR text from the current screen",
            schema={"type":"object","properties":{}})
        async def read_screen() -> dict:
            try:
                screen_file = Path("/tmp/cipher_screen_text.txt")
                if screen_file.exists():
                    return {"text": screen_file.read_text()[:5000]}
                return {"text": "No screen capture available"}
            except Exception as e:
                return {"error": str(e)}

        @self.registry.register("speak", "Speak text aloud via TTS",
            schema={"type":"object","properties":{"text":{"type":"string"}},"required":["text"]})
        async def speak(text: str) -> dict:
            import subprocess
            proc = subprocess.Popen(
                ["piper-speak", text],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return {"speaking": True, "pid": proc.pid}

        @self.registry.register("notify", "Send desktop notification",
            schema={"type":"object","properties":{"title":{"type":"string"},"body":{"type":"string"},"urgency":{"type":"string","enum":["low","normal","critical"]}},"required":["title","body"]})
        async def notify(title: str, body: str, urgency: str = "normal") -> dict:
            import subprocess
            subprocess.Popen(["notify-send", "-u", urgency, title, body])
            return {"sent": True}

        logger.info(f"Registered {len(self.registry.all_tools())} tools.")

    async def handle_input(self, text: str) -> str:
        """Process a text query through the agent, return final response."""
        logger.info(f"Input: {text[:80]}")
        await self.hud.broadcast({"type": "ai_status", "data": {"status": "thinking", "response": ""}})

        # Inject memory context
        memories = await self.memory.search(text, top_k=5)
        if memories:
            mem_text = "\n".join(f"- {m['content']}" for m in memories[:5])
            self.context.inject_context("relevant memories", mem_text)

        final_response = "I couldn't complete that task."
        async for event in self.agent.run(text):
            if event["type"] == "final":
                final_response = event["response"]
            elif event["type"] == "thinking":
                await self.hud.broadcast({
                    "type": "ai_status",
                    "data": {"status": "thinking", "response": f"Using {event['tool']}…"}
                })

        await self.hud.broadcast({
            "type": "ai_status",
            "data": {"status": "operational", "response": final_response}
        })
        logger.info(f"Response: {final_response[:80]}")
        return final_response

    async def run(self) -> None:
        """Main event loop — serve input from socket and voice bridge."""
        logger.info("CipherOS AI Core starting…")
        await self.memory.initialize()
        await self.hud.start()

        sd_notify("READY=1\nSTATUS=CipherOS AI Core operational")
        await self.hud.broadcast({"type": "ai_status", "data": {"status": "operational", "response": "CipherOS ready."}})

        # Unix socket for CLI/IPC
        socket_path = "/tmp/cipher_ai.sock"
        try:
            Path(socket_path).unlink(missing_ok=True)
        except Exception:
            pass

        server = await asyncio.start_unix_server(
            self._handle_socket_client, path=socket_path
        )
        os.chmod(socket_path, 0o600)
        logger.info(f"Listening on {socket_path}")

        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            sd_notify("STOPPING=1")
            await self.memory.close()
            await self.hud.stop()
            logger.info("AI Core stopped.")

    async def _handle_socket_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await asyncio.wait_for(reader.read(65536), timeout=5.0)
            payload = json.loads(data.decode())
            cmd  = payload.get("command", "chat")
            text = payload.get("text", "")

            if cmd == "chat":
                response = await self.handle_input(text)
                writer.write(json.dumps({"response": response}).encode())
            elif cmd == "ping":
                writer.write(b'{"status":"ok"}')
            elif cmd == "clear_context":
                self.context.clear()
                writer.write(b'{"cleared":true}')
            elif cmd == "status":
                writer.write(json.dumps({
                    "status": "operational",
                    "model": self.model,
                    "tools": len(self.registry.all_tools()),
                }).encode())
            else:
                writer.write(b'{"error":"unknown command"}')
        except Exception as exc:
            logger.error(f"Socket handler error: {exc}")
            try:
                writer.write(json.dumps({"error": str(exc)}).encode())
            except Exception:
                pass
        finally:
            try:
                await writer.drain()
                writer.close()
            except Exception:
                pass


def main() -> None:
    def _shutdown(sig: int, frame: Any) -> None:
        logger.info(f"Received signal {sig}, shutting down…")
        asyncio.get_event_loop().stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    core = AICore()
    try:
        asyncio.run(core.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
