#!/usr/bin/env python3
"""CipherOS system control — app launching, mouse/keyboard, clipboard, screenshots."""
import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SystemControl:
    """Wayland-first system control for Hyprland desktop."""

    # ── Application control ──────────────────────────────────────────────────
    APP_ALIASES: dict[str, str] = {
        "browser": "chromium", "chrome": "chromium", "firefox": "firefox-esr",
        "terminal": "kitty", "term": "kitty", "files": "thunar",
        "file manager": "thunar", "text editor": "gedit", "editor": "neovim",
        "vlc": "vlc", "music": "mpv", "calc": "gnome-calculator",
        "settings": "gnome-control-center",
    }

    async def launch_app(self, app: str) -> dict[str, Any]:
        cmd = self.APP_ALIASES.get(app.lower(), app)
        try:
            subprocess.Popen(
                [cmd],
                env={**os.environ, "DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"launched": cmd, "success": True}
        except FileNotFoundError:
            return {"error": f"App not found: {cmd}"}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Screenshot ───────────────────────────────────────────────────────────
    async def take_screenshot(self, region: str = "full") -> dict[str, Any]:
        out = Path.home() / f"Pictures/screenshot-{int(asyncio.get_event_loop().time())}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if region == "selection":
                geom = subprocess.check_output(["slurp"], text=True).strip()
                subprocess.run(["grim", "-g", geom, str(out)], check=True)
            else:
                subprocess.run(["grim", str(out)], check=True)
            return {"path": str(out), "success": True}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Clipboard ────────────────────────────────────────────────────────────
    async def get_clipboard(self) -> dict[str, Any]:
        try:
            text = subprocess.check_output(
                ["wl-paste", "--type", "text/plain"],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            return {"content": text}
        except Exception:
            return {"content": ""}

    async def set_clipboard(self, text: str) -> dict[str, Any]:
        try:
            proc = subprocess.Popen(
                ["wl-copy"], stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            proc.communicate(input=text.encode())
            return {"success": True}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Keyboard input ───────────────────────────────────────────────────────
    async def type_text(self, text: str) -> dict[str, Any]:
        try:
            # wtype is the Wayland xdotool equivalent
            subprocess.run(["wtype", text], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"typed": len(text), "success": True}
        except FileNotFoundError:
            try:
                subprocess.run(["xdotool", "type", "--", text], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return {"typed": len(text), "success": True, "method": "xdotool"}
            except Exception as e2:
                return {"error": str(e2)}
        except Exception as exc:
            return {"error": str(exc)}

    async def key_press(self, keys: str) -> dict[str, Any]:
        """keys: e.g. 'ctrl+c', 'super+return', 'alt+F4'"""
        try:
            # wtype -k for key names, -M/-m for modifiers
            parts = keys.lower().replace("+", " ").split()
            key   = parts[-1]
            mods  = parts[:-1]
            cmd   = ["wtype"]
            for m in mods:
                cmd += ["-M", m]
            cmd += ["-k", key]
            for m in reversed(mods):
                cmd += ["-m", m]
            subprocess.run(cmd, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"keys": keys, "success": True}
        except FileNotFoundError:
            try:
                subprocess.run(
                    ["xdotool", "key", keys.replace("+", "--")],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return {"keys": keys, "success": True, "method": "xdotool"}
            except Exception as e2:
                return {"error": str(e2)}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Mouse ────────────────────────────────────────────────────────────────
    async def move_mouse(self, x: int, y: int) -> dict[str, Any]:
        try:
            subprocess.run(["xdotool", "mousemove", str(x), str(y)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"moved": {"x": x, "y": y}, "success": True}
        except Exception as exc:
            return {"error": str(exc)}

    async def click(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        btn_map = {"left": "1", "middle": "2", "right": "3"}
        b = btn_map.get(button, "1")
        try:
            subprocess.run(
                ["xdotool", "mousemove", str(x), str(y), "click", b],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return {"clicked": {"x": x, "y": y, "button": button}, "success": True}
        except Exception as exc:
            return {"error": str(exc)}

    # ── Window management ────────────────────────────────────────────────────
    async def focus_window(self, window_class: str) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["hyprctl", "dispatch", "focuswindow", f"class:{window_class}"],
                capture_output=True, text=True
            )
            return {"success": result.returncode == 0, "output": result.stdout.strip()}
        except Exception as exc:
            return {"error": str(exc)}

    async def get_active_window(self) -> dict[str, Any]:
        try:
            import json
            out = subprocess.check_output(
                ["hyprctl", "activewindow", "-j"], text=True
            )
            return json.loads(out)
        except Exception as exc:
            return {"error": str(exc)}
