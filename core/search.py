# core/search.py
"""
Web search layer.
  Primary:  Tavily (if TAVILY_API_KEY is set)
  Fallback: DuckDuckGo via duckduckgo-search (no key needed)
Page content fetched with httpx + BeautifulSoup.
"""
from __future__ import annotations
import os
import re
import httpx
from bs4 import BeautifulSoup

TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")
_UA = "Mozilla/5.0 (compatible; ARIAResearch/2.1; +https://github.com/dhruv-2712/aria)"


def search(query: str, max_results: int = 5) -> list[dict]:
    """Return list of {title, url, snippet, content}."""
    if TAVILY_KEY:
        results = _tavily(query, max_results)
        if results:
            return results
    return _ddg(query, max_results)


def _tavily(query: str, max_results: int) -> list[dict]:
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key":            TAVILY_KEY,
                "query":              query,
                "max_results":        max_results,
                "search_depth":       "advanced",
                "include_raw_content": False,
            },
            timeout=15,
        )
        return [
            {
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "snippet": r.get("content", ""),
                "content": r.get("content", ""),
                "_source": "tavily",   # skip page fetch — Tavily content is final
            }
            for r in resp.json().get("results", [])
        ]
    except Exception as e:
        print(f"[Search] Tavily error: {e}")
        return []


def _ddg(query: str, max_results: int) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title", ""),
                    "url":     r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "content": r.get("body", ""),
                })
        return results
    except Exception as e:
        print(f"[Search] DuckDuckGo error: {e}")
        return []


def fetch_page(url: str, timeout: int = 4) -> str:
    """Fetch and clean page text. Returns '' on any failure."""
    if not url or url == "web_search":
        return ""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": _UA},
            timeout=timeout,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", text)[:3000]
    except Exception:
        return ""
