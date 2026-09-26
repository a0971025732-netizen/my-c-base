"""Phase 1.2 LOAD AGENT: read the Finch Agent URL and build the Agent Profile."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from . import llm
from .models import AgentProfile

STOPWORDS = set(
    """a an and are as at be by can for from has have in into is it its of on or that the this to with your you
    our we will all any more most use using used via get make just also than then them they their what when which
    who how why not no yes do does agent agents finch free try now new one""".split()
)


def fetch_page(url: str) -> dict[str, str]:
    import httpx
    from bs4 import BeautifulSoup

    resp = httpx.get(url, timeout=20, follow_redirects=True, headers={"User-Agent": "finch-harness/0.1"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    def meta(*names: str) -> str:
        for n in names:
            tag = soup.find("meta", attrs={"name": n}) or soup.find("meta", attrs={"property": n})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return ""

    jsonld = [s.get_text() for s in soup.find_all("script", attrs={"type": "application/ld+json"})]
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    return {
        "title": (soup.title.get_text().strip() if soup.title else "") or meta("og:title"),
        "description": meta("description", "og:description", "twitter:description"),
        "jsonld": "\n".join(jsonld)[:5000],
        "text": text[:20000],
    }


def keywords(text: str, n: int = 15) -> list[str]:
    words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9+#-]{2,}", text.lower()) if w not in STOPWORDS]
    return [w for w, _ in Counter(words).most_common(n)]


class _ProfileOut(BaseModel):
    name: str
    category: str
    capabilities: list[str]
    use_cases: list[str]
    target_users: list[str]
    free_usage: str = Field(description="Free usage allowance as stated on the page, or 'unknown'")
    keywords: list[str]
    semantic_topics: list[str] = Field(description="Conversation topics where this agent is genuinely useful")
    adjacent_topics: list[str] = Field(description="Neighbouring topics where people discuss the underlying problem")
    subreddits: list[str] = Field(description="8-20 subreddit names (no r/ prefix) where target users talk")
    reddit_queries: list[str] = Field(description="10-20 Reddit search queries covering questions, comparisons, workflows, experiences")
    x_queries: list[str] = Field(description="6-12 X recent-search queries using X operators, e.g. '(\"best tool\" OR \"how do I\") topic -is:retweet lang:en'")


PROFILE_SYSTEM = (
    "You build marketing-safe profiles of AI agents for a transparent outbound program. "
    "Extract only what the page supports; write 'unknown' rather than inventing facts. "
    "Queries must target conversations where the agent would be genuinely useful: questions, tool recommendations, "
    "workflow and technical discussions, comparisons, experience sharing, project building, education, emerging topics. "
    "Do not require the agent's own keywords to appear in a query."
)


def build_profile(url: str, overrides: dict[str, Any] | None = None, page: dict[str, str] | None = None) -> AgentProfile:
    if page is None:
        try:
            page = fetch_page(url)
        except Exception as e:  # network blocked, 4xx, etc.
            page = {"title": "", "description": "", "jsonld": "", "text": "", "error": f"{type(e).__name__}: {e}"}

    data: dict[str, Any] | None = None
    if page.get("text") or page.get("description"):
        out = llm.structured(
            PROFILE_SYSTEM,
            f"Agent URL: {url}\n\nPage title: {page['title']}\nDescription: {page['description']}\n"
            f"JSON-LD: {page['jsonld']}\n\nPage text:\n{page['text']}",
            _ProfileOut,
        )
        if out is not None:
            data = out.model_dump()

    if data is None:
        blob = " ".join([page.get("title", ""), page.get("description", ""), page.get("text", "")[:5000]])
        kws = keywords(blob)
        data = {
            "name": (page.get("title") or url.rstrip("/").rsplit("/", 1)[-1]).split("|")[0].strip(),
            "category": "",
            "keywords": kws,
            "semantic_topics": kws[:8],
            "reddit_queries": [" ".join(kws[i : i + 2]) for i in range(0, min(len(kws), 12), 2)],
            "x_queries": [f"{k} -is:retweet lang:en" for k in kws[:6]],
        }

    if overrides:
        for k, v in overrides.items():
            if isinstance(v, list) and isinstance(data.get(k), list):
                data[k] = list(dict.fromkeys(v + data[k]))
            elif v:
                data[k] = v
    data["url"] = url  # canonical, never rewritten
    return AgentProfile.model_validate(data)


def load_overrides(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text) if str(path).endswith(".json") else yaml.safe_load(text)
