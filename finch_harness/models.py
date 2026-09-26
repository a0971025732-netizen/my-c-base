from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["reddit", "x", "web"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentProfile(BaseModel):
    name: str
    url: str  # canonical promotion URL — used verbatim in every comment
    category: str = ""
    capabilities: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    free_usage: str = ""
    keywords: list[str] = Field(default_factory=list)
    semantic_topics: list[str] = Field(default_factory=list)
    adjacent_topics: list[str] = Field(default_factory=list)
    subreddits: list[str] = Field(default_factory=list)
    reddit_queries: list[str] = Field(default_factory=list)
    x_queries: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    platform: Platform
    external_id: str
    url: str
    community: str = ""  # subreddit, or "x", or domain
    title: str = ""
    body: str = ""
    author: str = ""
    created_at: datetime | None = None
    num_comments: int = 0
    score: int = 0
    query: str = ""
    top_comments: list[str] = Field(default_factory=list)
    locked: bool = False

    def age_hours(self, now: datetime | None = None) -> float | None:
        if not self.created_at:
            return None
        now = now or utcnow()
        created = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=timezone.utc)
        return max((now - created).total_seconds() / 3600, 0.0)


class JudgedFit(BaseModel):
    """LLM (or heuristic) judgment of a candidate; each 0.0–1.0."""

    relevance: float
    intent: float
    audience_fit: float
    agent_fit: float
    naturalness: float
    intent_type: str = ""
    rationale: str = ""


class OpportunityScore(BaseModel):
    relevance: float
    intent: float
    freshness: float
    momentum: float
    audience_fit: float
    agent_fit: float
    naturalness: float
    total: float
    intent_type: str = ""
    rationale: str = ""


class CommentDraft(BaseModel):
    style: str
    text: str


class QualityScores(BaseModel):
    relevance: int
    helpfulness: int
    specificity: int
    naturalness: int
    conversation_fit: int
    agent_fit: int
    platform_fit: int
    promotional_intensity: int
    feedback: str = ""

    @property
    def total(self) -> int:
        return (
            self.relevance
            + self.helpfulness
            + self.specificity
            + self.naturalness
            + self.conversation_fit
            + self.agent_fit
            + self.platform_fit
        )


class GateResult(BaseModel):
    verdict: Literal["PASS", "REWRITE", "REJECT"]
    scores: QualityScores | None = None
    reasons: list[str] = Field(default_factory=list)
