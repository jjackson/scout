# Task Plan

## Goal
Break down the Data Explorer MCP Server design document (`docs/data-explorer-mcp-design.md`) into implementable phases. Produce a scoped, ordered plan with clear boundaries, dependencies, and decision points — without writing implementation code.

## Key Reference
- Design doc: `docs/data-explorer-mcp-design.md`
- Existing MCP server: `mcp_server/` (stub tools from prior work)
- Backend apps: `apps/` (projects app has DB connection infrastructure)

## Planning Phases

### Phase 1 - Requirements & Discovery [COMPLETE]
- [x] Audit existing codebase for reusable infrastructure
- [x] Map design doc components to existing Django apps and identify gaps
- [x] Identify MCP SDK/framework → FastMCP v1.26.0
- [x] Document external dependencies

### Phase 2 - Architecture Scoping [COMPLETE]
- [x] Deployment model → standalone process with Django ORM access (AD-4)
- [x] Auth strategy → project context via CLI arg (stdio) or request metadata (HTTP)
- [x] Schema provisioning → use existing project schema, no dynamic provisioning (AD-5)
- [x] Metadata service → reuse DataDictionaryGenerator + TableKnowledge
- [x] Materialization → deferred to v2 (AD-2)
- [x] Data model → connector-centric, tenant = project for v1 (AD-1, AD-3)

### Phase 3 - Implementation Plan [COMPLETE]
- [x] Define v1 minimal scope
- [x] Order into incremental milestones
- [x] Identify risks and open questions
- [x] Write implementation plan (see below)

### Phase 4 - Review & Finalize
- [ ] Review plan against design doc for completeness
- [ ] Document deferred items (v2+) and rationale
- [ ] Get user sign-off

---

## v1 Implementation Plan

### Summary

v1 delivers a working MCP server that gives any MCP-compatible agent secure, read-only access to a Scout project's database. It reuses existing infrastructure heavily (SQL validation, schema introspection, connection pooling) and runs as a standalone process that imports Django models.

**v1 tools**: `list_tables`, `describe_table`, `get_metadata`, `query`
**Transport**: stdio (dev), streamable-http (prod)
**Auth**: Project ID passed via CLI arg (stdio) or resolved from request context (HTTP)

---

### Milestone 1: Project-Aware MCP Server Scaffold

**Goal**: MCP server starts up, loads a project from Django ORM, and responds to `tools/list`.

**Work**:
1. Configure Django ORM in `mcp_server/` — add `django.setup()` with `DJANGO_SETTINGS_MODULE` in server startup
2. Add `--project-id <uuid>` CLI argument to `mcp_server/server.py`
3. On startup: load `Project` + `DatabaseConnection` from DB, validate project exists and is active
4. Store project context in a module-level variable (or FastMCP server state) accessible to tool handlers
5. Remove the two existing stub tools (`execute_sql`, `get_schema`)
6. Register the 4 v1 tools as empty stubs that return the project context (proves wiring works)

**Test**: Run `python -m mcp_server --project-id <uuid>` over stdio. Send `tools/list` → get back 4 tool definitions with correct schemas.

**Depends on**: Nothing. Can start immediately.

**Key files**:
- `mcp_server/server.py` (modify)
- `mcp_server/context.py` (new — project context holder)

---

### Milestone 2: Metadata Tools (`list_tables`, `describe_table`, `get_metadata`)

**Goal**: Agent can discover what data is available in the project's database.

**Work**:
1. Create `mcp_server/services/metadata.py` — adapter around `DataDictionaryGenerator`
   - Accept a project, return structured metadata
   - If `project.data_dictionary` is stale or missing, regenerate it
   - Merge `TableKnowledge` annotations (descriptions, column notes, use cases)
2. Implement `list_tables` tool:
   - Returns table names, types (table/view), row count estimates, descriptions
   - Respects `project.allowed_tables` / `project.excluded_tables`
3. Implement `describe_table` tool:
   - Returns columns, types, nullability, PKs, FKs, indexes, sample values
   - Includes TableKnowledge enrichments if available
   - Case-insensitive matching with suggestions on miss
4. Implement `get_metadata` tool:
   - Full schema snapshot (all tables + relationships + semantic layer)
   - Single call for agent to build comprehensive understanding

**Test**: Point at a real project DB, call each tool, verify output matches data dictionary.

**Depends on**: Milestone 1 (project context available).

**Reuses**:
- `apps/projects/services/data_dictionary.py` — DataDictionaryGenerator
- `apps/knowledge/models.py` — TableKnowledge
- `apps/agents/tools/describe_table.py` — formatting logic

**Key files**:
- `mcp_server/services/metadata.py` (new)
- `mcp_server/tools/metadata.py` (new — tool handlers)

---

