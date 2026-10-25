"""Domain operations, independently testable without an LLM or an MCP transport.

The data operation never opens the task database. Database connections are local
to each action call, so FastMCP may safely dispatch synchronous calls to workers.
"""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from pydantic import ValidationError

from .models import StudyPlan, StudyResource, StudyTask


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog.json"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "tasks.sqlite3"
logger = logging.getLogger(__name__)


class StudyPlannerError(ValueError):
    """A predictable, actionable domain error that is safe to show to the caller."""


def _text(value: str, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise StudyPlannerError(f"{field} must be a nonempty string of at most {limit} characters.")
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > limit:
        raise StudyPlannerError(f"{field} must be a nonempty string of at most {limit} characters.")
    return normalized


def _minutes(value: int) -> int:
    # bool is an int subclass in Python but is not a meaningful study duration.
    if type(value) is not int or not 5 <= value <= 180:
        raise StudyPlannerError("minutes must be a whole number between 5 and 180 inclusive.")
    return value


def _catalog() -> list[dict]:
    try:
        contents = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        entries = contents["resources"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("Missing resource list")
        return entries
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise StudyPlannerError(
            "The bundled sample catalog is unavailable or invalid. Restore data/catalog.json and retry."
        ) from exc


def find_study_resource(topic: str) -> StudyResource:
    """Return one exact topic/alias match without accessing or modifying task storage."""
    normalized = _text(topic, "topic", 100).casefold()
    logger.info("DATA find_study_resource: reading bundled sample catalog")
    entries = _catalog()
    try:
        for entry in entries:
            names = [entry["topic"], *entry.get("aliases", [])]
            if normalized in {" ".join(name.split()).casefold() for name in names}:
                resource = StudyResource.model_validate({key: value for key, value in entry.items() if key != "aliases"})
                logger.info("DATA find_study_resource: returning one resource")
                return resource
        available = ", ".join(entry["topic"] for entry in entries)
    except (KeyError, TypeError, AttributeError, ValidationError) as exc:
        raise StudyPlannerError("The bundled sample catalog is invalid. Restore data/catalog.json and retry.") from exc
    raise StudyPlannerError(f"Unknown topic. Available topics: {available}. Use a topic name or documented alias.")


def _database_path() -> Path:
    configured = os.environ.get("STUDY_PLANNER_DB")
    if configured is None:
        return DEFAULT_DB_PATH
    if not configured.strip():
        raise StudyPlannerError("STUDY_PLANNER_DB must be a nonempty file path, or unset to use the default.")
    return Path(configured).expanduser()


def create_study_task(resource_title: str, minutes: int, request_id: str) -> StudyTask:
    """Persist one study task; an identical retry returns its original saved record.

    request_id is unique across all tasks, including those made by orchestration.
    Titles may name a catalog resource or another resource chosen by the caller.
    """
    title = _text(resource_title, "resource_title", 160)
    duration = _minutes(minutes)
    key = _text(request_id, "request_id", 100)
    database_path = _database_path()
    logger.info("ACTION create_study_task: checking durable task storage")
    try:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database_path, timeout=10)) as connection:
            connection.row_factory = sqlite3.Row
            # Serialize the check-and-insert, including concurrent identical retries.
            # The connection context commits on success and rolls back on errors.
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        resource_title TEXT NOT NULL,
                        minutes INTEGER NOT NULL CHECK (minutes BETWEEN 5 AND 180),
                        request_id TEXT NOT NULL UNIQUE,
                        status TEXT NOT NULL CHECK (status = 'planned'),
                        created_at TEXT NOT NULL
                    )"""
                )
                existing = connection.execute(
                    "SELECT task_id, resource_title, minutes, request_id, status, created_at "
                    "FROM tasks WHERE request_id = ?", (key,),
                ).fetchone()
                if existing is not None:
                    if existing["resource_title"] != title or existing["minutes"] != duration:
                        raise StudyPlannerError(
                            "request_id already exists with a different resource_title or minutes. "
                            "Reuse the original payload to retry, or choose a new request_id for a new task."
                        )
                    logger.info("ACTION create_study_task: returning original task for identical retry")
                    return StudyTask.model_validate(dict(existing))
                task = StudyTask(
                    task_id=str(uuid4()),
                    resource_title=title,
                    minutes=duration,
                    request_id=key,
                    created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                )
                connection.execute(
                    "INSERT INTO tasks (task_id, resource_title, minutes, request_id, status, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (task.task_id, task.resource_title, task.minutes, task.request_id, task.status, task.created_at),
                )
            logger.info("ACTION create_study_task: committed one new task")
            return task
    except (OSError, sqlite3.Error, ValidationError) as exc:
        raise StudyPlannerError(
            "Task storage is unavailable or invalid. Check STUDY_PLANNER_DB and its folder permissions, then retry."
        ) from exc


def plan_study_session(topic: str, minutes: int, request_id: str) -> StudyPlan:
    """Look up a resource, then save one task using the same public domain operations."""
    # Check the entire request before any potential write. Each underlying
    # operation still validates independently for direct calls to its own tool.
    _text(topic, "topic", 100)
    _minutes(minutes)
    _text(request_id, "request_id", 100)
    logger.info("ORCHESTRATION plan_study_session: step 1 -> find_study_resource")
    resource = find_study_resource(topic)
    logger.info("ORCHESTRATION plan_study_session: step 2 -> create_study_task")
    task = create_study_task(resource.title, minutes, request_id)
    logger.info("ORCHESTRATION plan_study_session: returning resource and saved task")
    return StudyPlan(resource=resource, task=task)
