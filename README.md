# Finch Outbound Growth Harness

This harness promotes Finch Agents in public conversations. It finds conversations on Reddit and X where an Agent would genuinely help, drafts a disclosed reply that is useful on its own, and has a human approve every reply. After posting it measures results and tunes the next campaign.

The system has two layers:

| Layer | Question | Where it lives | Changes |
| --- | --- | --- | --- |
| **Tool layer** | What can the system technically do? | `harness/tool_registry.yaml`, `finch_harness/{registry,discovery,publishing,measurement,store}.py` | Rarely: only when a re-research trigger fires |
| **Strategy layer** | What should the system choose to do? | `harness/strategy.yaml`, `finch_harness/{agent_profile,scoring,generation,quality_gate,optimize}.py` | For every Agent and every campaign |

- The Phase 0 research, the tool choices and the rejected tools are in [`docs/phase0-report.md`](docs/phase0-report.md).
- The step-by-step campaign playbook (Phase 1) is in [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md).

## Non-negotiables (enforced in code)

- **Every reply includes the exact Agent URL, unmodified.** The quality gate rejects a draft without it. Finch affiliation is mentioned when it reads naturally (`quality_gate.require_disclosure: false`). The system never poses as an independent user or invents experiences.
- **Every reply needs human approval** (`finch review`) before anything is published.
- **X replies are posted by [x-use](https://github.com/ihuzaifashoukat/x-use)** (browser automation, no X API) only after the human approved each reply text. The X API route is not used: since 2026-02-23 it rejects programmatic replies unless the author mentioned or quoted you.
- **Reddit API posting** (`--mode api`) needs an approved Data API app under the Responsible Builder Policy. It posts at most one comment every 10 minutes and respects a per-subreddit cap. The default mode is manual.
- **No duplicate engagement:** one reply per thread across all campaigns, and a similarity check against every earlier reply.

## Quick start

```bash
pip install -e ".[all,dev]"
cp .env.example .env    # fill in what you have; everything degrades gracefully
finch harness verify --network

finch campaign start https://<finch-agent-url> [--profile harness/profile.example.yaml]
finch discover 1                  # Reddit (+ X if X_BEARER_TOKEN)
finch import 1 web_hits.json      # optional: candidates found by web search / MCP tools
finch score 1                     # 100-pt opportunity score → qualified set
finch draft 1                     # Claude drafts + 35-pt quality gate + rewrite loop
finch review 1                    # HUMAN: approve / reject each draft
finch publish 1                   # manual package (default) or --mode api for Reddit
finch record-post <draft_id> <comment_url>
finch measure 1                   # score, replies, author response
finch import-conversions 1 finch_export.csv   # clicks / trials / usage from Finch
finch analyze 1                   # KEEP / CHANGE / TEST / DROP report → data/campaign-1-report.md
```

If `ANTHROPIC_API_KEY` is not set, the orchestrating Claude Code session (or a person) writes the drafts itself. It registers each one with `finch add-draft <cid> <candidate_id> <style> --text-file reply.md --scores 4,4,4,4,4,5,4,1`. Those drafts go through the same hard checks and thresholds.

## Tests

```bash
pytest -q     # offline end-to-end campaign cycle, no network or LLM needed
```