### Milestone 3: Query Tool (`query`)

**Goal**: Agent can execute read-only SQL against the project's database.

**Work**:
1. Create `mcp_server/services/query.py` — adapter around SQLValidator + ConnectionPoolManager
   - Validate SQL (SELECT-only, single statement, no dangerous functions)
   - Enforce table allowlists from project config
   - Inject LIMIT from `project.max_rows_per_query`
   - Execute via connection pool with `SET ROLE` to `project.readonly_role`
   - Apply `project.max_query_timeout_seconds` as statement_timeout
2. Implement `query` tool:
   - Input: SQL string
   - Output: columns, rows, row_count, truncated flag, executed SQL
   - Error responses with sanitized messages (no internal details)
3. Add rate limiting (reuse QueryRateLimiter or stub for v1)

**Test**: Execute valid/invalid queries, verify enforcement of limits, role isolation, and error handling.

**Depends on**: Milestone 1 (project context + DB connection).

**Reuses**:
- `apps/agents/tools/sql_tool.py` — SQLValidator, dangerous function blocklist
- `apps/projects/services/db_manager.py` — ConnectionPoolManager
- `apps/projects/services/rate_limiter.py` — QueryRateLimiter

**Key files**:
- `mcp_server/services/query.py` (new)
- `mcp_server/tools/query.py` (new — tool handler)

---

### Milestone 4: Response Envelope + Error Handling

**Goal**: Consistent response format across all tools, proper error handling.

**Work**:
1. Define response envelope (per design doc section 7.5):
   ```json
   {"success": true, "data": {...}, "project_id": "...", "schema": "...", "timing_ms": 142}
   ```
2. Centralize error handling:
   - Permission errors → `PERMISSION_DENIED`
   - Validation errors → `VALIDATION_ERROR`
   - Connection errors → `CONNECTION_ERROR` (sanitized)
   - Timeout → `QUERY_TIMEOUT`
3. Add timing instrumentation to all tool handlers
4. Add query audit logging (structured log output, not a DB table in v1)

**Test**: Trigger each error case, verify envelope structure and error codes.

**Depends on**: Milestones 2 + 3 (tools exist to wrap).

**Key files**:
- `mcp_server/envelope.py` (new — response/error helpers)
- Modify all tool handlers to use envelope

---

### Milestone 5: Integration Testing + Scout Agent Wiring

**Goal**: Scout's LangGraph agent uses the MCP server as a tool provider instead of its built-in tools.

**Work**:
1. Write integration tests:
   - Spin up MCP server over stdio against a test database
   - Exercise all 4 tools via MCP client
   - Verify security boundaries (table allowlists, readonly, SQL validation)
2. Wire Scout's agent to use MCP:
   - Option A: LangGraph agent spawns MCP server as subprocess, uses MCP tools
   - Option B: Agent calls MCP server over HTTP
   - This milestone bridges the two systems
3. Verify end-to-end: user asks question in Scout UI → agent calls MCP tools → results streamed back

**Test**: End-to-end test from chat input to query result.

**Depends on**: Milestones 1-4 (all tools working).

**Key files**:
- `tests/test_mcp_integration.py` (new)
- `apps/agents/graph/base.py` (modify — add MCP tool binding)

---

### Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Django ORM in standalone process adds startup overhead | Slow MCP server cold start | Lazy initialization, keep process alive (HTTP mode) |
| psycopg2 ThreadedConnectionPool in async context | Potential blocking | v1 uses sync tools (FastMCP handles threading). Evaluate asyncpg for v2. |
| SQLValidator coupled to LangChain tool interface | Refactoring needed | Extract validation logic into standalone functions, keep LangChain wrapper separate |
| DataDictionaryGenerator tightly coupled to Project model | Adapter complexity | Thin adapter layer in `mcp_server/services/` |

---

### Deferred to v2+

| Feature | Rationale |
|---|---|
| **Schema provisioning/teardown** | Not needed until materialization creates data in dynamic schemas |
| **Materialization** (loaders, dbt) | Largest work item. Needs connector model, pipeline registry, Celery tasks |
| **Connector system** | OAuth to external APIs, config UI, credential storage. Precondition for materialization |
| **Dynamic auth** (OAuth/API keys) | v1 uses project ID directly. Token-based auth needed when MCP server is exposed to external clients |
| **Audit table** | v1 uses structured logging. DB-backed audit trail for compliance in v2 |
| **Semantic layer (YAML)** | v1 uses TableKnowledge from DB. Formal YAML semantic layer per design doc in v2 |
| **Progress streaming** | Only relevant for long-running materialization. No long-running ops in v1 |
| **Redis-backed rate limiting** | v1 in-memory rate limiter sufficient for single-process deployment |

## Current Phase: Phase 4 - Review & Finalize
