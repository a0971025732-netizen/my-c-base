"""Thin Claude wrapper used by the strategy layer (profile building, judging, drafting).

Returns None when Claude is not configured so callers can fall back to heuristics.
"""

from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "claude-opus-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def available() -> bool:
    if os.environ.get("FINCH_DISABLE_LLM"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.environ.get("ANTHROPIC_PROFILE")
    )


class LLMRefusal(RuntimeError):
    pass


def structured(system: str, prompt: str, schema: type[T], *, model: str | None = None,
               effort: str = "medium", max_tokens: int = 16000) -> T | None:
    """One structured-output call. None if Claude is not configured."""
    if not available():
        return None
    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=model or DEFAULT_MODEL,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
    )
    if response.stop_reason == "refusal":
        raise LLMRefusal(str(response.stop_details))
    return response.parsed_output
