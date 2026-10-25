"""FastMCP server exposing exactly one Data, one Action, and one Orchestration tool.

Run with ``python -m study_planner.server``. stdout belongs exclusively to the MCP
transport; any future diagnostics should use logging (stderr), never print().
"""

import logging
import sys
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from . import service
from .models import StudyPlan, StudyResource, StudyTask


# Keep the demonstration trace separate from stdout's JSON-RPC messages.
# Avoid logging argument values, user prompts, credentials, or file paths.
if not service.logger.handlers:
    trace_handler = logging.StreamHandler(sys.stderr)
    trace_handler.setFormatter(logging.Formatter("[server] %(message)s"))
    service.logger.addHandler(trace_handler)
service.logger.setLevel(logging.INFO)
service.logger.propagate = False


mcp = FastMCP(
    "Campus Study Planner",
    instructions=(
        "A demonstration toolkit backed by an explicitly fictional campus catalog. "
        "find_study_resource only reads. create_study_task saves one local study intention. "
        "plan_study_session coordinates lookup and save. Saving does not reserve a room, "
        "book a calendar event, or send a notification. Use write tools only when the user asks to save or plan. "
        "Keep request_id unchanged for retries; use a new request_id for a new task."
    ),
    mask_error_details=True,
)

Topic = Annotated[str, Field(min_length=1, max_length=100, description="Topic or alias: Python async (python, asyncio), REST APIs (rest, http), or MCP tools (mcp). Case and whitespace are ignored.")]
ResourceTitle = Annotated[str, Field(min_length=1, max_length=160, description="Title of the resource to study; use the exact lookup result title when available.")]
Minutes = Annotated[int, Field(strict=True, ge=5, le=180, description="Study duration as a whole number of minutes, from 5 through 180.")]
RequestId = Annotated[str, Field(min_length=1, max_length=100, description="Caller-chosen unique key for this intended task. Reuse the same key and payload for retries; use a fresh key for a new task.")]


@mcp.tool(annotations={"title": "Find a study resource", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
def find_study_resource(topic: Topic) -> StudyResource:
    """DATA: Retrieve one learning resource from the fictional, bundled campus catalog.

    Use for information-only requests. Returns the resource title, sample campus
    location, summary and focus points. Matching is exact against a canonical
    topic or its documented aliases, ignoring case/whitespace. Does not touch
    task storage. Unknown topics produce an error listing available topics.
    """
    try:
        return service.find_study_resource(topic)
    except service.StudyPlannerError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations={"title": "Create a study task", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
def create_study_task(resource_title: ResourceTitle, minutes: Minutes, request_id: RequestId) -> StudyTask:
    """ACTION: Save one study intention to local, durable SQLite task storage.

    Use when the user asks to save a task for a known resource title. Returns
    its persisted identifier, title, duration, status, request key and original
    UTC creation time. This does not schedule a calendar event or reserve a
    resource. Identical request_id/payload retries return the original task;
    reusing a key with a different title or duration is an explicit error.
    """
    try:
        return service.create_study_task(resource_title, minutes, request_id)
    except service.StudyPlannerError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations={"title": "Plan a study session", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
def plan_study_session(topic: Topic, minutes: Minutes, request_id: RequestId) -> StudyPlan:
    """ORCHESTRATION: Look up a topic, then save a task for the selected resource.

    Use for a higher-level request to find a suitable resource and save a study
    intention. Calls the same data operation followed by the same action
    operation; returns both typed results. Invalid input or unknown topic causes
    no task write. Identical retries reuse the saved task; conflicting request
    keys fail clearly. Never call create_study_task again after this succeeds.
    """
    try:
        return service.plan_study_session(topic, minutes, request_id)
    except service.StudyPlannerError as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
