# Verified local results

Checked October 25, 2026 using Python 3.12 on Windows.

- **43 tests passed in 40.83 seconds.** This includes the real MCP stdio subprocess integration test and the OpenAI Agents SDK bridge test.
- The standalone transport verification passed **7 checks and 11 real MCP calls** with exactly **3 tools**. See `mcp-verification.json` for discovered schemas, observed calls/errors, package versions, and persisted records.
- Successful checks cover each capability, clear errors, lookup without writes, identical/conflicting retries, orchestration using the selected resource, and persistence after a new server process starts.
- A Windows-only verification cleanup issue was corrected by explicitly closing the final SQLite connection before deleting its temporary directory. The production service already closes its connections.
- The SDK bridge test uses an explicitly scripted model to verify that the SDK receives the actual three tool definitions, invokes each real MCP tool, returns tool results to the model, and carries an error result correctly. It makes four real MCP calls. It does not claim hosted inference or learned tool selection.

## Live provider results

The Groq model `openai/gpt-oss-20b` completed all five real OpenAI Agents SDK / MCP scenarios. The original `live-agent.json` and historical `recorded-*.json` reports remain as earlier verification runs.

The current video uses the new interactive recording script, `scripts/record_live_roundtrips.py`. The user requests are visibly entered and submitted; the model selects each tool through the real SDK host. `uninterrupted-live-agent.json` records all five passing outcomes from this one MCP session and SQLite database: Data, Action, Orchestration, unavailable-topic failure, and identical retry. The retry preserves the original task and timestamp; exactly two tasks remain.

The final narrated screencast is 5 minutes 55 seconds at 1280 by 720 pixels. Each complete live query-to-final-answer sequence follows the original capture timestamps, without an internal cut or speed change; the output is sampled at 25 frames per second. Edits occur only between complete chapters; static introduction, architecture and summary cards accompany the explanations. `screencast-verification.json` records source frame counts, maximum capture intervals, event coverage, chapter timing, and successful full-file decoding. The synthesized narration uses the speaker's approved voice with explicit authorization. Original voice references, temporary generation files, task databases and credentials are excluded.
