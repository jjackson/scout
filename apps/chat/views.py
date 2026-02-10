"""
Chat views: streaming chat endpoint and auth API.

The chat endpoint is a raw async Django view (not DRF) because DRF
does not support async streaming responses.  Auth endpoints are also
plain Django views to keep this app self-contained.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid

from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.http import JsonResponse, StreamingHttpResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from apps.agents.graph.base import build_agent_graph
from apps.agents.memory.checkpointer import get_database_url
from apps.chat.stream import langgraph_to_data_stream
from apps.projects.models import Project, ProjectMembership

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Checkpointer singleton (lazy initialization)
# ---------------------------------------------------------------------------
_checkpointer = None


async def _ensure_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        database_url = get_database_url()
        saver_cm = AsyncPostgresSaver.from_conn_string(database_url)
        checkpointer = await saver_cm.__aenter__()
        await checkpointer.setup()
        _checkpointer = checkpointer
        logger.info("PostgreSQL checkpointer initialized")
    except Exception as e:
        from langgraph.checkpoint.memory import MemorySaver

        logger.warning("PostgreSQL checkpointer unavailable, using MemorySaver: %s", e)
        _checkpointer = MemorySaver()

    return _checkpointer


# ---------------------------------------------------------------------------
# Rate limiting helpers
# ---------------------------------------------------------------------------
AUTH_MAX_ATTEMPTS = 5
AUTH_LOCKOUT_SECONDS = 300


def _check_rate_limit(username: str) -> bool:
    """Return True if rate-limited (should block)."""
    return cache.get(f"auth_attempts:{username}", 0) >= AUTH_MAX_ATTEMPTS


def _record_attempt(username: str, success: bool) -> None:
    key = f"auth_attempts:{username}"
    if success:
        cache.delete(key)
    else:
        cache.set(key, cache.get(key, 0) + 1, AUTH_LOCKOUT_SECONDS)


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@ensure_csrf_cookie
@require_GET
def csrf_view(request):
    """Return CSRF cookie so the SPA can read it."""
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
def me_view(request):
    """Return current user info or 401."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    user = request.user
    return JsonResponse({
        "id": str(user.id),
        "email": user.email,
        "name": user.get_full_name(),
    })


@require_POST
def login_view(request):
    """Email/password login."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = body.get("email", "").strip()
    password = body.get("password", "")

    if not email or not password:
        return JsonResponse({"error": "Email and password are required"}, status=400)

    if _check_rate_limit(email):
        return JsonResponse({"error": "Too many attempts. Try again later."}, status=429)

    user = authenticate(request, username=email, password=password)
    if user is None or not user.is_active:
        _record_attempt(email, False)
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    _record_attempt(email, True)
    login(request, user)

    return JsonResponse({
        "id": str(user.id),
        "email": user.email,
        "name": user.get_full_name(),
    })


@require_POST
def logout_view(request):
    """Logout and clear session."""
    logout(request)
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Streaming chat endpoint
# ---------------------------------------------------------------------------

MAX_MESSAGE_LENGTH = 10_000


async def chat_view(request):
    """
    POST /api/chat/

    Accepts Vercel AI SDK useChat request format, returns a
    StreamingHttpResponse in the Data Stream Protocol.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    # Parse body
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    messages = body.get("messages", [])
    data = body.get("data", {})
    project_id = data.get("projectId") or body.get("projectId")
    thread_id = data.get("threadId") or body.get("threadId") or str(uuid.uuid4())

    if not messages:
        return JsonResponse({"error": "messages is required"}, status=400)
    if not project_id:
        return JsonResponse({"error": "projectId is required"}, status=400)

    # Get the last user message
    last_msg = messages[-1]
    user_content = last_msg.get("content", "")
    if not user_content or not user_content.strip():
        return JsonResponse({"error": "Empty message"}, status=400)
    if len(user_content) > MAX_MESSAGE_LENGTH:
        return JsonResponse({"error": f"Message exceeds {MAX_MESSAGE_LENGTH} characters"}, status=400)

    # Validate project membership
    user = request.user
    try:
        membership = await ProjectMembership.objects.select_related("project").aget(
            user=user, project_id=project_id
        )
    except ProjectMembership.DoesNotExist:
        return JsonResponse({"error": "Project not found or access denied"}, status=403)

    project = membership.project
    if not project.is_active:
        return JsonResponse({"error": "Project is inactive"}, status=403)

    # Build agent
    try:
        checkpointer = await _ensure_checkpointer()
        agent = await sync_to_async(build_agent_graph)(
            project=project,
            user=user,
            checkpointer=checkpointer,
        )
    except Exception as e:
        error_ref = hashlib.sha256(f"{time.time()}{e}".encode()).hexdigest()[:8]
        logger.exception("Failed to build agent [ref=%s]", error_ref)
        return JsonResponse({"error": f"Agent initialization failed. Ref: {error_ref}"}, status=500)

    # Build LangGraph input state
    from langchain_core.messages import HumanMessage

    input_state = {
        "messages": [HumanMessage(content=user_content)],
        "project_id": str(project.id),
        "project_name": project.name,
        "user_id": str(user.id),
        "user_role": membership.role,
        "needs_correction": False,
        "retry_count": 0,
        "correction_context": {},
    }
    config = {"configurable": {"thread_id": thread_id}}

    # Return streaming response
    response = StreamingHttpResponse(
        langgraph_to_data_stream(agent, input_state, config),
        content_type="text/plain; charset=utf-8",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
