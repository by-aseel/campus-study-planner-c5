"""Test the SDK-to-MCP bridge with a scripted model, never claiming real inference."""

import asyncio
import json

from agents import Model, ModelResponse, Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

from study_planner.client import EXPECTED_TOOLS, make_server, run_turn


class ScriptedModel(Model):
    """A deliberate test double: tool choice is supplied by the test, not learned."""

    def __init__(self, name, arguments):
        self.tool_name = name
        self.arguments = arguments
        self.responses = 0

    async def get_response(self, system_instructions, input, model_settings, tools,
                           output_schema, handoffs, tracing, **kwargs):
        assert {tool.name for tool in tools} == EXPECTED_TOOLS
        self.responses += 1
        if self.responses == 1:
            output = ResponseFunctionToolCall(
                id="test-function-call", call_id="test-call", type="function_call",
                name=self.tool_name, arguments=json.dumps(self.arguments), status="completed",
            )
        else:
            assert self.responses == 2
            returned = [item for item in input if isinstance(item, dict)
                        and item.get("type") == "function_call_output"]
            assert len(returned) == 1, "The SDK must return the real MCP result to the model"
            output = ResponseOutputMessage(
                id="test-final", type="message", role="assistant", status="completed",
                content=[ResponseOutputText(type="output_text", text="Scripted bridge check completed.", annotations=[])],
            )
        return ModelResponse(output=[output], usage=Usage(), response_id="scripted-test")

    async def stream_response(self, *args, **kwargs):
        raise NotImplementedError("Streaming is outside this test's scope")
        yield  # Required because the interface expects an async generator.


def test_sdk_routes_each_scripted_call_through_real_mcp_and_returns_results(tmp_path):
    async def check():
        cases = [
            ("find_study_resource", {"topic": "Python async"}),
            ("create_study_task", {"resource_title": "Bridge test notes", "minutes": 25, "request_id": "bridge-action"}),
            ("plan_study_session", {"topic": "MCP tools", "minutes": 30, "request_id": "bridge-plan"}),
            ("find_study_resource", {"topic": "unavailable topic"}),
        ]
        async with make_server(database=tmp_path / "bridge.sqlite3", verbose=False) as server:
            for index, (name, arguments) in enumerate(cases):
                model = ScriptedModel(name, arguments)
                result = await run_turn(server, model, "Exercise the configured test case.")
                assert result.final_output == "Scripted bridge check completed."
                assert model.responses == 2
                call = server.calls[-1]
                assert call["tool"] == name
                assert call["arguments"] == arguments
                response = call["result"]
                is_error = response.get("isError", response.get("is_error", False))
                assert bool(is_error) == (index == 3)
            assert len(server.calls) == 4
    asyncio.run(check())
