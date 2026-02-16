# Findings

## Design Doc Summary
Source: `docs/data-explorer-mcp-design.md`

### Core Components
1. **Auth Layer** — OAuth 2.0 or pass-through token, resolves user to tenant
2. **Session Manager** — Per-session state: tenant ID, schema name, permissions
3. **Schema Manager** — Creates/tears down tenant-scoped PostgreSQL schemas
4. **Metadata Service** — Introspects DB catalogs, exposes table/column metadata
5. **Materializer** — Orchestrates data loading (API ingestion) + dbt transforms
6. **Tool Router** — Maps MCP tool calls to services with tenant context

### MCP Tools (13 total)
- Metadata: `list_databases`, `list_tables`, `describe_table`, `get_metadata`
- Query: `query` (read-only SQL)
- Schema: `provision_schema`, `teardown_schema`, `list_schemas`
- Materialization: `list_pipelines`, `run_materialization`, `get_materialization_status`, `cancel_materialization`

### Key Design Decisions
- Schema reuse across sessions (TTL-based cleanup, not per-session)
- Full-refresh materialization only in v1 (incremental deferred)
- Read-only queries only in v1 (no agent DDL)
- Metadata persists separately from data schemas

---

## Codebase Audit

### 1. Existing MCP Server (`mcp_server/`)

**SDK**: FastMCP v1.26.0 (`mcp>=1.0` in pyproject.toml)

**Files**: 3 files, ~2.6 KB total
- `__init__.py` — Package docstring
- `__main__.py` — Entry point calling `main()` from server
- `server.py` — CLI + 2 stub tools

**Current Tools** (both raise `NotImplementedError`):
- `execute_sql(query: str) -> dict` — Read-only SQL
- `get_schema() -> dict` — Database schema

**Transport**: CLI supports `--transport stdio|streamable-http`, default stdio, HTTP on `127.0.0.1:8100`

**Assessment**: Minimal scaffold. Tool names don't match design doc. Server name is `"scout"`. Good foundation to build on — FastMCP handles tool registration, schema generation, and transport.

### 2. Database Connection Infrastructure (`apps/projects/`)

**ConnectionPoolManager** (`services/db_manager.py`):
- Thread-safe singleton with per-project psycopg2 `ThreadedConnectionPool`
- Context manager: `with pool_manager.get_connection(project) as conn:`
- Read-only enforcement at psycopg2 level, auto-rollback on error
- Config: min=1, max=5 connections per project (env-configurable)

**DatabaseConnection model** (`models.py`):
- Fernet-encrypted `_db_user` / `_db_password` (BinaryField)
- `get_connection_params(schema, timeout_seconds)` → psycopg2 dict
- Credentials never exposed in API responses (write-only serializer fields)

**Project model** (`models.py`):
- FK to DatabaseConnection (PROTECT)
- `db_schema` — validated (regex: alphanumeric + underscore)
- `allowed_tables` / `excluded_tables` — JSONField allowlist/blocklist
- `max_rows_per_query` (default 500), `max_query_timeout_seconds` (default 30)
- `readonly_role` — PostgreSQL role for read-only access
- `data_dictionary` — cached introspection (JSONField)
- `system_prompt` — per-project agent prompt

**ProjectMembership** — Links users to projects with roles: `viewer`, `analyst`, `admin`

**Reusability**: HIGH. Connection pooling, encrypted credentials, schema validation, and table allowlisting map directly to MCP server needs. The `readonly_role` field is exactly what the design doc's `SET ROLE` pattern needs.

### 3. Schema Introspection (`apps/projects/services/data_dictionary.py`)

**DataDictionaryGenerator class** — Full PostgreSQL introspection:
- Tables (with row count estimates from pg_stat)
- Columns (type, nullable, default, comments, sample values)
- Primary keys, foreign keys, indexes
- Enum types
- Sensitive column detection (password, token, ssn, etc. excluded from sampling)

**Output format**: JSON dict with `schema`, `generated_at`, `tables`, `enums`

**Methods**:
- `generate()` — Full introspection, saves to project.data_dictionary
- `render_for_prompt(max_tables_inline=15)` — Formatted for agent consumption

**Reusability**: HIGH. This IS the metadata service. Would need to be adapted to work with tenant-scoped schemas instead of project schemas, but the introspection queries are production-ready.

### 4. SQL Validation & Execution (`apps/agents/tools/sql_tool.py`)

**SQLValidator class**:
- SELECT-only enforcement (blocks INSERT, UPDATE, DELETE, DDL, etc.)
- Single-statement validation (prevents batched queries)
- 103+ dangerous function blocklist (pg_read_file, dblink_*, lo_import, etc.)
- Table/schema allowlist enforcement via sqlglot AST
- Automatic LIMIT injection
- Uses `sqlglot` for SQL parsing

