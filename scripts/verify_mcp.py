"""Exercise the actual stdio MCP connection without an LLM or API key.

Run from the project root: python scripts/verify_mcp.py
The JSON evidence contains observed responses, not simulated model output.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import closing
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "find_study_resource": {"topic": "string"},
    "create_study_task": {"resource_title": "string", "minutes": "integer", "request_id": "string"},
    "plan_study_session": {"topic": "string", "minutes": "integer", "request_id": "string"},
}


def make_client(database: Path) -> Client:
    """Launch a fresh process; forward configuration but no API credentials."""
    return Client(
        StdioTransport(
            command=sys.executable,
            args=["-m", "study_planner.server"],
            cwd=str(PROJECT_ROOT),
            env={"STUDY_PLANNER_DB": str(database), "PYTHONUNBUFFERED": "1"},
            keep_alive=False,
        ),
        timeout=30,
    )


def require(condition: Any, message: str) -> None:
    """Do not disable verification when Python runs with optimization enabled."""
    if not condition:
        raise AssertionError(message)


def schema_field(tool: dict[str, Any], camel: str, snake: str) -> Any:
    return tool.get(camel, tool.get(snake))


def validate_catalog(tools: list[Any]) -> list[dict[str, Any]]:
    names = [tool.name for tool in tools]
    require(len(names) == 3 and set(names) == set(EXPECTED_TOOLS),
            f"Expected exactly three toolkit tools, received {names!r}")
    catalog = [tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in tools]
    for tool in catalog:
        require(bool(tool.get("description", "").strip()), f"Missing description: {tool['name']}")
        inputs = schema_field(tool, "inputSchema", "input_schema")
        outputs = schema_field(tool, "outputSchema", "output_schema")
        require(isinstance(inputs, dict), f"Missing input schema: {tool['name']}")
        require(isinstance(outputs, dict) and bool(outputs), f"Missing output schema: {tool['name']}")
        properties = inputs.get("properties", {})
        for argument, expected_type in EXPECTED_TOOLS[tool["name"]].items():
            require(properties.get(argument, {}).get("type") == expected_type,
                    f"Expected {argument} to have JSON type {expected_type}: {tool['name']}")
        require(set(EXPECTED_TOOLS[tool["name"]]) <= set(inputs.get("required", [])),
                f"Missing required arguments: {tool['name']}")
    return catalog


async def recorded_call(
    client: Client,
    report: dict[str, Any],
    name: str,
    arguments: dict[str, Any],
    *,
    expect_error: bool = False,
    phase: str = "initial process",
) -> dict[str, Any]:
    result = await client.call_tool(name, arguments, raise_on_error=False)
    messages = [block.text for block in result.content if hasattr(block, "text")]
    entry = {
        "phase": phase,
        "tool": name,
        "arguments": arguments,
        "is_error": result.is_error,
        "structured_content": result.structured_content,
        "text_content": messages,
    }
    report["calls"].append(entry)
    require(result.is_error is expect_error,
            f"{name}: expected is_error={expect_error}, received {entry!r}")
    if expect_error:
        require(any(text.strip() for text in messages), f"{name}: error must explain the failure")
        return {}
    require(isinstance(result.structured_content, dict), f"{name}: missing typed structured result")
    return result.structured_content


async def verify() -> dict[str, Any]:
    """Run real tool discovery/calls, including process restart and persistence."""
    report: dict[str, Any] = {
        "status": "running",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Real MCP stdio subprocess integration; no model inference or API calls.",
        "versions": {name: version(name) for name in ("fastmcp", "mcp", "openai-agents")},
        "calls": [],
        "checks": [],
    }
    with tempfile.TemporaryDirectory(prefix="study-planner-verification-") as directory:
        database = Path(directory) / "store" / "tasks.sqlite3"
        action_args = {"resource_title": "My personal review notes", "minutes": 25, "request_id": "verify-action-001"}
        plan_args = {"topic": "MCP tools", "minutes": 30, "request_id": "verify-plan-001"}
        async with make_client(database) as client:
            report["tools"] = validate_catalog(await client.list_tools())
            report["checks"].append("Exactly three described tools advertise typed input and output schemas.")

            resource = await recorded_call(client, report, "find_study_resource", {"topic": "MCP tools"})
            require(resource["title"] == "MCP Tool Design Guide", "Lookup returned an unexpected fixture")
            require(resource["is_sample"] is True, "Fixture must identify itself as sample data")
            require(not database.exists(), "Data tool must not create a task database")
            report["checks"].append("Data lookup succeeds without a persistence side effect.")

            await recorded_call(client, report, "find_study_resource", {"topic": "unavailable topic"}, expect_error=True)
            await recorded_call(client, report, "create_study_task", {**action_args, "minutes": 4}, expect_error=True)
            await recorded_call(client, report, "plan_study_session", {**plan_args, "topic": "unavailable topic"}, expect_error=True)
            require(not database.exists(), "Failed calls must not create a partial task database")
            report["checks"].append("Each tool exposes a clear is_error failure; failed lookup/orchestration writes nothing.")

            task = await recorded_call(client, report, "create_study_task", action_args)
            require(task["resource_title"] == action_args["resource_title"], "Action saved a different title")
            require(task["minutes"] == 25 and task["status"] == "planned", "Action returned an invalid task")
            require(database.is_file(), "Action must persist its result")
            duplicate = await recorded_call(client, report, "create_study_task", action_args)
            require(duplicate == task, "An identical request_id retry must return the same task")
            await recorded_call(client, report, "create_study_task", {**action_args, "minutes": 45}, expect_error=True)
            report["checks"].append("Action persists a task, deduplicates identical retries, and rejects conflicting retries.")

            plan = await recorded_call(client, report, "plan_study_session", plan_args)
            require(plan["resource"]["title"] == resource["title"], "Orchestration selected an unexpected resource")
            require(plan["task"]["resource_title"] == resource["title"], "Orchestration did not save the looked-up resource")
            require(plan["task"]["minutes"] == 30, "Orchestration saved an unexpected duration")
            report["checks"].append("Orchestration combines the lookup result with a persisted task.")

            before = database.read_bytes()
            await recorded_call(client, report, "find_study_resource", {"topic": "Python async"})
            require(database.read_bytes() == before, "Data lookup modified existing task storage")
            report["checks"].append("Data lookup also leaves an existing database unchanged.")

        # The previous context ended its subprocess. This connection starts a new server.
        async with make_client(database) as restarted:
            replay = await recorded_call(restarted, report, "create_study_task", action_args, phase="restarted process")
            require(replay == task, "Task identity did not survive a server process restart")
            replay_plan = await recorded_call(restarted, report, "plan_study_session", plan_args, phase="restarted process")
            require(replay_plan == plan, "Plan identity did not survive a server process restart")
        with closing(sqlite3.connect(database)) as connection:
            request_ids = [row[0] for row in connection.execute("SELECT request_id FROM tasks ORDER BY request_id")]
        require(request_ids == ["verify-action-001", "verify-plan-001"],
                f"Expected exactly two durable tasks, received {request_ids!r}")
        report["checks"].append("Tasks survive a fresh server process; retries leave exactly two database rows.")
        report["persisted_tasks"] = [task, plan["task"]]
        report["final_database_row_count"] = len(request_ids)
    report["status"] = "passed"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "evidence" / "mcp-verification.json")
    arguments = parser.parse_args()
    report = asyncio.run(verify())
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: {len(report['checks'])} checks; {len(report['calls'])} real MCP calls; exactly three tools.")
    print("No API key or model inference was used.")
    print(f"Evidence: {arguments.report.resolve()}")


if __name__ == "__main__":
    main()
