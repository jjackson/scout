# OAuth Token Pass-Through for Data Materialization

**Date:** 2026-02-17
**Status:** Approved

## Goal

Enable the MCP server to pull data from CommCare HQ and CommCare Connect APIs on behalf of users, using their OAuth tokens. Django mediates authentication — the MCP server trusts Django and never independently validates tokens.

## Architecture Overview

```
User (browser)
  → Django (session auth, owns OAuth tokens)
    → LangGraph agent (tokens in config, not state)
      → MCP server (tokens in _meta, used for API calls, discarded)
        → CommCare HQ / CommCare Connect APIs
```

Tokens flow from Django to MCP per-request. They are never persisted in the MCP server, never visible to the LLM, and never stored in the LangGraph checkpointer.

## 1. Token Storage

### Enable allauth token persistence

Set `SOCIALACCOUNT_STORE_TOKENS = True` in `config/settings/base.py`. This makes allauth save `SocialToken` records (access token, refresh token, expiry) after OAuth login.

### Fernet encryption at rest

Allauth stores tokens in plaintext. Add a custom `SocialAccountAdapter` that encrypts `token` and `token_secret` fields using the existing `DB_CREDENTIAL_KEY` Fernet key (same key used for `DatabaseConnection` credentials).

Override `serialize_instance` / `deserialize_instance` in the adapter so allauth works normally but tokens are encrypted in the database.

### CommCare Connect provider

Add a second allauth provider at `apps/users/providers/commcare_connect/`:

```
apps/users/providers/
├── commcare/              # existing — CommCare HQ
│   ├── provider.py        # id = "commcare"
│   ├── views.py           # endpoints: commcarehq.org
│   └── urls.py
└── commcare_connect/      # new — CommCare Connect
    ├── provider.py        # id = "commcare_connect"
    ├── views.py           # endpoints: TBD (placeholders)
    └── urls.py
```

Mirrors the existing CommCare HQ pattern. OAuth endpoints are placeholders until Connect's URLs are confirmed.

Add `"apps.users.providers.commcare_connect"` to `INSTALLED_APPS` and its config to `SOCIALACCOUNT_PROVIDERS`.

## 2. Token Flow — Django to MCP Server

### Retrieval

New helper `get_user_oauth_tokens(user)` in `apps/agents/mcp_client.py`:
- Queries `SocialToken` for the user's CommCare HQ and CommCare Connect accounts
- Decrypts tokens via the Fernet adapter
- Returns: `{"commcare": "<access_token>", "commcare_connect": "<access_token>"}`
- Returns empty dict for providers the user hasn't connected

### Injection into chat view

In `apps/chat/views.py`, after loading MCP tools:
1. Call `get_user_oauth_tokens(request.user)`
2. Pass the tokens dict into `build_agent_graph()` via a new `oauth_tokens` parameter

### Passing through the graph

In `apps/agents/graph/base.py`:
- Accept `oauth_tokens` parameter in `build_agent_graph()`
- Pass tokens via the LangGraph `config` dict (not `AgentState`)
- `config` is not checkpointed and not visible to the LLM

### MCP transport-layer injection

Tokens are injected into the MCP `_meta` field at the transport layer, invisible to the LLM. The LLM invokes a materialization tool with just the logical parameters (e.g., form ID, date range). The transport layer adds:

```json
{"_meta": {"oauth_tokens": {"commcare": "...", "commcare_connect": "..."}}}
```

Only materialization tools receive tokens. Existing data access tools (query, list_tables, etc.) are unchanged.

## 3. Token Refresh

### Proactive refresh

Before injecting tokens into MCP metadata, check `SocialToken.expires_at`. If the token expires within 5 minutes, refresh it first.

### Refresh service

New `apps/users/services/token_refresh.py` with `refresh_oauth_token(user, provider)`:
- Loads `SocialToken` + `SocialApp` (client ID/secret)
- Posts to the provider's token endpoint with `grant_type=refresh_token`
- Updates `SocialToken` with new access token + expiry
- Returns the new access token

### Reactive refresh

If the MCP server returns `AUTH_TOKEN_EXPIRED` error code, the chat view:
1. Refreshes the token
2. Retries the graph step once
3. If refresh itself fails (revoked/expired refresh token), returns a user-facing message asking them to re-authorize

## 4. MCP Server Changes

### Token extraction

New `mcp_server/auth.py` with `extract_oauth_tokens(meta)`:
- Extracts `oauth_tokens` dict from MCP request `_meta` field
- Returns empty dict if not present

### Context

Tokens are carried in a per-request context (not in `ProjectContext`, which is about DB config). Either extend the tool handler signatures or use a separate `RequestContext` dataclass.

### New error code

Add `AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"` to `mcp_server/envelope.py`. Returned when an upstream API call gets a 401, signaling Django to refresh and retry.

### Materialization tools (future)

The OAuth plumbing comes first. Materialization tools (`materialize_commcare`, `materialize_commcare_connect`) are a separate implementation phase that will use this token infrastructure.

## 5. Security

| Concern | Mitigation |
|---------|------------|
| Tokens in logs | Scrub `_meta.oauth_tokens` before audit logging in `envelope.py` |
| Tokens visible to LLM | Transport-layer injection (Option B) — LLM never sees tokens |
| Tokens in checkpointer | Use LangGraph `config` dict, not `AgentState` — not persisted |
| Tokens at rest | Fernet encryption using existing `DB_CREDENTIAL_KEY` |
| Token scope | Request minimum scopes (read-only data access) |
| Tokens in error responses | Error envelope must never include the token |

## Files Changed (Summary)

### New files
- `apps/users/providers/commcare_connect/provider.py`
- `apps/users/providers/commcare_connect/views.py`
- `apps/users/providers/commcare_connect/urls.py`
- `apps/users/providers/commcare_connect/__init__.py`
- `apps/users/providers/commcare_connect/apps.py`
- `apps/users/services/token_refresh.py`
- `mcp_server/auth.py`

### Modified files
- `config/settings/base.py` — enable `STORE_TOKENS`, add Connect provider
- `apps/users/adapters.py` — Fernet encryption adapter (new or modified)
- `apps/agents/mcp_client.py` — `get_user_oauth_tokens()` helper
- `apps/chat/views.py` — retrieve and pass tokens
- `apps/agents/graph/base.py` — accept `oauth_tokens`, pass via `config`
- `mcp_server/envelope.py` — `AUTH_TOKEN_EXPIRED` code, log scrubbing
- `mcp_server/server.py` — token extraction in materialization tool handlers
