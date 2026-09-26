"""Measurement: engagement + author response (API), Finch clicks/trials/usage (CSV import)."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

from .models import Candidate
from .store import Store


def _reddit_metrics(comment_id: str, thread_author: str) -> dict[str, Any]:
    from .discovery import _reddit_client

    c = _reddit_client().comment(id=comment_id)
    c.refresh()
    c.replies.replace_more(limit=0)
    replies = list(c.replies)
    return {
        "score": c.score,
        "replies": len(replies),
        "author_replied": any(str(r.author) == thread_author for r in replies if r.author),
        "removed": c.body in ("[removed]", "[deleted]"),
    }


def _x_metrics(tweet_id: str, thread_author: str) -> dict[str, Any]:
    import tweepy

    client = tweepy.Client(bearer_token=os.environ["X_BEARER_TOKEN"], wait_on_rate_limit=True)
    t = client.get_tweet(tweet_id, tweet_fields=["public_metrics", "conversation_id"]).data
    m = t.public_metrics or {}
    author_replied = None
    try:
        r = client.search_recent_tweets(
            query=f"conversation_id:{t.conversation_id} from:{thread_author} is:reply", max_results=10
        )
        author_replied = bool(r.data)
    except Exception:
        pass
    return {
        "score": m.get("like_count", 0) + m.get("retweet_count", 0) + m.get("quote_count", 0),
        "replies": m.get("reply_count", 0),
        "author_replied": author_replied,
        "impressions": m.get("impression_count"),
    }


def measure(store: Store, cid: int) -> list[dict[str, Any]]:
    out = []
    for p in store.publications(cid):
        cand = Candidate.model_validate_json(p["data_json"])
        row: dict[str, Any] = {"publication_id": p["id"], "platform": p["platform"], "url": p["comment_url"]}
        if not p["comment_external_id"]:
            row["error"] = "no comment id recorded"
            out.append(row)
            continue
        try:
            if p["platform"] == "reddit":
                m = _reddit_metrics(p["comment_external_id"], cand.author)
            elif p["platform"] == "x":
                m = _x_metrics(p["comment_external_id"], cand.author)
            else:
                continue
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
            out.append(row)
            continue
        store.add_metric(p["id"], m.get("score"), m.get("replies"), m.get("author_replied"), m)
        row.update(m)
        out.append(row)
    return out


def import_conversions(store: Store, cid: int, path: str | Path) -> int:
    """CSV columns: comment_url or thread_url (optional), day, clicks, trials, usage_events.

    Rows that cannot be matched to a publication are stored at campaign level.
    """
    pubs = store.publications(cid)
    by_url = {}
    for p in pubs:
        by_url[p["thread_url"]] = p["id"]
        if p["comment_url"]:
            by_url[p["comment_url"]] = p["id"]
    n = 0
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pid = by_url.get(r.get("comment_url") or "") or by_url.get(r.get("thread_url") or "")
            store.add_conversion(cid, pid, r.get("day"), int(r.get("clicks") or 0), int(r.get("trials") or 0),
                                 int(r.get("usage_events") or 0), source=str(path))
            n += 1
    return n
