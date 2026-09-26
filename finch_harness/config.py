from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
HARNESS_DIR = Path(os.environ.get("FINCH_HARNESS_DIR", ROOT / "harness"))
DATA_DIR = Path(os.environ.get("FINCH_DATA_DIR", ROOT / "data"))


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_registry() -> dict[str, Any]:
    return load_yaml(HARNESS_DIR / "tool_registry.yaml")


def load_strategy(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    strategy = load_yaml(HARNESS_DIR / "strategy.yaml")
    if overrides:
        strategy = deep_merge(strategy, overrides)
    weights = strategy["scoring_weights"]
    if sum(weights.values()) != 100:
        raise ValueError(f"scoring_weights must sum to 100, got {sum(weights.values())}")
    return strategy


def deep_merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
