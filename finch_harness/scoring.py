"""Phase 1.5 OPPORTUNITY SCORING (0-100)."""

from __future__ import annotations

import json
import math
import re
from typing import Any

from pydantic import BaseModel, Field

from . import llm
from .models import AgentProfile, Candidate, JudgedFit, OpportunityScore
from .store import Store


def freshness_fraction(age_hours: float | None, curve: list[list[float]]) -> float:
    """Linear interpolation over [(hours, fraction), ...]; unknown age scores 0.5."""
    if age_hours is None:
        return 0.5
    prev_h, prev_f = 0.0, 1.0
    for h, f in curve:
        if age_hours <= h:
            span = h - prev_h
            return prev_f + (f - prev_f) * ((age_hours - prev_h) / span if span else 1)
        prev_h, prev_f = h, f
    return curve[-1][1]


def momentum_fraction(c: Candidate) -> float:
    """Activity per hour, log-scaled. A thread with ~10 interactions/hour saturates."""
    age = max(c.age_hours() or 24.0, 1.0)
    activity = c.num_comments + max(c.score, 0) / 3
    velocity = activity / age
    base = math.log1p(activity) / math.log1p(60)
    vel = math.log1p(velocity) / math.log1p(10)
    # dead threads (0 comments, low score) still have some value for a first helpful answer
    return max(0.0, min(1.0, 0.5 * base + 0.5 * vel))


_WORD = re.compile(r"[a-z0-9+#-]{3,}")


def heuristic_judge(profile: AgentProfile, c: Candidate) -> JudgedFit:
    text = f"{c.title} {c.body}".lower()
    words = set(_WORD.findall(text))
    topic_terms = {w for t in profile.keywords + profile.semantic_topics + profile.adjacent_topics for w in _WORD.findall(t.lower())}
    overlap = len(words & topic_terms) / max(len(topic_terms), 1)
    relevance = min(1.0, overlap * 4)
    question = "?" in text or bool(re.search(r"\b(how do|how to|any (tool|recommend)|best way|looking for|recommend|alternative)", text))
    intent = 0.8 if question else 0.4
    audience = 0.8 if c.community.lower() in {s.lower() for s in profile.subreddits} else 0.5
    return JudgedFit(
        relevance=relevance,
        intent=intent,
        audience_fit=audience,
        agent_fit=relevance * 0.9,
        naturalness=0.6 if question else 0.3,
        intent_type="question" if question else "discussion",
        rationale="heuristic (no LLM configured)",
    )


class _Judgements(BaseModel):
    items: list[JudgedFit] = Field(description="One judgement per candidate, same order as input")


JUDGE_SYSTEM = (
    "You evaluate social conversations for a transparent, disclosed outbound program. For each conversation, rate 0.0-1.0:\n"
    "relevance: how closely the topic matches what the agent does (semantic, not keyword).\n"
    "intent: how much the author/participants want help, tools, or perspectives right now.\n"
    "audience_fit: whether participants are the agent's target users.\n"
    "agent_fit: whether recommending this specific agent would genuinely help this person.\n"
    "naturalness: whether a disclosed mention would be welcome rather than spammy in this thread and community "
    "(0 if the community or post forbids self-promotion, or the thread is emotional/personal).\n"
    "intent_type: one of question, tool_recommendation, workflow_discussion, technical_discussion, industry_discussion, "
    "comparison, experience_sharing, project_building, educational, emerging.\n"
    "Be strict: most conversations should NOT score high on agent_fit."
)


def judge(profile: AgentProfile, cands: list[Candidate], batch: int = 10) -> list[JudgedFit]:
    if not llm.available():
        return [heuristic_judge(profile, c) for c in cands]
    out: list[JudgedFit] = []
    prof = profile.model_dump_json(include={"name", "category", "capabilities", "use_cases", "target_users", "semantic_topics"})
    for i in range(0, len(cands), batch):
        chunk = cands[i : i + batch]
        convo = "\n\n".join(
            f"### {j}\ncommunity: {c.community}\ntitle: {c.title}\nbody: {c.body[:1500]}\n"
            f"top comments: {json.dumps(c.top_comments[:3])[:1500]}"
            for j, c in enumerate(chunk)
        )
        res = llm.structured(JUDGE_SYSTEM, f"Agent profile:\n{prof}\n\nConversations:\n{convo}", _Judgements, effort="low")
        items = res.items if res and len(res.items) == len(chunk) else [heuristic_judge(profile, c) for c in chunk]
        out.extend(items)
    return out


def combine(j: JudgedFit, c: Candidate, profile: AgentProfile, strategy: dict[str, Any]) -> OpportunityScore:
    w = strategy["scoring_weights"]
    fresh = freshness_fraction(c.age_hours(), strategy["freshness_curve_hours"])
    audience = j.audience_fit
    if c.community.lower() in {s.lower() for s in profile.subreddits}:
        audience = min(1.0, audience + 0.1)
    parts = {
        "relevance": w["relevance"] * j.relevance,
        "intent": w["intent"] * j.intent,
        "freshness": w["freshness"] * fresh,
        "momentum": w["momentum"] * momentum_fraction(c),
        "audience_fit": w["audience_fit"] * audience,
        "agent_fit": w["agent_fit"] * j.agent_fit,
        "naturalness": w["naturalness"] * j.naturalness,
    }
    parts = {k: round(v, 2) for k, v in parts.items()}
    return OpportunityScore(**parts, total=round(sum(parts.values()), 1), intent_type=j.intent_type, rationale=j.rationale)


def score_campaign(store: Store, cid: int) -> dict[str, int]:
    profile = store.profile(cid)
    strategy = store.strategy(cid)
    rows = store.candidates(cid, "new")
    cands = [Candidate.model_validate_json(r["data_json"]) for r in rows]
    judged = judge(profile, cands)
    threshold = strategy["campaign"]["qualify_min_score"]
    qualified_cap = strategy["campaign"]["qualified_target"][1]
    scored = []
    for r, c, j in zip(rows, cands, judged):
        s = combine(j, c, profile, strategy)
        scored.append((r["id"], s))
    scored.sort(key=lambda t: t[1].total, reverse=True)
    n_q = 0
    for cand_id, s in scored:
        # agent_fit is a hard floor: a high total without real fit is not an opportunity
        ok = s.total >= threshold and s.agent_fit >= 0.5 * strategy["scoring_weights"]["agent_fit"] and n_q < qualified_cap
        store.set_candidate(cand_id, opp_json=s.model_dump_json(), opp_total=s.total, status="qualified" if ok else "rejected")
        n_q += ok
    return {"scored": len(scored), "qualified": n_q}
