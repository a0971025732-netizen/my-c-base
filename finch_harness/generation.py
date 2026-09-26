"""Phase 1.6 COMMENT GENERATION + 1.7 gate loop (generate → judge → rewrite ≤ N → PASS/REJECT)."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from . import llm, quality_gate
from .models import AgentProfile, Candidate, CommentDraft, OpportunityScore
from .store import Store

GEN_SYSTEM = """You write replies for Finch's transparent outbound program. The account is openly affiliated with Finch.

Rules:
- The reply must be genuinely useful on its own: answer the actual question or add a concrete perspective first.
- Mention the agent once, as one relevant option, with the exact URL given (do not alter, shorten, or add parameters).
- Include a short, natural affiliation disclosure (e.g. one of the disclosure templates provided).
- Never pretend to be an independent user, never invent personal experiences, results, or numbers.
- Match the thread's language, tone and platform norms. No hashtags, no emojis unless the thread uses them, no marketing adjectives.
- Reddit: 2-6 short paragraphs or a short list, plain markdown. X: one reply under 280 characters (links count as 23).
- Use the requested style and do not reuse phrasing from previous replies shown to you."""


class _Draft(BaseModel):
    style: str
    text: str = Field(description="The reply text only")


def choose_style(strategy: dict[str, Any], used: Counter, opp: OpportunityScore, style_bias: dict[str, float] | None = None) -> str:
    styles = strategy["comment_styles"]
    preferred = {
        "question": ["direct_answer", "clarifying_plus_tip"],
        "tool_recommendation": ["resource_list", "comparison", "direct_answer"],
        "comparison": ["comparison"],
        "workflow_discussion": ["workflow_walkthrough"],
        "technical_discussion": ["workflow_walkthrough", "direct_answer"],
        "experience_sharing": ["experience_share"],
        "project_building": ["workflow_walkthrough", "resource_list"],
        "educational": ["resource_list", "direct_answer"],
    }.get(opp.intent_type, styles)
    bias = style_bias or {}
    return min(
        (s for s in styles if s in preferred) or styles,
        key=lambda s: (used[s] - bias.get(s, 0.0), styles.index(s)),
    )


def generate(profile: AgentProfile, cand: Candidate, style: str, strategy: dict[str, Any], recent: list[str],
             feedback: str = "") -> CommentDraft | None:
    prompt = (
        f"Platform: {cand.platform} / community: {cand.community}\nThread URL: {cand.url}\n"
        f"Title: {cand.title}\nBody: {cand.body[:3000]}\nTop comments: {json.dumps(cand.top_comments[:5])[:2500]}\n\n"
        f"Agent profile: {profile.model_dump_json(include={'name','category','capabilities','use_cases','free_usage'})}\n"
        f"Exact Agent URL: {profile.url}\nDisclosure templates: {strategy['disclosure_templates']}\n"
        f"Style: {style}\nPrevious replies (do not reuse phrasing): {json.dumps(recent[-5:])[:3000]}\n"
    )
    if feedback:
        prompt += f"\nA reviewer rejected the previous version. Fix these issues: {feedback}\n"
    out = llm.structured(GEN_SYSTEM, prompt, _Draft, model=strategy.get("llm", {}).get("model"),
                         effort=strategy.get("llm", {}).get("effort", "medium"))
    return CommentDraft(style=style, text=out.text.strip()) if out else None


def draft_campaign(store: Store, cid: int, style_bias: dict[str, float] | None = None) -> dict[str, int]:
    if not llm.available():
        raise RuntimeError(
            "Claude is not configured (ANTHROPIC_API_KEY). Write drafts manually with `finch add-draft`, "
            "or let the orchestrating Claude session write them."
        )
    profile, strategy = store.profile(cid), store.strategy(cid)
    gate_cfg = strategy["quality_gate"]
    history = store.published_texts()
    used: Counter = Counter()
    stats = Counter()
    for row in store.candidates(cid, "qualified"):
        cand = Candidate.model_validate_json(row["data_json"])
        opp = OpportunityScore.model_validate_json(row["opp_json"])
        style = choose_style(strategy, used, opp, style_bias)
        feedback, result, draft = "", None, None
        for _attempt in range(gate_cfg["max_rewrites"] + 1):
            draft = generate(profile, cand, style, strategy, history, feedback)
            if draft is None:
                break
            result = quality_gate.evaluate(draft.text, profile, cand, history, gate_cfg)
            if result.verdict != "REWRITE":
                break
            feedback = "; ".join(result.reasons) + (f" | {result.scores.feedback}" if result.scores else "")
        if draft is None or result is None:
            continue
        verdict = "REJECT" if result.verdict == "REWRITE" else result.verdict
        did = store.add_draft(cid, row["id"], draft.style, draft.text)
        store.set_draft(did, verdict=verdict, gate_json=result.model_dump_json(),
                        status="pending" if verdict == "PASS" else "rejected")
        store.set_candidate(row["id"], status="drafted")
        if verdict == "PASS":
            used[style] += 1
            history.append(draft.text)
        stats[verdict] += 1
    return dict(stats)


def add_manual_draft(store: Store, cid: int, cand_id: int, style: str, text: str,
                     scores: dict[str, int] | None = None) -> tuple[int, str, list[str]]:
    """Register a human- or orchestrator-written draft and run it through the same gate."""
    from .models import QualityScores

    profile, strategy = store.profile(cid), store.strategy(cid)
    row = store.q("SELECT * FROM candidates WHERE id=? AND campaign_id=?", (cand_id, cid))[0]
    cand = Candidate.model_validate_json(row["data_json"])
    qs = QualityScores(**scores) if scores else None
    result = quality_gate.evaluate(text, profile, cand, store.published_texts(), strategy["quality_gate"], qs)
    did = store.add_draft(cid, cand_id, style, text)
    store.set_draft(did, verdict=result.verdict, gate_json=result.model_dump_json(),
                    status="pending" if result.verdict == "PASS" else "rejected" if result.verdict == "REJECT" else "needs_rewrite")
    store.set_candidate(cand_id, status="drafted")
    return did, result.verdict, result.reasons
