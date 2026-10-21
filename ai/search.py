"""Web search — DuckDuckGo + Wikipedia results, AI summary.

The AI provider behind the local proxy may not support Anthropic's
server-side web_search tool, so we search ourselves with DDGS
(DuckDuckGo, no API key needed) and let the AI summarize the results.
"""

import logging

from ddgs import DDGS

from ai.client import _client  # reuse the same provider/client
from config import AI_MAX_TOKENS, AI_MODEL

logger = logging.getLogger(__name__)

MAX_RESULTS = 8  # web results to fetch
MAX_NEWS = 5  # news results to fetch
RESULT_MAX_CHARS = 1500  # snippet length cap per result
FETCH_TOP_PAGES = 3  # top results whose full page content gets read


# ---------------------------------------------------------------------------
# Router: does this question need a web search?
# ---------------------------------------------------------------------------
def needs_web(query: str) -> bool:
    """Ask the AI whether the query needs fresh web results.

    Returns True for current events, news, prices, weather, scores, etc.
    Returns False for chat, opinions, coding help, math, definitions...
    """
    try:
        response = _client.messages.create(
            model=AI_MODEL,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Decide if this user message needs a live web search to answer "
                        "correctly. Answer with exactly one word:\n"
                        "- SEARCH if it's about current events, news, prices, weather, "
                        "sports scores, recent releases, or anything time-sensitive.\n"
                        "- CHAT if it can be answered from general knowledge, or it's "
                        "conversation, opinion, coding help, math, or a definition.\n\n"
                        f"MESSAGE: {query}"
                    ),
                }
            ],
        )
        verdict = next((b.text for b in response.content if b.type == "text"), "").strip().upper()
        return verdict.startswith("SEARCH")
    except Exception as exc:
        logger.warning("needs_web classifier failed, defaulting to CHAT: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Search providers (all free, no API keys)
# ---------------------------------------------------------------------------
def _ddg_text(query: str) -> list[dict]:
    """DuckDuckGo general web results."""
    try:
        with DDGS() as ddgs:
            return list(
                ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=MAX_RESULTS)
            )
    except Exception as exc:
        logger.error("DuckDuckGo text search failed: %s", exc)
        return []


def _ddg_news(query: str) -> list[dict]:
    """DuckDuckGo news results."""
    try:
        with DDGS() as ddgs:
            return list(
                ddgs.news(query, region="wt-wt", safesearch="moderate", max_results=MAX_NEWS)
            )
    except Exception as exc:
        logger.error("DuckDuckGo news search failed: %s", exc)
        return []


def _wikipedia(query: str) -> list[dict]:
    """Wikipedia REST search (free, no key) — good for facts/people/places."""
    import json
    import urllib.request

    results: list[dict] = []
    try:
        url = (
            "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch="
            + urllib.request.quote(query)
            + "&format=json&srlimit=3"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "telegram-ai-chatbot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            results.append(
                {
                    "title": title,
                    "href": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
                    "body": snippet.replace('<span class="searchmatch">', "").replace(
                        "</span>", ""
                    ),
                }
            )
    except Exception as exc:
        logger.error("Wikipedia search failed: %s", exc)
    return results


def _fetch_page(url: str, max_chars: int = 3000) -> str:
    """Fetch a web page and extract readable text (for deeper answers)."""
    import re
    import urllib.request

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "telegram-ai-chatbot/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read(500_000).decode("utf-8", errors="ignore")

        # Strip scripts, styles, tags — keep readable text
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        # Skip pages that are mostly boilerplate
        if len(text) < 200:
            return ""
        return text[:max_chars]
    except Exception as exc:
        logger.debug("Page fetch failed (%s): %s", url, exc)
        return ""


# ---------------------------------------------------------------------------
# The search engine
# ---------------------------------------------------------------------------
def search_web(query: str, include_news: bool = True, include_wiki: bool = True) -> str:
    """Search the web (DuckDuckGo + Wikipedia), read top pages, AI answers.

    Returns the answer with a Sources list. Falls back to a plain list of
    results if the AI summarization fails.
    """
    # --- 1. Gather results from all providers ----------------------------------
    results: list[dict] = _ddg_text(query)
    if include_news:
        results.extend(_ddg_news(query))
    if include_wiki:
        results.extend(_wikipedia(query))

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[dict] = []
    for r in results:
        href = r.get("href", "")
        if href and href not in seen:
            seen.add(href)
            unique.append(r)
    results = unique[: MAX_RESULTS + MAX_NEWS]

    if not results:
        return "🔍 I couldn't find any results for that."

    # --- 2. Read the top pages for deeper content -------------------------------
    # Snippets alone often miss the actual data (tables, numbers), so fetch
    # the top few pages and include their readable text.
    from concurrent.futures import ThreadPoolExecutor

    def load_result(i: int, r: dict) -> str:
        title = r.get("title", "")
        href = r.get("href", "")
        snippet = (r.get("body") or "")[:RESULT_MAX_CHARS]

        # Fetch full page content for the top hits only
        page_text = _fetch_page(href) if i <= FETCH_TOP_PAGES else ""

        entry = f"[{i}] {title}\n{href}\n{snippet}"
        if page_text:
            entry += f"\n\nPAGE CONTENT: {page_text}"
        return entry

    with ThreadPoolExecutor(max_workers=FETCH_TOP_PAGES + 2) as pool:
        context_parts = list(
            pool.map(lambda pair: load_result(pair[0], pair[1]), enumerate(results, start=1))
        )

    context = "\n\n".join(context_parts)

    # --- 3. Ask the AI to answer using only these results -----------------------
    try:
        response = _client.messages.create(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a search engine assistant. Below are web search results "
                        "for a query, including the full page content of the top results. "
                        "Write a clear, complete answer to the query using ONLY these results. "
                        "If a table, ranking, or numbers are asked for, include the actual data. "
                        "Cite sources inline like [1], [2]. Reply in the query's language.\n\n"
                        f"QUERY: {query}\n\n"
                        f"SEARCH RESULTS:\n{context}"
                    ),
                }
            ],
        )
        answer = next(
            (b.text for b in response.content if b.type == "text"),
            "",
        ).strip()
    except Exception as exc:
        logger.error("AI summarization failed: %s", exc)
        answer = ""  # fall back to raw results below

    # --- 4. Append sources, or return raw results as the answer ----------------
    sources = [f"🔗 [{r.get('title', 'source')}]({r.get('href', '')})" for r in results]
    source_block = "\n📚 *Sources:*\n" + "\n".join(sources)

    if not answer:
        # AI failed — give the user the raw results directly
        raw = "\n\n".join(
            f"🔗 [{r.get('title', '')}]({r.get('href', '')})\n{r.get('body', '')}" for r in results
        )
        return raw[:4000] + source_block

    return answer + source_block
