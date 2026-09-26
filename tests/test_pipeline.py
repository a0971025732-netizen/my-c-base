"""Offline end-to-end test of one campaign cycle (no network, no LLM)."""

from __future__ import annotations

import csv
import json
from datetime import timedelta

import pytest

from finch_harness import generation, measurement, optimize, publishing, quality_gate, scoring
from finch_harness.config import load_strategy
from finch_harness.models import AgentProfile, Candidate, QualityScores, utcnow
from finch_harness.store import Store

URL = "https://finch.example/agents/csv-cleaner"
GOOD = [4, 4, 4, 4, 4, 5, 4, 1]  # 29/35, promo 1


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    monkeypatch.setenv("FINCH_DISABLE_LLM", "1")


@pytest.fixture
def profile():
    return AgentProfile(
        name="CSV Cleaner",
        url=URL,
        category="data",
        keywords=["csv", "cleaning", "spreadsheet", "dedupe", "excel"],
        semantic_topics=["messy spreadsheet data", "data cleaning workflow"],
        subreddits=["excel", "datascience"],
        reddit_queries=["clean messy csv"],
    )


def cand(i, community="excel", hours=5, comments=8, title="How do I clean a messy CSV with duplicates in excel?", platform="reddit",
         body="Spreadsheet cleaning is killing me, any tool to dedupe csv?"):
    return Candidate(
        platform=platform, external_id=f"t{i}", url=f"https://www.reddit.com/r/{community}/comments/t{i}/x/",
        community=community, title=title, body=body,
        author=f"op{i}", created_at=utcnow() - timedelta(hours=hours), num_comments=comments, score=12,
        query="clean messy csv",
    )


def reply(n=0):
    return (
        f"For dedupe on a CSV that size I'd first normalise whitespace and casing in the key columns (TRIM/LOWER), "
        f"then use Remove Duplicates on the composite key rather than the whole row{'.' * (n + 1)} If it's a recurring job, "
        f"Power Query keeps the steps repeatable. Another option is {URL} which does the normalise+dedupe pass "
        f"in one go. (Disclosure: I'm with Finch.) Variant {n}: check for trailing zeros in IDs first."
    )


def test_freshness_curve():
    curve = load_strategy()["freshness_curve_hours"]
    assert scoring.freshness_fraction(0, curve) == 1.0
    assert 0.85 < scoring.freshness_fraction(12, curve) < 1.0
    assert scoring.freshness_fraction(10_000, curve) < 0.3
    assert scoring.freshness_fraction(None, curve) == 0.5


def test_weights_sum_to_100():
    assert sum(load_strategy()["scoring_weights"].values()) == 100


def test_hard_checks(profile):
    cfg = load_strategy()["quality_gate"]
    c = cand(1)
    assert quality_gate.hard_checks(reply(), profile, c, [], cfg) == []
    probs = quality_gate.hard_checks("Try this tool, it's great " * 10, profile, c, [], cfg)
    assert "missing the exact Agent URL" in probs and "missing affiliation disclosure" not in probs
    strict = {**cfg, "require_disclosure": True}
    assert "missing affiliation disclosure" in quality_gate.hard_checks("Try this tool " * 10, profile, c, [], strict)
    assert any("too similar" in p for p in quality_gate.hard_checks(reply(), profile, c, [reply()], cfg))
    xc = cand(2, platform="x")
    assert any("too long for X" in p for p in quality_gate.hard_checks(reply(), profile, xc, [], cfg))


def test_gate_thresholds(profile):
    cfg = load_strategy()["quality_gate"]
    c = cand(1)
    ok = QualityScores(**dict(zip(["relevance", "helpfulness", "specificity", "naturalness", "conversation_fit",
                                   "agent_fit", "platform_fit", "promotional_intensity"], GOOD)))
    assert quality_gate.evaluate(reply(), profile, c, [], cfg, ok).verdict == "PASS"
    assert quality_gate.evaluate(reply(), profile, c, [], cfg, ok.model_copy(update={"promotional_intensity": 3})).verdict == "REWRITE"
    assert quality_gate.evaluate(reply(), profile, c, [], cfg, ok.model_copy(update={"agent_fit": 2})).verdict == "REJECT"
    assert quality_gate.evaluate(reply(), profile, c, [], cfg).verdict == "REWRITE"  # no judge → human must score


