"""Phase 1.10 POST-CAMPAIGN OPTIMIZATION → KEEP / CHANGE / TEST / DROP findings + campaign report."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from .models import Candidate, OpportunityScore
from .store import Store

MIN_SAMPLE = 3  # below this, a finding is at most TEST


@dataclass
class Finding:
    area: str
    classification: str  # KEEP | CHANGE | TEST | DROP
    finding: str
    recommendation: dict[str, Any] = field(default_factory=dict)


def _outcome(store: Store, pub: Any) -> dict[str, float]:
    m = store.latest_metric(pub["id"])
    conv = store.q(
        "SELECT COALESCE(SUM(clicks),0) c, COALESCE(SUM(trials),0) t, COALESCE(SUM(usage_events),0) u"
        " FROM conversions WHERE publication_id=?",
        (pub["id"],),
    )[0]
    return {
        "score": (m["score"] or 0) if m else 0,
        "replies": (m["replies"] or 0) if m else 0,
        "author_replied": (m["author_replied"] or 0) if m else 0,
        "clicks": conv["c"],
        "trials": conv["t"],
        "usage": conv["u"],
        "measured": 1 if m else 0,
    }


def engagement(o: dict[str, float]) -> float:
    """Single number for ranking: conversions dominate, author reply is a strong quality signal."""
    return o["usage"] * 10 + o["trials"] * 5 + o["clicks"] * 2 + o["author_replied"] * 3 + o["replies"] + max(o["score"], 0) * 0.5


def _age_bucket(h: float | None) -> str:
    if h is None:
        return "unknown"
    return "<6h" if h < 6 else "6-24h" if h < 24 else "1-3d" if h < 72 else "3-7d"


def _classify(area: str, groups: dict[str, list[float]], label: str) -> list[Finding]:
    stats = {k: (mean(v), len(v)) for k, v in groups.items() if v}
    if not stats:
        return []
    overall = mean(x for v in groups.values() for x in v) or 0.0
    out = []
    for k, (avg, n) in sorted(stats.items(), key=lambda t: -t[1][0]):
        if n < MIN_SAMPLE:
            cls = "TEST"
        elif avg >= overall * 1.25 and avg > 0:
            cls = "KEEP"
        elif avg == 0 or avg < overall * 0.5:
            cls = "DROP"
        else:
            cls = "CHANGE" if avg < overall else "KEEP"
        out.append(Finding(area, cls, f"{label} '{k}': avg engagement {avg:.2f} over {n} (campaign avg {overall:.2f})",
                           {"key": k, "avg": round(avg, 3), "n": n}))
    return out


def analyze(store: Store, cid: int) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []

    # Discovery: query yield (qualified / results) from query log + candidate statuses
    qrows = store.q("SELECT platform, community, query, n_results, error FROM queries WHERE campaign_id=?", (cid,))
    cand_rows = store.candidates(cid)
    qualified_by_query: dict[str, int] = defaultdict(int)
    for r in cand_rows:
        if r["status"] in ("qualified", "drafted"):
            qualified_by_query[r["query"]] += 1
    seen = set()
    for q in qrows:
        if q["query"] in seen:
            continue
        seen.add(q["query"])
        total = sum(x["n_results"] for x in qrows if x["query"] == q["query"])
        qual = qualified_by_query.get(q["query"], 0)
        if q["error"]:
            findings.append(Finding("discovery", "CHANGE", f"query '{q['query']}' errored: {q['error']}", {"query": q["query"]}))
        elif total == 0:
            findings.append(Finding("discovery", "DROP", f"query '{q['query']}' returned nothing", {"query": q["query"]}))
        elif qual == 0 and total >= 5:
            findings.append(Finding("discovery", "DROP", f"query '{q['query']}': {total} results, 0 qualified", {"query": q["query"]}))
        elif qual / max(total, 1) >= 0.3:
            findings.append(Finding("discovery", "KEEP", f"query '{q['query']}': {qual}/{total} qualified", {"query": q["query"]}))

    # Qualification funnel vs. baseline targets
    strategy = store.strategy(cid)
    n_c, n_q = len(cand_rows), sum(r["status"] in ("qualified", "drafted") for r in cand_rows)
    lo, hi = strategy["campaign"]["candidates_target"]
    if n_c < lo:
        findings.append(Finding("discovery", "CHANGE", f"only {n_c} candidates (target {lo}-{hi}): widen time_filter or add subreddits",
                                {"discovery.reddit.time_filter": "month"}))
    if n_c and n_q / n_c < 0.15:
        findings.append(Finding("discovery", "CHANGE", f"qualification rate {n_q}/{n_c} is low: refine queries toward intent",
                                {"campaign.qualify_min_score": strategy["campaign"]["qualify_min_score"]}))

    # Outcome-based analyses
    pubs = store.publications(cid)
    by_platform, by_comm, by_style, by_age, by_intent = (defaultdict(list) for _ in range(5))
    outcomes = []
    for p in pubs:
        o = _outcome(store, p)
        e = engagement(o)
        cand = Candidate.model_validate_json(p["data_json"])
        opp = OpportunityScore.model_validate_json(
            store.q("SELECT opp_json FROM candidates WHERE campaign_id=? AND external_id=?", (cid, p["thread_external_id"]))[0]["opp_json"]
        )
        by_platform[p["platform"]].append(e)
        by_comm[p["community"]].append(e)
        by_style[p["style"]].append(e)
        by_age[_age_bucket(cand.age_hours(now=_parse(p["published_at"])))].append(e)
        by_intent[opp.intent_type or "unknown"].append(e)
        outcomes.append({"publication_id": p["id"], "platform": p["platform"], "community": p["community"],
                         "style": p["style"], "url": p["comment_url"], "engagement": round(e, 2), **o})

    findings += _classify("platform", by_platform, "platform")
    findings += _classify("community", by_comm, "community")
    findings += _classify("content", by_style, "style")
    findings += _classify("timing", by_age, "post age at publish")
    findings += _classify("conversion", by_intent, "intent type")

    unmeasured = [o for o in outcomes if not o["measured"]]
    if unmeasured:
        findings.append(Finding("measurement", "CHANGE", f"{len(unmeasured)} publications have no metrics yet: run `finch measure`"))

    for f in findings:
        store.add_finding(cid, f.area, f.classification, f.finding, f.recommendation)

    summary = {
        "campaign_id": cid,
        "agent": store.campaign(cid)["agent_name"],
        "candidates": n_c,
        "qualified": n_q,
        "drafts_passed": len(store.q("SELECT 1 FROM drafts WHERE campaign_id=? AND verdict='PASS'", (cid,))),
        "published": len(pubs),
        "outcomes": outcomes,
        "style_bias": {k: round(mean(v), 3) for k, v in by_style.items() if len(v) >= MIN_SAMPLE},
    }
    return findings, summary


def _parse(ts: str):
    from datetime import datetime

    return datetime.fromisoformat(ts)


def render_report(findings: list[Finding], summary: dict[str, Any]) -> str:
    lines = [
        f"# Campaign {summary['campaign_id']} — {summary['agent']}",
        "",
        f"Funnel: {summary['candidates']} candidates → {summary['qualified']} qualified → "
        f"{summary['drafts_passed']} passed gate → {summary['published']} published",
        "",
        "## Findings",
        "",
        "| Area | Class | Finding |",
        "| --- | --- | --- |",
    ]
    for f in findings:
        lines.append(f"| {f.area} | **{f.classification}** | {f.finding} |")
    lines += ["", "## Publications", "", "```json", json.dumps(summary["outcomes"], indent=2), "```"]
    return "\n".join(lines)
