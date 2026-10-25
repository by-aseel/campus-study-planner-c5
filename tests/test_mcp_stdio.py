"""This test starts the actual server twice, rather than calling tool wrappers."""

import asyncio
import importlib.util
from pathlib import Path


def test_stdio_tools_and_persistence():
    path = Path(__file__).resolve().parents[1] / "scripts" / "verify_mcp.py"
    spec = importlib.util.spec_from_file_location("verify_mcp", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = asyncio.run(module.verify())
    assert report["status"] == "passed"
    assert report["final_database_row_count"] == 2
    assert len(report["tools"]) == 3
