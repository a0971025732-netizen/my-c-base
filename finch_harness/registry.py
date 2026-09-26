"""Tool Registry loader and health check (Phase 1.1 LOAD HARNESS)."""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass, field
from typing import Any

from .config import load_registry

PROBES = {
    "reddit": "https://www.reddit.com/r/test/new.json?limit=1",
    "x": "https://api.x.com/2/openapi.json",
    "anthropic": "https://api.anthropic.com/v1/models",
}


@dataclass
class ToolHealth:
    capability: str
    tool: str
    status: str
    ok: bool
    problems: list[str] = field(default_factory=list)


def _probe(url: str) -> str | None:
    import httpx

    try:
        httpx.get(url, timeout=8, headers={"User-Agent": "finch-harness/0.1 (registry health check)"})
        return None
    except httpx.HTTPError as e:
        return f"network: {type(e).__name__}"


def verify(network: bool = False) -> list[ToolHealth]:
    reg = load_registry()
    probes: dict[str, str | None] = {}
    if network:
        probes = {k: _probe(u) for k, u in PROBES.items()}

    out: list[ToolHealth] = []
    for cap in reg["capabilities"]:
        h = ToolHealth(cap["capability"], cap["tool"], cap["status"], ok=True)
        module = cap.get("module")
        if module and importlib.util.find_spec(module) is None:
            h.problems.append(f"python module '{module}' not installed")
        missing = [v for v in cap.get("requires_env", []) if not os.environ.get(v)]
        if missing:
            h.problems.append("missing env: " + ", ".join(missing))
        if network:
            key = "reddit" if module == "praw" else "x" if module == "tweepy" else "anthropic" if module == "anthropic" else None
            if key and probes.get(key):
                h.problems.append(f"{key} unreachable ({probes[key]})")
        if cap["status"] == "manual":
            h.problems.append("MANUAL REVIEW REQUIRED")
        h.ok = cap["status"] != "manual" and not h.problems
        out.append(h)
    return out


def capability_ok(name: str, health: list[ToolHealth]) -> bool:
    return any(h.capability == name and h.ok for h in health)


def render(health: list[ToolHealth], registry: dict[str, Any] | None = None) -> str:
    reg = registry or load_registry()
    by_cap = {c["capability"]: c for c in reg["capabilities"]}
    lines = [
        "| Capability | Tool | Source | Stars | Status | Confidence | Ready |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for h in health:
        c = by_cap[h.capability]
        stars = c.get("stars")
        ready = "yes" if h.ok else "no — " + "; ".join(h.problems)
        lines.append(
            f"| {h.capability} | {h.tool} | {c.get('source', '-')} | {stars if stars else '-'} | {c['status']} | {c.get('confidence', '-')} | {ready} |"
        )
    return "\n".join(lines)
