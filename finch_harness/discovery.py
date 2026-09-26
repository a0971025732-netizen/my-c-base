"""Phase 1.3 DISCOVER CONVERSATIONS: Reddit (PRAW / public JSON fallback), X (Tweepy), web (import)."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .models import AgentProfile, Candidate
from .store import Store

USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "finch-harness/0.1 (transparent outbound research)")


# ---------------------------------------------------------------- Reddit
def _reddit_client():
    import praw

    kwargs: dict[str, Any] = dict(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=USER_AGENT,
    )
    if os.environ.get("REDDIT_USERNAME"):
        kwargs.update(username=os.environ["REDDIT_USERNAME"], password=os.environ["REDDIT_PASSWORD"])
    return praw.Reddit(**kwargs)


def reddit_api_configured() -> bool:
    return bool(os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"))


def _submission_to_candidate(s: Any, query: str, top_n: int = 5) -> Candidate:
    top: list[str] = []
    try:
        s.comment_sort = "top"
        s.comments.replace_more(limit=0)
        top = [c.body[:500] for c in list(s.comments)[:top_n]]
    except Exception:
        pass
    return Candidate(
        platform="reddit",
        external_id=s.id,
        url=f"https://www.reddit.com{s.permalink}",
        community=str(s.subreddit),
        title=s.title,
        body=(s.selftext or "")[:4000],
        author=str(s.author) if s.author else "",
        created_at=datetime.fromtimestamp(s.created_utc, tz=timezone.utc),
        num_comments=s.num_comments,
        score=s.score,
        query=query,
        top_comments=top,
        locked=bool(s.locked or s.archived),
    )


def _json_to_candidate(d: dict[str, Any], query: str) -> Candidate:
    return Candidate(
        platform="reddit",
        external_id=d["id"],
        url=f"https://www.reddit.com{d['permalink']}",
        community=d.get("subreddit", ""),
        title=d.get("title", ""),
        body=(d.get("selftext") or "")[:4000],
        author=d.get("author", ""),
        created_at=datetime.fromtimestamp(d["created_utc"], tz=timezone.utc),
        num_comments=d.get("num_comments", 0),
        score=d.get("score", 0),
        query=query,
        locked=bool(d.get("locked") or d.get("archived")),
    )


def search_reddit(query: str, subreddit: str | None, cfg: dict[str, Any]) -> list[Candidate]:
    limit = cfg.get("per_query_limit", 25)
    if reddit_api_configured():
        reddit = _reddit_client()
        target = reddit.subreddit(subreddit or "all")
        return [
            _submission_to_candidate(s, query)
            for s in target.search(query, sort=cfg.get("sort", "new"), time_filter=cfg.get("time_filter", "week"), limit=limit)
        ]
    # read-only public JSON fallback (rate-limited; be polite)
    import httpx

    base = f"https://www.reddit.com/r/{subreddit}/search.json" if subreddit else "https://www.reddit.com/search.json"
    params = {"q": query, "sort": cfg.get("sort", "new"), "t": cfg.get("time_filter", "week"), "limit": limit}
    if subreddit:
        params["restrict_sr"] = "1"
    resp = httpx.get(base, params=params, headers={"User-Agent": USER_AGENT}, timeout=20)
    resp.raise_for_status()
    time.sleep(2)
    return [_json_to_candidate(ch["data"], query) for ch in resp.json()["data"]["children"]]


# ---------------------------------------------------------------- X
def x_api_configured() -> bool:
    return bool(os.environ.get("X_BEARER_TOKEN"))


def search_x(query: str, cfg: dict[str, Any]) -> list[Candidate]:
    import tweepy

    client = tweepy.Client(bearer_token=os.environ["X_BEARER_TOKEN"], wait_on_rate_limit=True)
    q = query
    for extra in cfg.get("exclude", []):
        if extra not in q:
            q += f" {extra}"
    if cfg.get("lang") and "lang:" not in q:
        q += f" lang:{cfg['lang']}"
    resp = client.search_recent_tweets(
        query=q,
        max_results=max(10, min(cfg.get("max_results", 25), 100)),
        tweet_fields=["created_at", "public_metrics", "conversation_id", "author_id", "reply_settings"],
        expansions=["author_id"],
        user_fields=["username"],
    )
    users = {u.id: u.username for u in (resp.includes or {}).get("users", [])}
    out = []
    for t in resp.data or []:
        m = t.public_metrics or {}
        username = users.get(t.author_id, "i")
        out.append(
            Candidate(
                platform="x",
                external_id=str(t.id),
                url=f"https://x.com/{username}/status/{t.id}",
                community="x",
                body=t.text,
                author=username,
                created_at=t.created_at,
                num_comments=m.get("reply_count", 0),
                score=m.get("like_count", 0) + m.get("retweet_count", 0),
                query=query,
                locked=getattr(t, "reply_settings", "everyone") not in (None, "everyone"),
            )
        )
    return out


# ---------------------------------------------------------------- orchestration
def plan_queries(profile: AgentProfile, cfg: dict[str, Any]) -> Iterator[tuple[str, str | None, str]]:
    """Yield (platform, community, query). Mix global and subreddit-scoped searches."""
    subs = profile.subreddits or cfg["reddit"].get("seed_subreddits", [])
    rq = profile.reddit_queries or profile.keywords[:10]
    for q in rq:
        yield "reddit", None, q
    for i, sub in enumerate(subs):
        # rotate queries through subreddits to stay diverse without exploding call volume
        yield "reddit", sub, rq[i % len(rq)] if rq else profile.name
    for q in profile.x_queries:
        yield "x", "x", q


def discover(store: Store, cid: int, platforms: set[str], max_candidates: int | None = None) -> dict[str, int]:
    profile = store.profile(cid)
    strategy = store.strategy(cid)
    cfg = strategy["discovery"]
    target_hi = max_candidates or strategy["campaign"]["candidates_target"][1]
    added = 0
    stats = {"queries": 0, "errors": 0, "added": 0, "skipped_engaged": 0}
    for platform, community, query in plan_queries(profile, cfg):
        if platform not in platforms or added >= target_hi:
            continue
        if platform == "x" and not x_api_configured():
            continue
        stats["queries"] += 1
        try:
            results = search_reddit(query, community, cfg["reddit"]) if platform == "reddit" else search_x(query, cfg["x"])
        except Exception as e:
            store.log_query(cid, platform, query, community or "", 0, f"{type(e).__name__}: {e}")
            stats["errors"] += 1
            continue
        n = 0
        for c in results:
            if store.already_engaged(c.platform, c.external_id):
                stats["skipped_engaged"] += 1
                continue
            age = c.age_hours()
            if c.locked or (age is not None and age > cfg["max_post_age_hours"]):
                continue
            if store.add_candidate(cid, c):
                n += 1
                added += 1
        store.log_query(cid, platform, query, community or "", n)
    stats["added"] = added
    return stats


def import_candidates(store: Store, cid: int, path: str | Path) -> int:
    """Import candidates found by other tools (web search, MCP servers, manual research).

    JSON list of objects with at least platform, external_id, url; other Candidate fields optional.
    """
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    n = 0
    for r in rows:
        c = Candidate.model_validate(r)
        if not store.already_engaged(c.platform, c.external_id) and store.add_candidate(cid, c):
            n += 1
    return n
