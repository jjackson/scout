# MCP Chat Integration Test Plan

**Date:** 2026-02-16
**Goal:** Verify the full MCP integration path from `POST /api/chat/` through the LangGraph agent to MCP tool execution and SSE streaming back to the frontend.

## Architecture Under Test

```
POST /api/chat/
    → chat_view (auth, validation, project membership)
    → get_mcp_tools() (MCP client → MCP server)
    → build_agent_graph() (LLM + MCP tools + local tools)
    → langgraph_to_ui_stream() (agent execution → SSE)
    → StreamingHttpResponse (AI SDK v6 UI Message Stream Protocol)
```

## Test Layers

### Layer 1: Chat Endpoint Validation

Tests that the chat view correctly validates requests before reaching the agent.

| Test | Input | Expected |
|------|-------|----------|
| Unauthenticated request | No session | 401 |
| Missing messages | `{data: {projectId: X}}` | 400 |
| Missing projectId | `{messages: [...]}` | 400 |
| Empty message content | `{messages: [{content: ""}]}` | 400 |
| Non-member project | Valid user, wrong project | 403 |
| Inactive project | Valid member, inactive project | 403 |
| Message too long | >10,000 chars | 400 |
| GET method | GET request | 405 |

### Layer 2: MCP Tool Loading

Tests that MCP tools are loaded and failures are handled gracefully.

| Test | Scenario | Expected |
|------|----------|----------|
| MCP tools load successfully | Mock `get_mcp_tools` returns tools | Agent receives tools |
| MCP tools fail to load | Mock `get_mcp_tools` raises | 500 with error ref |

### Layer 3: Agent Graph Assembly with MCP Tools

Tests that the agent graph correctly includes MCP tools alongside local tools.

| Test | Scenario | Expected |
|------|----------|----------|
| MCP tools included in graph | Pass mock MCP tools | Tools available in ToolNode |
| Empty MCP tools fallback | Pass empty list | Only local tools in ToolNode |
| Tool names preserved | MCP tool names | query, list_tables, describe_table, get_metadata |

### Layer 4: SSE Stream Format

Tests that MCP tool calls/results produce correct UI Message Stream Protocol events.

| Test | Scenario | Expected SSE events |
|------|----------|-------------------|
| Text-only response | Agent returns text | start → start-step → text-start → text-delta(s) → text-end → finish-step → finish |
| Tool call + result | Agent calls tool, gets result | start → ... → tool-input-available → tool-output-available → ... → finish |
| Tool output truncation | Output >2000 chars | Output truncated to 2000 chars |
| Error during streaming | Agent raises exception | Error text-delta emitted, stream finishes cleanly |
| Reasoning blocks | Agent emits thinking blocks | reasoning-start → reasoning-delta(s) → reasoning-end |

### Layer 5: MCP Error → Self-Correction Loop

Tests the error handling chain when MCP tools return error envelopes.

| Test | Scenario | Expected |
|------|----------|----------|
| MCP envelope error detected | `{success: false, error: {code, message}}` | `needs_correction=True` with context |
| Error classification | Various MCP error messages | Correct error_type (syntax, column_not_found, etc.) |
| Retry triggers diagnosis | `needs_correction=True` | diagnose_and_retry_node runs, retry_count increments |
| Max retries exceeded | retry_count >= 3 | Agent gives up, explains to user |

### Layer 6: End-to-End Streaming (Chat View → SSE)

Tests the full path with mocked LLM and MCP tools.

| Test | Scenario | Expected |
|------|----------|----------|
| Simple text response | LLM returns text only | Valid SSE stream with text events |
| Tool call flow | LLM calls MCP tool | SSE includes tool-input-available and tool-output-available |
| Thread created | New thread_id | Thread record created in DB |
| Checkpointer fallback | PostgreSQL unavailable | Falls back to MemorySaver |

## Mock Strategy

- **LLM (ChatAnthropic):** Mock to control tool calls and text responses
- **MCP Server:** Mock `get_mcp_tools()` to return fake LangChain tools
- **Checkpointer:** Use `MemorySaver` (no PostgreSQL needed)
- **Django ORM:** Use real test DB with fixtures for User, Project, ProjectMembership, DatabaseConnection
- **Agent graph:** For stream tests, mock `agent.astream_events()` to emit controlled events

## Fixtures Needed

1. `user` - Test user (exists in conftest.py)
2. `project` - Active project with database connection
3. `membership` - ProjectMembership linking user to project
4. `authenticated_async_client` - Django async test client with session auth
5. `mock_mcp_tools` - Fake LangChain tools mimicking MCP tool signatures
6. `mock_agent` - Mock compiled LangGraph agent with controlled event stream

## Test File

`tests/test_mcp_chat_integration.py`
