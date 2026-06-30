#!/usr/bin/env python3
"""CipherOS HUD server — broadcasts AI state to AGS via Unix socket."""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HUDServer:
    SOCKET_PATH = "/tmp/cipher_hud.sock"

    def __init__(self) -> None:
        self._clients: list[asyncio.StreamWriter] = []
        self._server: asyncio.AbstractServer | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        Path(self.SOCKET_PATH).unlink(missing_ok=True)
        self._server = await asyncio.start_unix_server(
            self._handle_client, path=self.SOCKET_PATH
        )
        os.chmod(self.SOCKET_PATH, 0o600)
        logger.info(f"HUD server listening on {self.SOCKET_PATH}")

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        async with self._lock:
            for w in self._clients:
                try:
                    w.close()
                except Exception:
                    pass
            self._clients.clear()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        async with self._lock:
            self._clients.append(writer)
        logger.debug("AGS client connected.")
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                # Handle incoming commands from AGS
                try:
                    cmd = json.loads(data.decode())
                    logger.debug(f"HUD command: {cmd}")
                except Exception:
                    pass
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            async with self._lock:
                try:
                    self._clients.remove(writer)
                except ValueError:
                    pass
            try:
                writer.close()
            except Exception:
                pass

    async def broadcast(self, message: dict[str, Any]) -> None:
        payload = (json.dumps(message) + "\n").encode()
        async with self._lock:
            dead = []
            for w in self._clients:
                try:
                    w.write(payload)
                    await w.drain()
                except Exception:
                    dead.append(w)
            for w in dead:
                try:
                    self._clients.remove(w)
                except ValueError:
                    pass
