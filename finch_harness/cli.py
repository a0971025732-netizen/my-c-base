"""finch — command-line entry point for the outbound growth harness.

Typical campaign:
    finch harness verify
    finch campaign start <FINCH_AGENT_URL>          # 1.2 load agent → campaign id
    finch discover <cid>                            # 1.3
    finch score <cid>                               # 1.5
    finch draft <cid>                               # 1.6 + 1.7
    finch review <cid>                              # human approval (required)
    finch publish <cid> [--mode api]                # 1.8
    finch record-post <draft_id> <comment_url>      # after manual posts
    finch measure <cid>; finch import-conversions <cid> finch.csv
    finch analyze <cid>                             # 1.10
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from statistics import mean

from . import agent_profile, discovery, generation, llm, measurement, optimize, publishing, registry, scoring
from .config import DATA_DIR, load_strategy
from .models import QualityScores
from .store import Store

GATE_DIMS = ["relevance", "helpfulness", "specificity", "naturalness", "conversation_fit", "agent_fit", "platform_fit"]


def _style_bias(store: Store) -> dict[str, float]:
    """Relative style performance from all previous campaigns (Campaign Memory)."""
    per: dict[str, list[float]] = defaultdict(list)
    for p in store.q("SELECT p.*, d.style FROM publications p JOIN drafts d ON d.id=p.draft_id"):
        per[p["style"]].append(optimize.engagement(optimize._outcome(store, p)))
    per = {k: v for k, v in per.items() if len(v) >= optimize.MIN_SAMPLE}
    if not per:
        return {}
    overall = mean(x for v in per.values() for x in v) or 1.0
    return {k: mean(v) / overall - 1 for k, v in per.items()}


def cmd_harness_verify(a, store):
    health = registry.verify(network=a.network)
    print(registry.render(health))
    blocking = [h for h in health if not h.ok and h.status != "manual"]
    print(f"\n{len(health) - len(blocking)}/{len(health)} capabilities ready (manual ones count as ready-for-human).")
    print(f"Claude judge/generator: {'configured' if llm.available() else 'NOT configured (heuristics + human scoring)'}")


def cmd_campaign_start(a, store):
    overrides = agent_profile.load_overrides(a.profile)
    profile = agent_profile.build_profile(a.agent_url, overrides)
    strategy = load_strategy()
    # carry forward confirmed discovery knowledge: drop queries that were DROP-classified before
    dropped = {json.loads(r["recommendation_json"]).get("query") for r in store.q(
        "SELECT recommendation_json FROM findings f JOIN campaigns c ON c.id=f.campaign_id"
        " WHERE c.agent_url=? AND f.area='discovery' AND f.classification='DROP'", (a.agent_url,))}
    profile.reddit_queries = [q for q in profile.reddit_queries if q not in dropped]
    cid = store.create_campaign(profile, strategy)
    print(f"campaign {cid} created for {profile.name} <{profile.url}>")
    print(profile.model_dump_json(indent=2))
    if not (profile.reddit_queries or profile.x_queries):
        print("\nWARNING: no queries could be derived. Supply --profile with reddit_queries/subreddits.", file=sys.stderr)


def cmd_discover(a, store):
    platforms = set(a.platforms.split(","))
    print(json.dumps(discovery.discover(store, a.cid, platforms, a.max), indent=2))


def cmd_import(a, store):
    print(f"imported {discovery.import_candidates(store, a.cid, a.file)} candidates")


def cmd_score(a, store):
    print(json.dumps(scoring.score_campaign(store, a.cid), indent=2))
    for r in store.candidates(a.cid, "qualified"):
        print(f"  [{r['opp_total']:5.1f}] {r['platform']:6} {r['community']:22} {r['url']}")


def cmd_draft(a, store):
    print(json.dumps(generation.draft_campaign(store, a.cid, _style_bias(store)), indent=2))


def cmd_add_draft(a, store):
    scores = None
    if a.scores:
        vals = [int(x) for x in a.scores.split(",")]
        if len(vals) != 8:
            raise SystemExit("--scores needs 8 ints: " + ",".join(GATE_DIMS) + ",promotional_intensity")
        scores = dict(zip(GATE_DIMS + ["promotional_intensity"], vals))
    text = open(a.text_file, encoding="utf-8").read().strip() if a.text_file else a.text
    did, verdict, reasons = generation.add_manual_draft(store, a.cid, a.candidate_id, a.style, text, scores)
    print(f"draft {did}: {verdict}" + (f" — {'; '.join(reasons)}" if reasons else ""))


def cmd_review(a, store):
    rows = store.drafts(a.cid, "pending") + store.drafts(a.cid, "needs_rewrite")
    if not rows:
        print("nothing to review")
        return
    strategy = store.strategy(a.cid)
    for r in rows:
        print(publishing.review_summary(r))
        if r["status"] == "needs_rewrite":
            print("This draft has no judge scores. Enter 8 scores (0-5): " + ",".join(GATE_DIMS) + ",promotional_intensity")
            raw = input("scores (blank = skip) > ").strip()
            if not raw:
                continue
            vals = dict(zip(GATE_DIMS + ["promotional_intensity"], (int(x) for x in raw.split(","))))
            from . import quality_gate
            from .models import Candidate

            cand = Candidate.model_validate_json(r["data_json"])
            res = quality_gate.evaluate(r["text"], store.profile(a.cid), cand, store.published_texts(),
                                        strategy["quality_gate"], QualityScores(**vals))
            store.set_draft(r["id"], verdict=res.verdict, gate_json=res.model_dump_json())
            if res.verdict != "PASS":
                store.set_draft(r["id"], status="rejected", reviewer_note="; ".join(res.reasons))
                print(f"  → {res.verdict}: {'; '.join(res.reasons)}")
                continue
        ans = input("[a]pprove / [r]eject / [s]kip > ").strip().lower()
        if ans == "a":
            store.set_draft(r["id"], status="approved")
        elif ans == "r":
            store.set_draft(r["id"], status="rejected", reviewer_note=input("reason > "))


def cmd_publish(a, store):
    items = publishing.publish(store, a.cid, a.mode, a.dry_run)
    if not items:
        print("no approved drafts in queue (run `finch review` first)")
    for it in items:
        print(f"\n--- draft {it['draft_id']} [{it['platform']}] {it['action']}\nthread: {it['thread']}")
        if "intent_url" in it:
            print(f"intent: {it['intent_url']}")
        print(it["text"])


def cmd_record_post(a, store):
    print(f"publication {publishing.record_post(store, a.draft_id, a.comment_url)} recorded")


def cmd_measure(a, store):
    print(json.dumps(measurement.measure(store, a.cid), indent=2, default=str))


def cmd_import_conversions(a, store):
    print(f"imported {measurement.import_conversions(store, a.cid, a.file)} rows")


def cmd_analyze(a, store):
    findings, summary = optimize.analyze(store, a.cid)
    report = optimize.render_report(findings, summary)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"campaign-{a.cid}-report.md"
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nreport written to {out}")


def cmd_status(a, store):
    c = store.campaign(a.cid)
    print(f"campaign {a.cid}: {c['agent_name']} <{c['agent_url']}> created {c['created_at']}")
    for tbl, col in (("candidates", "status"), ("drafts", "status")):
        rows = store.q(f"SELECT {col}, COUNT(*) n FROM {tbl} WHERE campaign_id=? GROUP BY {col}", (a.cid,))
        print(f"  {tbl}: " + ", ".join(f"{r[col]}={r['n']}" for r in rows))
    print(f"  publications: {len(store.publications(a.cid))}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="finch", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", help="SQLite path (default data/finch.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("harness").add_subparsers(dest="sub", required=True)
    v = h.add_parser("verify")
    v.add_argument("--network", action="store_true", help="also probe Reddit/X/Anthropic reachability")
    v.set_defaults(fn=cmd_harness_verify)

    c = sub.add_parser("campaign").add_subparsers(dest="sub", required=True)
    s = c.add_parser("start")
    s.add_argument("agent_url")
    s.add_argument("--profile", help="YAML/JSON with profile fields to add/override (subreddits, queries, …)")
    s.set_defaults(fn=cmd_campaign_start)

    def with_cid(name, fn, **extra):
        sp = sub.add_parser(name)
        sp.add_argument("cid", type=int)
        for flag, kw in extra.items():
            sp.add_argument(flag, **kw)
        sp.set_defaults(fn=fn)
        return sp

    with_cid("discover", cmd_discover, **{"--platforms": dict(default="reddit,x"), "--max": dict(type=int)})
    with_cid("import", cmd_import, file={})
    with_cid("score", cmd_score)
    with_cid("draft", cmd_draft)
    ad = with_cid("add-draft", cmd_add_draft, candidate_id=dict(type=int), style={})
    g = ad.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--text-file")
    ad.add_argument("--scores", help="8 comma-separated ints: " + ",".join(GATE_DIMS) + ",promotional_intensity")
    with_cid("review", cmd_review)
    with_cid("publish", cmd_publish, **{"--mode": dict(choices=["manual", "api"], default="manual"),
                                        "--dry-run": dict(action="store_true")})
    rp = sub.add_parser("record-post")
    rp.add_argument("draft_id", type=int)
    rp.add_argument("comment_url")
    rp.set_defaults(fn=cmd_record_post)
    with_cid("measure", cmd_measure)
    with_cid("import-conversions", cmd_import_conversions, file={})
    with_cid("analyze", cmd_analyze)
    with_cid("status", cmd_status)

    a = p.parse_args(argv)
    store = Store(a.db) if a.db else Store()
    try:
        a.fn(a, store)
    finally:
        store.close()


if __name__ == "__main__":
    main()
