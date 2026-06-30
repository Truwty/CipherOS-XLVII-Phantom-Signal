#!/usr/bin/env python3
"""CipherOS persistent memory — SQLite + ChromaDB vector store."""
import asyncio
import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RETENTION_DAYS: dict[str, int | None] = {
    "identity": None,
    "facts": None,
    "preferences": 365,
    "projects": 180,
    "conversations": 90,
    "cache": 7,
}


class MemoryStore:
    def __init__(self) -> None:
        self._data_dir = Path.home() / ".local/share/cipher/memory"
        self._db_path  = self._data_dir / "cipher_memory.db"
        self._chroma_dir = self._data_dir / "vector_store"
        self._db: sqlite3.Connection | None = None
        self._collection: Any | None = None

    async def initialize(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._init_sqlite)
        await asyncio.to_thread(self._init_chroma)
        logger.info("MemoryStore initialized.")

    def _init_sqlite(self) -> None:
        self._db = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id          TEXT PRIMARY KEY,
                content     TEXT NOT NULL,
                category    TEXT NOT NULL DEFAULT 'facts',
                tags        TEXT DEFAULT '[]',
                created_at  REAL NOT NULL,
                expires_at  REAL,
                access_count INTEGER DEFAULT 0,
                last_access  REAL
            );
            CREATE INDEX IF NOT EXISTS idx_category ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_created  ON memories(created_at);
            CREATE INDEX IF NOT EXISTS idx_expires  ON memories(expires_at);
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content, category, tags, content=memories, content_rowid=rowid
            );
        """)
        self._db.commit()

    def _init_chroma(self) -> None:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(self._chroma_dir))
            self._collection = client.get_or_create_collection(
                name="cipher_memories",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"ChromaDB collection has {self._collection.count()} entries.")
        except Exception as exc:
            logger.warning(f"ChromaDB unavailable: {exc}. Vector search disabled.")
            self._collection = None

    def _make_id(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _expires_at(self, category: str) -> float | None:
        days = _RETENTION_DAYS.get(category)
        if days is None:
            return None
        return time.time() + days * 86400

    async def add(
        self,
        content: str,
        category: str = "facts",
        tags: list[str] | None = None,
    ) -> str:
        mem_id = self._make_id(content + str(time.time()))
        expires = self._expires_at(category)
        tags_json = json.dumps(tags or [])
        now = time.time()

        def _write() -> None:
            assert self._db
            self._db.execute(
                "INSERT OR REPLACE INTO memories (id,content,category,tags,created_at,expires_at) "
                "VALUES (?,?,?,?,?,?)",
                (mem_id, content, category, tags_json, now, expires),
            )
            self._db.commit()

        await asyncio.to_thread(_write)

        if self._collection is not None:
            try:
                await asyncio.to_thread(
                    self._collection.add,
                    documents=[content],
                    ids=[mem_id],
                    metadatas=[{"category": category, "created_at": now}],
                )
            except Exception as exc:
                logger.debug(f"Chroma add failed: {exc}")

        return mem_id

    async def search(self, query: str, top_k: int = 20, category: str | None = None) -> list[dict]:
        results: list[dict] = []

        # Vector search
        if self._collection is not None:
            try:
                res = await asyncio.to_thread(
                    self._collection.query,
                    query_texts=[query],
                    n_results=min(top_k, max(1, self._collection.count())),
                    where={"category": category} if category else None,
                )
                docs = res.get("documents", [[]])[0]
                ids  = res.get("ids", [[]])[0]
                dists = res.get("distances", [[]])[0]
                for doc, mid, dist in zip(docs, ids, dists):
                    if dist < 0.5:
                        results.append({"id": mid, "content": doc, "score": 1 - dist, "source": "vector"})
            except Exception as exc:
                logger.debug(f"Vector search failed: {exc}")

        # FTS keyword search
        def _fts() -> list[dict]:
            assert self._db
            cat_filter = "AND m.category = ?" if category else ""
            params: list[Any] = [query.replace('"', '""')]
            if category:
                params.append(category)
            rows = self._db.execute(
                f"""SELECT m.id, m.content, m.category
                    FROM memories_fts f
                    JOIN memories m ON f.rowid = m.rowid
                    WHERE memories_fts MATCH ?
                    {cat_filter}
                    AND (m.expires_at IS NULL OR m.expires_at > ?)
                    LIMIT ?""",
                (*params, time.time(), top_k),
            ).fetchall()
            return [{"id": r["id"], "content": r["content"], "score": 0.6, "source": "fts"} for r in rows]

        try:
            fts_results = await asyncio.to_thread(_fts)
            seen = {r["id"] for r in results}
            for r in fts_results:
                if r["id"] not in seen:
                    results.append(r)
        except Exception as exc:
            logger.debug(f"FTS search failed: {exc}")

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def get_all(self, category: str | None = None, limit: int = 100) -> list[dict]:
        def _get() -> list[dict]:
            assert self._db
            where = "WHERE (expires_at IS NULL OR expires_at > ?)"
            params: list[Any] = [time.time()]
            if category:
                where += " AND category = ?"
                params.append(category)
            rows = self._db.execute(
                f"SELECT id, content, category, tags, created_at FROM memories {where} ORDER BY created_at DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
            return [dict(r) for r in rows]

        return await asyncio.to_thread(_get)

    async def delete(self, mem_id: str) -> None:
        def _del() -> None:
            assert self._db
            self._db.execute("DELETE FROM memories WHERE id=?", (mem_id,))
            self._db.commit()

        await asyncio.to_thread(_del)
        if self._collection:
            try:
                await asyncio.to_thread(self._collection.delete, ids=[mem_id])
            except Exception:
                pass

    async def count(self) -> int:
        def _count() -> int:
            assert self._db
            return self._db.execute(
                "SELECT COUNT(*) FROM memories WHERE expires_at IS NULL OR expires_at > ?",
                (time.time(),)
            ).fetchone()[0]
        return await asyncio.to_thread(_count)

    async def expire_old(self) -> int:
        def _expire() -> int:
            assert self._db
            cur = self._db.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
                (time.time(),)
            )
            self._db.commit()
            return cur.rowcount
        return await asyncio.to_thread(_expire)

    async def close(self) -> None:
        if self._db:
            await asyncio.to_thread(self._db.close)
