"""Phase 1.7 QUALITY GATE: hard rules + 7-dimension judge (0-5 each, min 28/35)."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from . import llm
from .models import AgentProfile, Candidate, GateResult, QualityScores

X_URL_LEN = 23  # t.co wraps every link to 23 chars
X_LIMIT = 280
REDDIT_MIN_CHARS = 120
REDDIT_MAX_CHARS = 3000

DISCLOSURE_PAT = re.compile(r"\b(disclosure|i work (on|at|for)|i('m| am) with|i help build|i build|i made|we built|biased|affiliated)\b", re.I)


def x_length(text: str) -> int:
    return len(re.sub(r"https?://\S+", "x" * X_URL_LEN, text))


def similarity(a: str, b: str) -> float:
    norm = lambda s: re.sub(r"https?://\S+|\W+", " ", s.lower()).strip()  # noqa: E731
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def hard_checks(text: str, profile: AgentProfile, cand: Candidate, history: list[str], cfg: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if profile.url not in text:
        problems.append("missing the exact Agent URL")
    if cfg.get("require_disclosure", True) and not DISCLOSURE_PAT.search(text):
        problems.append("missing affiliation disclosure")
    if cand.platform == "x" and x_length(text) > X_LIMIT:
        problems.append(f"too long for X ({x_length(text)}>{X_LIMIT})")
    if cand.platform == "reddit" and not (REDDIT_MIN_CHARS <= len(text) <= REDDIT_MAX_CHARS):
        problems.append(f"reddit length {len(text)} outside {REDDIT_MIN_CHARS}-{REDDIT_MAX_CHARS}")
    if cand.locked:
        problems.append("thread locked/archived or replies restricted")
    worst = max((similarity(text, h) for h in history), default=0.0)
    if worst > cfg["max_similarity_to_history"]:
        problems.append(f"too similar to a previously published comment ({worst:.2f})")
    if text.count(profile.url) > 1:
        problems.append("agent URL repeated")
    return problems


JUDGE_SYSTEM = (
    "You are a strict community-quality reviewer for a transparent outbound program. Score the reply 0-5 on each:\n"
    "relevance (to the thread), helpfulness (useful even if the link were removed), specificity (concrete, not generic), "
    "naturalness (reads like a knowledgeable human, not an ad), conversation_fit (right tone, answers what was asked, "
    "doesn't repeat existing comments), agent_fit (the agent mention truly helps this person), platform_fit (length, "
    "format, norms of the platform/community).\n"
    "Also score promotional_intensity 0-5 (0 = pure help, 5 = pure ad). Give actionable feedback for a rewrite."
)


def judge(text: str, profile: AgentProfile, cand: Candidate) -> QualityScores | None:
    return llm.structured(
        JUDGE_SYSTEM,
        f"Platform: {cand.platform} / {cand.community}\nThread title: {cand.title}\nThread body: {cand.body[:2500]}\n"
        f"Existing top comments: {cand.top_comments[:5]}\n\nAgent: {profile.name} — {profile.category}; "
        f"capabilities: {profile.capabilities}\n\nProposed reply:\n{text}",
        QualityScores,
        effort="low",
    )


def evaluate(text: str, profile: AgentProfile, cand: Candidate, history: list[str], cfg: dict[str, Any],
             scores: QualityScores | None = None) -> GateResult:
    problems = hard_checks(text, profile, cand, history, cfg)
    if scores is None:
        scores = judge(text, profile, cand)
    reasons = list(problems)
    if scores is None:
        reasons.append("no judge available: a human reviewer must score this draft (finch review)")
        return GateResult(verdict="REWRITE", scores=None, reasons=reasons)

    if scores.total < cfg["min_total"]:
        reasons.append(f"total {scores.total}/35 < {cfg['min_total']}")
    if scores.promotional_intensity > cfg["max_promotional_intensity"]:
        reasons.append(f"promotional intensity {scores.promotional_intensity} > {cfg['max_promotional_intensity']}")
    if scores.agent_fit < cfg["min_agent_fit"]:
        reasons.append(f"agent fit {scores.agent_fit} < {cfg['min_agent_fit']}")
    if scores.conversation_fit < cfg["min_conversation_fit"]:
        reasons.append(f"conversation fit {scores.conversation_fit} < {cfg['min_conversation_fit']}")

    if not reasons:
        return GateResult(verdict="PASS", scores=scores)
    # a thread where the agent simply doesn't fit can't be fixed by rewriting
    unfixable = scores.agent_fit <= 2 or any("locked" in r for r in problems)
    return GateResult(verdict="REJECT" if unfixable else "REWRITE", scores=scores, reasons=reasons)
