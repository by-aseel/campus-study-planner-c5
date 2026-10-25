"""Print saved tasks as JSON using a read-only SQLite connection."""

from __future__ import annotations

from contextlib import closing
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, help="Read a specific demonstration database")
    args = parser.parse_args()
    # Existing process environment takes priority, matching the agent client.
    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")
    configured = os.environ.get("STUDY_PLANNER_DB")
    if configured is not None and not configured.strip():
        print("STUDY_PLANNER_DB must be a nonempty file path.", file=sys.stderr)
        return 1
    database = (args.database or (Path(configured).expanduser() if configured is not None else PROJECT_ROOT / "data" / "tasks.sqlite3")).resolve()
    if not database.exists():
        print("[]")
        return 0
    try:
        # as_uri quotes path characters. mode=ro forbids both creating a missing
        # database and making changes to an existing one.
        with closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT task_id, resource_title, minutes, request_id, status, created_at "
                "FROM tasks ORDER BY created_at, task_id"
            ).fetchall()
        print(json.dumps([dict(row) for row in rows], indent=2, ensure_ascii=True))
        return 0
    except (OSError, sqlite3.Error):
        print("Could not read task storage. Check STUDY_PLANNER_DB and whether it contains the tasks table.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
