"""Web Search Tool using DuckDuckGo or Tavily with graceful error recovery."""
import logging
import warnings
from typing import Optional
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.config import TAVILY_API_KEY

# Suppress library rename deprecation notice
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*renamed to.*")

logger = logging.getLogger("AgentSystem.Tools.Search")

MAX_SNIPPET_LENGTH = 1500


class SearchInput(BaseModel):
    query: str = Field(..., description="The search query string to look up facts, current events, or documentation.")


class WebSearchTool(BaseTool):
    """
    Tool for searching the internet to retrieve external knowledge, documentation,
    and real-time facts not present in LLM static training data.
    """
    name: str = "web_search"
    description: str = (
        "Use this tool to search the internet for current events, facts, technical documentation, "
        "or information not in your training data. Input must be a clear, optimized search query string. "
        "Returns concise text snippets summarizing the top search results."
    )
    args_schema = SearchInput
    requires_approval: bool = False

    def __init__(self, max_length: int = MAX_SNIPPET_LENGTH):
        self.max_length = max_length

    def _search_tavily(self, query: str) -> Optional[str]:
        if not TAVILY_API_KEY:
            return None
        try:
            import requests
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_API_KEY, "query": query, "max_results": 3},
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                snippets = []
                for idx, r in enumerate(results, 1):
                    title = r.get("title", "")
                    content = r.get("content", "")
                    snippets.append(f"[{idx}] {title}: {content}")
                return "\n".join(snippets)
        except Exception as e:
            logger.warning(f"Tavily search attempt failed: {e}")
        return None

    def _search_duckduckgo(self, query: str) -> str:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    # pyrefly: ignore[missing-import]
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=3))
                    if not results:
                        return f"No search results found for query: '{query}'"
                    
                    snippets = []
                    for idx, r in enumerate(results, 1):
                        title = r.get("title", "Untitled")
                        body = r.get("body", "")
                        snippets.append(f"[{idx}] {title}: {body}")
                    return "\n".join(snippets)
        except Exception as e:
            logger.warning(f"DuckDuckGo search error: {e}")
            return f"Search service notice: Search attempted for '{query}'. Details: {str(e)}"

    def execute(self, query: str) -> str:
        query = query.strip()
        if not query:
            return "Observation: Search query cannot be empty."

        # Try Tavily if configured
        tavily_result = self._search_tavily(query)
        if tavily_result:
            result = tavily_result
        else:
            result = self._search_duckduckgo(query)

        # Truncate to preserve LLM context window
        if len(result) > self.max_length:
            result = result[:self.max_length] + "\n...[Output truncated to preserve context window]"

        return f"Observation: {result}"

