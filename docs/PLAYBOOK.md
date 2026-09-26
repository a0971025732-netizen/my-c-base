# Phase 1 Playbook: one campaign per Finch Agent URL

Use this when the user hands you **one Finch Agent URL**. Do not repeat the Phase 0 research unless a re-research trigger in `harness/tool_registry.yaml` has fired.

| Step | Command | Orchestrator responsibility |
| --- | --- | --- |
| 1.1 Load harness | `finch harness verify --network` | Report which capabilities are ready. Missing credentials are not a reason to re-research. |
| 1.2 Load agent | `finch campaign start <URL>` | Check the profile. If the page could not be read, fill in `--profile` from what the user told you. Never invent capabilities or free-usage numbers. |
| 1.3 Discover | `finch discover <cid>`, plus WebSearch → `finch import` | Cover the full range of intents: questions, recommendations, workflows, comparisons, experiences, building, education, emerging topics. |
| 1.4 Baseline | `harness/strategy.yaml` | 40–60 candidates, 12–16 qualified, 5–8 published, at most 15. |
| 1.5 Score | `finch score <cid>` | Spot-check the top 5 and bottom 5 of the qualified set. |
| 1.6–1.7 Draft + gate | `finch draft <cid>` or `finch add-draft` | Minimum 28/35. Promotional intensity ≤ 2. Agent fit ≥ 4. Conversation fit ≥ 4. Must contain the exact URL and a disclosure. |
| Human approval | `finch review <cid>` | **Required.** Nothing is published without it. |
| 1.8 Publish | `finch publish <cid>` then `finch record-post` | X is always manual. Reddit goes through the API only with an approved app and `--mode api`. |
| 1.9 Memory | automatic (SQLite `data/finch.db`) | Stores queries, scores, drafts, publications, metrics and conversions. |
| Measure | `finch measure`, `finch import-conversions` | Run about 24 h and 72 h after publishing. |
| 1.10 Optimize | `finch analyze <cid>` | Promote a confirmed **TEST** finding into `strategy.yaml` only after at least 3 samples. |

Carry-over between campaigns happens automatically:

- Queries classified **DROP** for the same Agent are removed.
- Comment-style performance from all earlier campaigns shifts which style gets picked.
- Threads that were already engaged are never engaged again.