**SQLExecutionResult** dataclass: columns, rows, row_count, truncated, sql_executed, tables_accessed, error

**create_sql_tool(project, user)** — Factory creating a LangChain tool with validation + rate limiting + connection pool

**Reusability**: HIGH. The validator is exactly what the MCP `query` tool needs. Would need to swap the LangChain tool wrapper for an MCP tool handler.

### 5. Rate Limiting (`apps/projects/services/rate_limiter.py`)

**QueryRateLimiter** — In-memory, thread-safe singleton:
- Per-user: 10/min, 100/hour
- Per-project: 1000/day
- Note: recommends Redis for distributed deployment

**Reusability**: MEDIUM. Pattern works but in-memory won't scale. Design doc implies Redis-backed limits.

### 6. Auth Infrastructure (`apps/users/`)

**User model**: Email-based auth (USERNAME_FIELD="email"), custom UserManager

**Session auth**:
- Cookie: `sessionid_scout`, CSRF: `csrftoken_scout`
- CSRF_COOKIE_HTTPONLY=False (frontend reads it)
- No JWT / no bearer tokens currently

**OAuth** (django-allauth):
- Google (profile + email scopes)
- GitHub (user:email scope)
- CommCare (custom provider in `apps/users/providers/commcare/`)
- Auto-signup and auto-connect enabled

**Permissions** (`apps/projects/api/permissions.py`):
- `check_project_access()` — membership check
- `check_edit_permission()` — analyst or admin
- `check_admin_permission()` — admin only
- Superuser bypass

**Reusability for MCP**: PARTIAL. No token/scope system exists. Django sessions don't naturally translate to MCP auth. Options:
1. Pass-through: MCP server validates session cookie via Django middleware (tight coupling)
2. API keys: New model with scopes/expiry (clean but new work)
3. OAuth token validation: Validate allauth tokens directly (possible but allauth manages tokens internally)

### 7. Chat & Streaming (`apps/chat/`)

**Streaming** (`views.py`, `stream.py`):
- `async def chat_view(request)` — raw Django async view (not DRF)
- `StreamingHttpResponse` with SSE format (`data: {json}\n\n`)
- `stream.py` translates LangGraph `astream_events(v2)` → Vercel AI SDK v6 UI Message Stream chunks
- Headers: `text/event-stream`, `no-cache`, `X-Accel-Buffering: no`

**LangGraph** (`apps/agents/graph/`):
- `build_agent_graph(project, user, checkpointer)` → compiled StateGraph
- Pattern: agent → should_continue? → tools → check_result → retry loop (max 3)
- AgentState TypedDict with message pruning (max 20)

**Checkpointer** (`apps/agents/memory/checkpointer.py`):
- Lazy singleton via `AsyncConnectionPool` (psycopg_pool, max_size=20)
- Falls back to `MemorySaver` in test mode or if postgres unavailable
- DB URL resolution: DATABASE_URL → individual env vars → Django settings

**Threads** (`models.py`):
- UUID PK, FK to project + user
- Sharing: `is_shared`, `is_public`, `share_token`

**Reusability**: MEDIUM. The streaming and async patterns are useful reference but the chat system is tightly coupled to LangGraph/Vercel AI SDK. The checkpointer pattern is reusable for MCP session persistence.

### 8. Background Tasks (Celery)

**Config** (`config/celery.py`):
- Broker: Redis (CELERY_BROKER_URL)
- JSON serializer, 30-min time limit, prefetch=1
- Scheduler: django_celery_beat
- Auto-discovery enabled

**Active tasks**: None (only debug_task). Infrastructure exists but unused.

**Reusability**: HIGH for materialization. Celery is exactly what the design doc describes for long-running pipeline execution. Workers would run loaders and dbt, with progress reported back via task events.

### 9. Knowledge Layer (`apps/knowledge/`)

**TableKnowledge** — Semantic metadata per table:
- description, use_cases, data_quality_notes, owner, refresh_frequency
- related_tables (join hints), column_notes (per-column annotations)

**KnowledgeEntry** — General knowledge (title, markdown, tags)

**AgentLearning** — Auto-discovered corrections with confidence scoring

**Reusability**: HIGH for semantic layer. TableKnowledge maps directly to the design doc's semantic layer concept. Would need to be extended for tenant-scoped metadata.

---

## Reusability Matrix

