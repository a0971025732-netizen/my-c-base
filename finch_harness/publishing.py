"""Phase 1.8 PUBLISHING.

Every draft needs explicit human approval (`finch review`). After that:
- Reddit: `manual` (default) — the harness prints a publish package, a human posts it, then records the URL;
          `api` — PRAW posts the approved text (requires an approved Reddit Data API app + account creds).
- X:      always manual via web intent. Programmatic keyword-driven replies violate X automation rules and
          have been blocked by the API since 2026-02-23.
"""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from typing import Any
from urllib.parse import quote

from .models import Candidate, GateResult, OpportunityScore
from .store import Store

REDDIT_MIN_INTERVAL_S = int(os.environ.get("FINCH_REDDIT_MIN_INTERVAL_S", "600"))


def x_intent_url(tweet_id: str, text: str) -> str:
    return f"https://x.com/intent/post?in_reply_to={tweet_id}&text={quote(text)}"


def publish_order(rows: list[Any], strategy: dict[str, Any], already: Counter | None = None) -> list[Any]:
    """Priority: opportunity score, freshness, agent fit, momentum, audience fit, then community diversity."""
    cap = strategy["campaign"]["publish_max"]
    per_comm = strategy["campaign"]["max_per_community"]

    def key(r: Any) -> tuple:
        o = OpportunityScore.model_validate_json(r["opp_json"])
        return (-o.total, -o.freshness, -o.agent_fit, -o.momentum, -o.audience_fit)

    chosen, per = [], Counter(already or {})
    for r in sorted(rows, key=key):
        if len(chosen) >= cap:
            break
        comm = r["community"].lower()
        if per[comm] >= per_comm:
            continue
        per[comm] += 1
        chosen.append(r)
    return chosen


def approved_queue(store: Store, cid: int) -> list[Any]:
    rows = store.q(
        "SELECT d.*, c.platform, c.url AS thread_url, c.external_id AS thread_external_id, c.community, c.opp_json,"
        " c.data_json FROM drafts d JOIN candidates c ON c.id=d.candidate_id WHERE d.campaign_id=? AND d.status='approved'",
        (cid,),
    )
    published = store.publications(cid)
    already = Counter(p["community"].lower() for p in published)
    strategy = store.strategy(cid)
    remaining = dict(strategy)
    remaining["campaign"] = dict(strategy["campaign"], publish_max=strategy["campaign"]["publish_max"] - len(published))
    return publish_order(rows, remaining, already)


def _reddit_post(thread_id: str, text: str) -> tuple[str, str]:
    from .discovery import _reddit_client

    reddit = _reddit_client()
    sub = reddit.submission(id=thread_id)
    if sub.locked or sub.archived:
        raise RuntimeError("thread is locked/archived")
    comment = sub.reply(text)
    return f"https://www.reddit.com{comment.permalink}", comment.id


def publish(store: Store, cid: int, mode: str = "manual", dry_run: bool = False) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    last_api_post = 0.0
    for r in approved_queue(store, cid):
        if store.already_engaged(r["platform"], r["thread_external_id"]):
            store.set_draft(r["id"], status="skipped", reviewer_note="thread already engaged")
            continue
        item = {"draft_id": str(r["id"]), "platform": r["platform"], "thread": r["thread_url"], "text": r["text"]}
        if r["platform"] == "x":
            item["action"] = "MANUAL: open intent link, review, click Post, then `finch record-post`"
            item["intent_url"] = x_intent_url(r["thread_external_id"], r["text"])
        elif r["platform"] == "reddit" and mode == "api" and not dry_run:
            wait = REDDIT_MIN_INTERVAL_S - (time.time() - last_api_post)
            if last_api_post and wait > 0:
                time.sleep(wait)
            try:
                url, ext = _reddit_post(r["thread_external_id"], r["text"])
            except Exception as e:
                item["action"] = f"FAILED: {type(e).__name__}: {e}"
                out.append(item)
                continue
            last_api_post = time.time()
            store.add_publication(cid, r["id"], "reddit", r["thread_url"], r["thread_external_id"], url, ext, "api")
            store.set_draft(r["id"], status="published")
            item["action"] = f"POSTED {url}"
        else:
            item["action"] = "MANUAL: paste the text as a reply in the thread, then `finch record-post`"
        out.append(item)
    return out


def comment_id_from_url(platform: str, url: str) -> str | None:
    if platform == "x":
        m = re.search(r"/status/(\d+)", url)
    else:
        m = re.search(r"/comments/[^/]+/[^/]*/([a-z0-9]+)", url) or re.search(r"/comment/([a-z0-9]+)", url)
    return m.group(1) if m else None


def record_post(store: Store, draft_id: int, comment_url: str) -> int:
    d = store.q(
        "SELECT d.*, c.platform, c.url AS thread_url, c.external_id AS thread_external_id FROM drafts d"
        " JOIN candidates c ON c.id=d.candidate_id WHERE d.id=?",
        (draft_id,),
    )[0]
    if d["status"] not in ("approved",):
        raise ValueError(f"draft {draft_id} is '{d['status']}', only approved drafts can be recorded as posted")
    pid = store.add_publication(d["campaign_id"], draft_id, d["platform"], d["thread_url"], d["thread_external_id"],
                                comment_url, comment_id_from_url(d["platform"], comment_url), "manual")
    store.set_draft(draft_id, status="published")
    return pid


def review_summary(r: Any) -> str:
    cand = Candidate.model_validate_json(r["data_json"])
    gate = GateResult.model_validate_json(r["gate_json"]) if r["gate_json"] else None
    s = gate.scores if gate else None
    scores = (
        f"{s.total}/35 promo={s.promotional_intensity} agent_fit={s.agent_fit} conv_fit={s.conversation_fit}" if s else "unscored"
    )
    return (
        f"\n=== draft {r['id']}  [{r['platform']} / {r['community']}]  opp={r['opp_total']}  style={r['style']}  gate={scores}\n"
        f"thread: {r['thread_url']}\ntitle:  {cand.title or cand.body[:120]}\n--- reply ---\n{r['text']}\n"
    )
