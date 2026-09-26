"""Campaign memory: SQLite store for campaigns, candidates, drafts, publications, metrics."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .config import DATA_DIR
from .models import AgentProfile, Candidate, utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY,
    agent_url TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    strategy_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    platform TEXT NOT NULL,
    community TEXT NOT NULL DEFAULT '',
    query TEXT NOT NULL,
    n_results INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    url TEXT NOT NULL,
    community TEXT NOT NULL DEFAULT '',
    query TEXT NOT NULL DEFAULT '',
    data_json TEXT NOT NULL,
    opp_json TEXT,
    opp_total REAL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    UNIQUE (campaign_id, platform, external_id)
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    style TEXT NOT NULL,
    text TEXT NOT NULL,
    verdict TEXT,
    gate_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    reviewer_note TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    draft_id INTEGER NOT NULL REFERENCES drafts(id),
    platform TEXT NOT NULL,
    thread_url TEXT NOT NULL,
    thread_external_id TEXT NOT NULL,
    comment_url TEXT,
    comment_external_id TEXT,
    mode TEXT NOT NULL,
    published_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY,
    publication_id INTEGER NOT NULL REFERENCES publications(id),
    observed_at TEXT NOT NULL,
    score INTEGER,
    replies INTEGER,
    author_replied INTEGER,
    raw_json TEXT
);
CREATE TABLE IF NOT EXISTS conversions (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    publication_id INTEGER REFERENCES publications(id),
    day TEXT,
    clicks INTEGER NOT NULL DEFAULT 0,
    trials INTEGER NOT NULL DEFAULT 0,
    usage_events INTEGER NOT NULL DEFAULT 0,
    source TEXT
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    area TEXT NOT NULL,
    classification TEXT NOT NULL,
    finding TEXT NOT NULL,
    recommendation_json TEXT,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return utcnow().isoformat()


class Store:
    def __init__(self, path: Path | str | None = None):
        if path is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            path = DATA_DIR / "finch.db"
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    def q(self, sql: str, args: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return list(self.db.execute(sql, tuple(args)))

    def x(self, sql: str, args: Iterable[Any] = ()) -> int:
        cur = self.db.execute(sql, tuple(args))
        self.db.commit()
        return cur.lastrowid

    # ---- campaigns
    def create_campaign(self, profile: AgentProfile, strategy: dict[str, Any]) -> int:
        return self.x(
            "INSERT INTO campaigns (agent_url, agent_name, profile_json, strategy_json, created_at) VALUES (?,?,?,?,?)",
            (profile.url, profile.name, profile.model_dump_json(), json.dumps(strategy), _now()),
        )

    def campaign(self, cid: int) -> sqlite3.Row:
        rows = self.q("SELECT * FROM campaigns WHERE id=?", (cid,))
        if not rows:
            raise KeyError(f"campaign {cid} not found")
        return rows[0]

    def profile(self, cid: int) -> AgentProfile:
        return AgentProfile.model_validate_json(self.campaign(cid)["profile_json"])

    def strategy(self, cid: int) -> dict[str, Any]:
        return json.loads(self.campaign(cid)["strategy_json"])

    # ---- queries
    def log_query(self, cid: int, platform: str, query: str, community: str, n: int, error: str | None = None) -> None:
        self.x(
            "INSERT INTO queries (campaign_id, platform, community, query, n_results, error, created_at) VALUES (?,?,?,?,?,?,?)",
            (cid, platform, community, query, n, error, _now()),
        )

    # ---- candidates
    def add_candidate(self, cid: int, c: Candidate) -> int | None:
        try:
            return self.x(
                "INSERT INTO candidates (campaign_id, platform, external_id, url, community, query, data_json, created_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (cid, c.platform, c.external_id, c.url, c.community, c.query, c.model_dump_json(), _now()),
            )
        except sqlite3.IntegrityError:
            return None

    def candidates(self, cid: int, status: str | None = None) -> list[sqlite3.Row]:
        if status:
            return self.q("SELECT * FROM candidates WHERE campaign_id=? AND status=? ORDER BY opp_total DESC", (cid, status))
        return self.q("SELECT * FROM candidates WHERE campaign_id=? ORDER BY opp_total DESC", (cid,))

    def set_candidate(self, cand_id: int, **fields: Any) -> None:
        cols = ", ".join(f"{k}=?" for k in fields)
        self.x(f"UPDATE candidates SET {cols} WHERE id=?", (*fields.values(), cand_id))

    def already_engaged(self, platform: str, external_id: str) -> bool:
        """True if any campaign already published into this thread."""
        return bool(
            self.q(
                "SELECT 1 FROM publications WHERE platform=? AND thread_external_id=? LIMIT 1",
                (platform, external_id),
            )
        )

    # ---- drafts
    def add_draft(self, cid: int, cand_id: int, style: str, text: str) -> int:
        return self.x(
            "INSERT INTO drafts (campaign_id, candidate_id, style, text, created_at) VALUES (?,?,?,?,?)",
            (cid, cand_id, style, text, _now()),
        )

    def drafts(self, cid: int, status: str | None = None) -> list[sqlite3.Row]:
        sql = (
            "SELECT d.*, c.platform, c.url AS thread_url, c.external_id AS thread_external_id, c.community,"
            " c.opp_total, c.data_json FROM drafts d JOIN candidates c ON c.id=d.candidate_id WHERE d.campaign_id=?"
        )
        args: list[Any] = [cid]
        if status:
            sql += " AND d.status=?"
            args.append(status)
        return self.q(sql + " ORDER BY c.opp_total DESC", args)

    def set_draft(self, draft_id: int, **fields: Any) -> None:
        cols = ", ".join(f"{k}=?" for k in fields)
        self.x(f"UPDATE drafts SET {cols} WHERE id=?", (*fields.values(), draft_id))

    def published_texts(self) -> list[str]:
        return [
            r["text"]
            for r in self.q("SELECT d.text FROM publications p JOIN drafts d ON d.id=p.draft_id")
        ]

    # ---- publications / metrics / conversions
    def add_publication(self, cid: int, draft_id: int, platform: str, thread_url: str, thread_ext: str,
                        comment_url: str | None, comment_ext: str | None, mode: str) -> int:
        return self.x(
            "INSERT INTO publications (campaign_id, draft_id, platform, thread_url, thread_external_id, comment_url,"
            " comment_external_id, mode, published_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (cid, draft_id, platform, thread_url, thread_ext, comment_url, comment_ext, mode, _now()),
        )

    def publications(self, cid: int) -> list[sqlite3.Row]:
        return self.q(
            "SELECT p.*, d.style, d.text, c.community, c.query, c.opp_total, c.data_json FROM publications p"
            " JOIN drafts d ON d.id=p.draft_id JOIN candidates c ON c.id=d.candidate_id WHERE p.campaign_id=?",
            (cid,),
        )

    def add_metric(self, pub_id: int, score: int | None, replies: int | None, author_replied: bool | None,
                   raw: dict[str, Any] | None = None) -> None:
        self.x(
            "INSERT INTO metrics (publication_id, observed_at, score, replies, author_replied, raw_json) VALUES (?,?,?,?,?,?)",
            (pub_id, _now(), score, replies, None if author_replied is None else int(author_replied), json.dumps(raw or {})),
        )

    def latest_metric(self, pub_id: int) -> sqlite3.Row | None:
        rows = self.q("SELECT * FROM metrics WHERE publication_id=? ORDER BY id DESC LIMIT 1", (pub_id,))
        return rows[0] if rows else None

    def add_conversion(self, cid: int, pub_id: int | None, day: str | None, clicks: int, trials: int, usage: int,
                       source: str) -> None:
        self.x(
            "INSERT INTO conversions (campaign_id, publication_id, day, clicks, trials, usage_events, source) VALUES (?,?,?,?,?,?,?)",
            (cid, pub_id, day, clicks, trials, usage, source),
        )

    def add_finding(self, cid: int, area: str, classification: str, finding: str, rec: dict[str, Any] | None) -> None:
        self.x(
            "INSERT INTO findings (campaign_id, area, classification, finding, recommendation_json, created_at) VALUES (?,?,?,?,?,?)",
            (cid, area, classification, finding, json.dumps(rec or {}), _now()),
        )
