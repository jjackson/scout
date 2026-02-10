"""
LangGraph event-to-Data-Stream-Protocol translator.

Translates LangGraph astream_events(version="v2") into the Vercel AI SDK
Data Stream Protocol so that the frontend useChat hook can parse them.

Protocol reference:
  - Text token:    0:"chunk text"\n
  - Data payload:  2:[{...}]\n
  - Finish step:   e:{"finishReason":"stop","usage":{},"isContinued":false}\n
  - Finish msg:    d:{"finishReason":"stop"}\n
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncGenerator

from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)

# UUID pattern for artifact detection
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)

_ARTIFACT_INDICATORS = [
    "artifact_id",
    "artifact created",
    "created artifact",
    "chart saved",
    "visualization created",
]


def _is_artifact_result(content: str) -> bool:
    """Check if content appears to be an artifact creation result."""
    if not content:
        return False
    if not _UUID_RE.search(content):
        return False
    content_lower = content.lower()
    return any(ind in content_lower for ind in _ARTIFACT_INDICATORS)


def _extract_artifact_from_result(content: str) -> dict | None:
    """Extract artifact information from a tool result."""
    # Try JSON parsing first
    try:
        if "{" in content:
            json_match = re.search(r"\{[^{}]*\}", content)
            if json_match:
                data = json.loads(json_match.group())
                if "artifact_id" in data:
                    return data
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fall back to UUID regex
    match = _UUID_RE.search(content)
    if match:
        return {"artifact_id": match.group(0)}
    return None


def _encode_text(text: str) -> str:
    """Encode a text token for Data Stream Protocol: 0:"text"\n"""
    return f"0:{json.dumps(text)}\n"


def _encode_data(payload: list[dict]) -> str:
    """Encode a data payload for Data Stream Protocol: 2:[...]\n"""
    return f"2:{json.dumps(payload)}\n"


def _encode_finish_step() -> str:
    return 'e:{"finishReason":"stop","usage":{},"isContinued":false}\n'


def _encode_finish_message() -> str:
    return 'd:{"finishReason":"stop"}\n'


def _tool_content_to_str(output: Any) -> str:
    """Convert tool output to a string."""
    if isinstance(output, ToolMessage):
        return output.content if isinstance(output.content, str) else str(output.content)
    if isinstance(output, str):
        return output
    return str(output)


async def langgraph_to_data_stream(
    agent: Any,
    input_state: dict,
    config: dict,
) -> AsyncGenerator[str, None]:
    """
    Stream LangGraph agent events as Data Stream Protocol chunks.

    Yields strings in the Vercel AI SDK Data Stream Protocol format.
    """
    tool_calls_processed: set[str] = set()

    try:
        async for event in agent.astream_events(input_state, config=config, version="v2"):
            event_type = event.get("event")

            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    if isinstance(chunk.content, str):
                        yield _encode_text(chunk.content)
                    elif isinstance(chunk.content, list):
                        for block in chunk.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    yield _encode_text(text)
                            elif hasattr(block, "text") and block.text:
                                yield _encode_text(block.text)

            elif event_type == "on_tool_end":
                run_id = event.get("run_id")
                if run_id and run_id in tool_calls_processed:
                    continue
                if run_id:
                    tool_calls_processed.add(run_id)

                tool_output = event.get("data", {}).get("output")
                if tool_output:
                    content = _tool_content_to_str(tool_output)
                    if _is_artifact_result(content):
                        artifact_info = _extract_artifact_from_result(content)
                        if artifact_info:
                            yield _encode_data([{
                                "type": "artifact",
                                "artifact_id": artifact_info["artifact_id"],
                                **{k: v for k, v in artifact_info.items() if k != "artifact_id"},
                            }])
                    else:
                        tool_name = event.get("name", "unknown")
                        yield _encode_data([{
                            "type": "tool_result",
                            "name": tool_name,
                            "content": content[:2000],
                        }])

    except Exception:
        logger.exception("Error during agent streaming")
        yield _encode_text("\n\nAn error occurred while processing your request.")

    # Always emit finish markers
    yield _encode_finish_step()
    yield _encode_finish_message()
