#!/usr/bin/env python3
"""CipherOS TOML configuration loader."""
import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore


_CONFIG_PATH = Path(os.environ.get("CIPHER_CONFIG", "/etc/cipher/cipher.conf"))
_CACHE: dict[str, Any] | None = None


def load_config(path: Path | None = None) -> dict[str, Any]:
    global _CACHE
    cfg_path = path or _CONFIG_PATH
    try:
        with open(cfg_path, "rb") as f:
            _CACHE = tomllib.load(f)
    except Exception as e:
        _CACHE = {}
    return _CACHE


def get(key: str, default: Any = None) -> Any:
    """Dot-notation key access: 'ai.primary_model'"""
    cfg = _CACHE or load_config()
    parts = key.split(".")
    node: Any = cfg
    for p in parts:
        if not isinstance(node, dict):
            return default
        node = node.get(p, default)
    return node


def get_voice_config() -> dict[str, Any]:
    voice_path = Path("/etc/cipher/voice.conf")
    try:
        with open(voice_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def get_memory_config() -> dict[str, Any]:
    mem_path = Path("/etc/cipher/memory.conf")
    try:
        with open(mem_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def get_monitor_config() -> dict[str, Any]:
    mon_path = Path("/etc/cipher/monitor.conf")
    try:
        with open(mon_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def get_search_config() -> dict[str, Any]:
    s_path = Path("/etc/cipher/search.conf")
    try:
        with open(s_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}