def test_full_cycle(tmp_path, profile):
    store = Store(tmp_path / "t.db")
    cid = store.create_campaign(profile, load_strategy())
    # 4 in r/excel, 1 in r/datascience, 1 irrelevant
    for i in range(4):
        store.add_candidate(cid, cand(i))
    store.add_candidate(cid, cand(10, community="datascience"))
    store.add_candidate(cid, cand(11, community="cooking", title="Best pasta shape for pesto", hours=100, comments=0,
                                   body="Fusilli or trofie? My nonna says trofie."))
    stats = scoring.score_campaign(store, cid)
    assert stats["scored"] == 6
    qualified = store.candidates(cid, "qualified")
    assert "t11" not in {r["external_id"] for r in qualified}

    for n, r in enumerate(qualified):
        did, verdict, reasons = generation.add_manual_draft(
            store, cid, r["id"], "direct_answer", reply(n).replace("Variant", f"Case {n*7919} variant"),
            dict(zip(["relevance", "helpfulness", "specificity", "naturalness", "conversation_fit", "agent_fit",
                      "platform_fit", "promotional_intensity"], GOOD)),
        )
        store.set_draft(did, status="approved")

    items = publishing.publish(store, cid, mode="manual")
    per_comm = {}
    for it in items:
        per_comm[it["thread"].split("/r/")[1].split("/")[0]] = per_comm.get(it["thread"].split("/r/")[1].split("/")[0], 0) + 1
        assert it["action"].startswith("MANUAL")
    assert max(per_comm.values()) <= load_strategy()["campaign"]["max_per_community"]

    for it in items:
        pid = publishing.record_post(store, int(it["draft_id"]), it["thread"] + "c0mment/")
        store.add_metric(pid, 5, 2, True)
    assert all(store.already_engaged("reddit", r["thread_external_id"]) for r in store.publications(cid))

    csv_path = tmp_path / "conv.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, ["thread_url", "day", "clicks", "trials", "usage_events"])
        w.writeheader()
        w.writerow({"thread_url": items[0]["thread"], "day": "2026-09-26", "clicks": 7, "trials": 2, "usage_events": 1})
    assert measurement.import_conversions(store, cid, csv_path) == 1

    findings, summary = optimize.analyze(store, cid)
    assert summary["published"] == len(items)
    assert {f.classification for f in findings} <= {"KEEP", "CHANGE", "TEST", "DROP"}
    report = optimize.render_report(findings, summary)
    assert "Funnel" in report and json.dumps(summary["outcomes"])


def test_x_intent_and_comment_ids():
    u = publishing.x_intent_url("123", "hi & bye")
    assert "in_reply_to=123" in u and "hi%20%26%20bye" in u
    assert publishing.comment_id_from_url("x", "https://x.com/a/status/987") == "987"
    assert publishing.comment_id_from_url("reddit", "https://www.reddit.com/r/excel/comments/abc/title/def12/") == "def12"


def test_style_choice_rotates():
    from collections import Counter

    from finch_harness.models import OpportunityScore

    strategy = load_strategy()
    opp = OpportunityScore(relevance=1, intent=1, freshness=1, momentum=1, audience_fit=1, agent_fit=1, naturalness=1,
                           total=7, intent_type="question")
    used = Counter()
    picks = []
    for _ in range(4):
        s = generation.choose_style(strategy, used, opp)
        used[s] += 1
        picks.append(s)
    assert len(set(picks)) == 2  # alternates between the two question styles


def test_registry_loads_and_verifies():
    from finch_harness import registry

    health = registry.verify(network=False)
    caps = {h.capability for h in health}
    assert {"reddit_search", "reddit_comment_publish", "x_search", "x_reply_publish", "web_search"} <= caps
    x_reply = next(h for h in health if h.capability == "x_reply_publish")
    assert not x_reply.ok and "MANUAL REVIEW REQUIRED" in x_reply.problems
