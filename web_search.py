"""
Web search for the chat ``/search`` command.

Uses SerpApi's officially maintained ``serpapi`` client (``pip install serpapi``).
The legacy ``google-search-results`` package (``from serpapi import GoogleSearch``)
is no longer developed and fails to build on recent Python versions; both packages
install a module named ``serpapi``, so only one of them may be installed.
"""

import os
from typing import Any, Dict, List, Optional

SEARCH_TIMEOUT_SECONDS = 20
MAX_RESULTS = 5


class WebSearchError(Exception):
    """Raised when the search provider is misconfigured or the request fails."""


def get_serpapi_key() -> str:
    return os.environ.get("SERPAPI_KEY") or os.environ.get("SERPAPI_API_KEY") or ""


def search_web(query: str, num_results: int = MAX_RESULTS, api_key: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Run a Google web search through SerpApi.

    Returns a list of ``{"title", "snippet", "link"}`` dictionaries (possibly empty).
    Raises :class:`WebSearchError` on missing configuration or provider errors.
    """
    api_key = api_key or get_serpapi_key()
    if not api_key:
        raise WebSearchError(
            "SerpAPI key not found. Add SERPAPI_KEY to your .env file or environment variables."
        )

    try:
        import serpapi
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise WebSearchError("The 'serpapi' package is not installed. Run: pip install serpapi") from exc

    if not hasattr(serpapi, "Client"):
        raise WebSearchError(
            "The legacy 'google-search-results' package is installed. "
            "Run: pip uninstall google-search-results && pip install serpapi"
        )

    try:
        client = serpapi.Client(api_key=api_key, timeout=SEARCH_TIMEOUT_SECONDS)
        results: Any = client.search({"engine": "google", "q": query, "num": num_results})
    except Exception as exc:
        raise WebSearchError(f"Web search failed: {exc}") from exc

    data = results.as_dict() if hasattr(results, "as_dict") else dict(results)
    if data.get("error"):
        raise WebSearchError(f"Web search failed: {data['error']}")

    return [
        {
            "title": item.get("title", "No title"),
            "snippet": item.get("snippet", "No description"),
            "link": item.get("link", "#"),
        }
        for item in (data.get("organic_results") or [])[:num_results]
    ]


def format_search_results(query: str, results: List[Dict[str, str]]) -> str:
    """Format search results as context text for the AI model."""
    if not results:
        return "\n\nNo search results found.\n\n"
    lines = [f"\n\nWeb search results for query: {query}\n"]
    for index, item in enumerate(results, 1):
        lines.append(f"{index}. {item['title']}\n{item['snippet']}\nURL: {item['link']}\n")
    return "\n".join(lines) + "\n"
