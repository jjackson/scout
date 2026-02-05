"""
Agent state definition for Scout data agent platform.

This module defines the AgentState TypedDict that flows through the LangGraph
conversation graph. The state maintains conversation history, user context,
and error correction metadata needed for the agent's self-healing capabilities.

The state is designed to be:
- Serializable: All fields can be persisted to Postgres checkpoints
- Immutable: LangGraph manages state updates through reducers
- Type-safe: Full type hints for IDE support and runtime validation
"""

from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    State object that flows through the Scout agent graph.

    This TypedDict defines all the data that persists across conversation turns
    and gets checkpointed to the database. LangGraph uses this state to:
    - Track conversation history with automatic message deduplication
    - Maintain user and project context for permission scoping
    - Enable the self-correction loop when queries fail

    Attributes
    ----------
    messages : Annotated[list[BaseMessage], add_messages]
        The conversation history. Uses LangGraph's add_messages reducer
        which handles message deduplication by ID. Includes:
        - HumanMessage: User questions
        - AIMessage: Agent responses (may include tool calls)
        - ToolMessage: Results from tool execution (SQL results, errors)
        - SystemMessage: Dynamic context injection

    project_id : str
        UUID of the current project (as string for serialization).
        Used to scope all database queries and knowledge lookups.
        The agent can ONLY access data within this project's schema.

    project_name : str
        Human-readable project name for use in responses.
        Displayed to users and included in provenance explanations.

    user_id : str
        UUID of the current user (as string for serialization).
        Used for audit logging and permission checks.

    user_role : str
        The user's role within this project. Controls:
        - 'viewer': Read-only access, no data modifications
        - 'analyst': Can run queries and create artifacts
        - 'admin': Full access including knowledge management

    needs_correction : bool
        Flag set by the error handling node when a query fails.
        When True, the graph routes back to the agent node for retry
        with the error context. Set to False on successful execution
        or when max retries exceeded.

    retry_count : int
        Number of correction attempts made for the current query.
        Incremented each time needs_correction triggers a retry.
        Reset to 0 when a new user message arrives.
        Max retries is typically 3 (configured in graph builder).

    correction_context : dict
        Structured information about what went wrong and potential fixes.
        Populated by the error analysis node. Contents:
        - 'error_type': Category (syntax, permission, timeout, data)
        - 'error_message': The actual error text
        - 'failed_sql': The SQL that caused the error
        - 'suggestion': Agent-generated fix suggestion
        - 'relevant_learnings': Past learnings that might help

    Example
    -------
    Initial state for a new conversation::

        state = AgentState(
            messages=[],
            project_id="550e8400-e29b-41d4-a716-446655440000",
            project_name="Acme Analytics",
            user_id="user-123",
            user_role="analyst",
            needs_correction=False,
            retry_count=0,
            correction_context={},
        )

    State after a failed query::

        state = AgentState(
            messages=[...],  # includes error in ToolMessage
            project_id="550e8400-e29b-41d4-a716-446655440000",
            project_name="Acme Analytics",
            user_id="user-123",
            user_role="analyst",
            needs_correction=True,
            retry_count=1,
            correction_context={
                "error_type": "syntax",
                "error_message": "column 'usr_id' does not exist",
                "failed_sql": "SELECT * FROM orders WHERE usr_id = 1",
                "suggestion": "Column is named 'user_id', not 'usr_id'",
                "relevant_learnings": [],
            },
        )

    Notes
    -----
    - The add_messages annotation is critical: it enables LangGraph's
      automatic message list management with deduplication by message ID.
    - All UUID fields are stored as strings because TypedDict values
      must be JSON-serializable for checkpoint persistence.
    - The correction loop (needs_correction + retry_count) implements
      the agent's self-healing capability described in the architecture.
    """

    # Conversation history with automatic deduplication
    messages: Annotated[list[BaseMessage], add_messages]

    # Project context - scopes all data access
    project_id: str
    project_name: str

    # User context - for permissions and audit
    user_id: str
    user_role: str

    # Error correction loop state
    needs_correction: bool
    retry_count: int
    correction_context: dict