| Design Doc Component | Existing Code | Reuse Level | Gap |
|---|---|---|---|
| **Auth Layer** | django-allauth, session auth | LOW | No token/scope system. Need new auth mode for MCP. |
| **Session Manager** | Chat thread model, checkpointer | LOW | MCP sessions differ from chat threads. Need new. |
| **Schema Manager** | Project model has `db_schema`, `readonly_role` | MEDIUM | Provisioning/teardown logic doesn't exist. `SET ROLE` pattern fits. |
| **Metadata Service** | DataDictionaryGenerator, describe_table | HIGH | Already introspects PostgreSQL. Needs tenant-scoped adapter. |
| **Query Tool** | SQLValidator, sql_tool, ConnectionPoolManager | HIGH | Core logic exists. Swap LangChain wrapper for MCP handler. |
| **Materializer** | Celery infrastructure | MEDIUM | Queue exists but no loaders/dbt integration yet. All new. |
| **Tool Router** | FastMCP tool registration | HIGH | FastMCP handles routing. Add scope-checking middleware. |
| **Rate Limiting** | QueryRateLimiter | MEDIUM | Works but in-memory. Needs Redis for production. |
| **Audit Logging** | Query logging in sql_tool | LOW | Partial. Need structured audit table. |

---

## Architecture Decisions

### AD-1: Connector-Centric Data Model

The design doc's "pipeline registry" maps to a **connector** system:

```
Connector Type (e.g. CommCare, Salesforce)
  - Defines: API endpoints, loader scripts, dbt models, available entities
  - Ships with the MCP server (code + config)

Connector Instance (e.g. "Acme Corp's CommCare project")
  - Created when user does "connect my CommCare project"
  - Stores: OAuth tokens, project-specific config, sync preferences
  - Scoped to a tenant/project
  - Has configuration knobs (which forms, date ranges, modules, etc.)
```

**Data flow when user asks "show me total visits since Dec":**
1. Agent receives question
2. Agent calls MCP `list_tables` or `get_metadata` → sees what's already materialized
3. If visits data not present, agent checks available connectors via `list_pipelines`
4. Agent calls `run_materialization(pipeline="commcare", entities=["visits"])`
5. MCP server uses connector instance's stored auth to call CommCare API
6. Data lands in user's schema, dbt transforms run
7. Agent queries materialized data

**Key insight**: Scout manages connector lifecycle (setup UI, OAuth flows, config). MCP server consumes connector config to materialize and query. Both systems know about connectors — Scout for setup/management, MCP for execution.

### AD-2: v1 Scope — Metadata + Query Only

Materialization (loaders, dbt, connectors) deferred to v2. v1 assumes data already exists in the target database (like current Scout model — project points to an existing database with data).

This means v1 tools: `list_tables`, `describe_table`, `get_metadata`, `query`. No schema provisioning in v1.

### AD-3: Tenant = Project (for v1)

In v1, Scout's `project_id` serves as the tenant scope. A project already encapsulates: database connection, schema, table allowlists, query limits, and user memberships. The MCP server receives project context and operates within those boundaries.

An org/tenant layer above projects may come later if multi-project tenants are needed.

### AD-4: Standalone Process with Django ORM Access

MCP server runs as a separate process (like Celery workers) but shares Django settings and can import Django models. This gives it direct access to Project, DatabaseConnection, etc. without duplicating model definitions or encryption logic.

```
Scout (Django web app)          MCP Server (FastMCP standalone)
        │                                │
        │  both read from                │  imports Django models
        └──────────┐  ┌─────────────────┘  via DJANGO_SETTINGS_MODULE
                   │  │
                   ▼  ▼
              Scout PostgreSQL DB
              (projects, users, connections)
                   │
                   │  MCP server also connects to
                   ▼
              Project's Target DB
              (user data, queried via connection pool)
```

**How Scout invokes the MCP server:**
- **Dev (stdio)**: LangGraph agent spawns MCP server as subprocess, passes `--project-id <uuid>` as CLI arg. MCP server loads project config from Django ORM.
- **Prod (HTTP)**: MCP server runs as a service. Project context passed per-request in MCP metadata or resolved from auth token.

### AD-5: Use Existing Schema (v1)

No dynamic schema provisioning in v1. MCP server queries the project's pre-configured `db_schema` with the project's `readonly_role` via `SET ROLE`. This matches current Scout behavior exactly. Schema provisioning becomes relevant in v2 when materialization needs isolated staging areas.

## Open Questions

### Resolved
1. ~~**Materialization v1**: Deferred to v2. v1 is metadata + query.~~ → AD-2
2. ~~**Tenant model**: tenant = project for v1.~~ → AD-3
3. ~~**Datasource linking**: Connector-centric model.~~ → AD-1
4. ~~**MCP server deployment**: Standalone process.~~ → AD-4
5. ~~**Schema provisioning in v1**: Use existing project schema, no dynamic provisioning.~~ → AD-5

### Open
6. **Auth for MCP**: How does the MCP server authenticate requests? (Likely project-scoped token or session pass-through — TBD based on how Scout invokes the MCP server)
7. **Connection pooling**: Reuse psycopg2 ThreadedConnectionPool or switch to async?
8. **Connector model location**: Does the connector/integration model live in Scout (Django app) or in the MCP server, or shared? (v2 question)
