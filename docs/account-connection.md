# Connecting X and Moltbook for automated publishing

Checked 2026-09-26.

## Moltbook

- Moltbook only supports `moltbook_...` API keys. It has no OAuth and no "log in with X" for agents (see https://www.moltbook.com/skill.md).
- The proxy-injected credential ("moltbook key") sends a value starting with `MOLTBOOK...`, and Moltbook rejects it with a 401.
- Fix: store the key as a plain **environment variable** `MOLTBOOK_API_KEY` in the cloud environment settings, not under API credentials. `runs/*/mb_publish.py` reads it directly.
- If the key is unknown, regenerate it from the owner dashboard: https://www.moltbook.com/login

## X

The proxy-injected `auth_token` / `ct0` cookies return `code 89`. Cookies expire, so don't rely on them.
Instead, connect X through an OAuth connector at claude.ai/customize/connectors (log in in the browser, no key handling), then start a new session:

| Option | Reply to a post | Search | Notes |
|---|---|---|---|
| Composio Twitter toolkit (custom connector) | yes | yes | Best fit for the reply workflow |
| Zapier (in the connector directory) | limited | limited | One-click; per-action setup in Zapier |
| Buffer MCP `https://mcp.buffer.com/mcp` | no | no | New posts only, so it doesn't fit comment outreach |
| X official MCP (XMCP) | yes | yes | Needs your own X developer app and pay-per-use billing |
