#!/usr/bin/env python3
"""CipherOS web search — DuckDuckGo with async content fetching."""
import asyncio
import logging
import sys
from typing import Any

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.config_loader import get_search_config

logger = logging.getLogger(__name__)


class SearchEngine:
    def __init__(self) -> None:
        self._cfg = get_search_config()

    async def search(self, query: str, mode: str = "search") -> dict[str, Any]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return {"error": "duckduckgo_search not installed", "results": []}

        cfg = self._cfg.get("modes", {}).get(mode, {})
        max_results  = cfg.get("max_results", 10)
        fetch_content = cfg.get("fetch_content", True)
        time_filter  = cfg.get("time_filter") if mode == "news" else None

        try:
            results: list[dict] = []
            with DDGS(timeout=15) as ddgs:
                if mode == "news":
                    raw = list(ddgs.news(query, max_results=max_results, timelimit=time_filter))
                else:
                    raw = list(ddgs.text(query, max_results=max_results))

            for r in raw:
                results.append({
                    "title":   r.get("title", ""),
                    "url":     r.get("href") or r.get("url", ""),
                    "snippet": r.get("body") or r.get("description", ""),
                })

            if fetch_content and results:
                results = await self._enrich_results(results)

            threshold = self._cfg.get("content", {}).get("panel_threshold", 120)
            total_chars = sum(len(r.get("content", r.get("snippet", ""))) for r in results)
            display_mode = "panel" if total_chars > threshold else "inline"

            return {
                "query": query,
                "mode": mode,
                "display": display_mode,
                "count": len(results),
                "results": results,
            }
        except Exception as exc:
            logger.error(f"Search error: {exc}")
            return {"error": str(exc), "query": query, "results": []}

    async def _enrich_results(self, results: list[dict]) -> list[dict]:
        """Fetch page content for top 3 results in parallel."""
        max_chars = self._cfg.get("content", {}).get("max_page_chars", 5000)
        timeout   = self._cfg.get("content", {}).get("fetch_timeout", 10)

        async def _fetch(result: dict) -> dict:
            url = result.get("url", "")
            if not url:
                return result
            try:
                import httpx
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "lxml")
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    text = " ".join(soup.get_text(separator=" ").split())
                    result["content"] = text[:max_chars]
            except Exception:
                result["content"] = result.get("snippet", "")
            return result

        top = results[:3]
        rest = results[3:]
        enriched = await asyncio.gather(*[_fetch(r) for r in top], return_exceptions=True)
        final = []
        for r in enriched:
            if isinstance(r, dict):
                final.append(r)
        return final + rest
