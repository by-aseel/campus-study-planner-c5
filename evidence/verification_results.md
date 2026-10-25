# Verified local results

Checked October 25, 2026 using Python 3.12 on Windows.

- **43 tests passed in 40.83 seconds.** This includes the real MCP stdio subprocess integration test and the OpenAI Agents SDK bridge test.
- The standalone transport verification passed **7 checks and 11 real MCP calls** with exactly **3 tools**. See `mcp-verification.json` for discovered schemas, observed calls/errors, package versions, and persisted records.
- Successful checks cover each capability, clear errors, lookup without writes, identical/conflicting retries, orchestration using the selected resource, and persistence after a new server process starts.
- A Windows-only verification cleanup issue was corrected by explicitly closing the final SQLite connection before deleting its temporary directory. The production service already closes its connections.
- The SDK bridge test uses an explicitly scripted model to verify that the SDK receives the actual three tool definitions, invokes each real MCP tool, returns tool results to the model, and carries an error result correctly. It makes four real MCP calls. It does not claim hosted inference or learned tool selection.

## Live provider results

The Groq free-tier model `openai/gpt-oss-20b` completed the real OpenAI Agents SDK / MCP round trip for all five scenarios. `live-agent.json` records all expected tool selections, correct success/error outcomes, and identical task identity on retry; every check passed.

A second run was captured through the local recording dashboard. `recorded-live-agent.json` records five passing scenarios and exactly two saved tasks. `recorded-action.json` records a supplementary live Action capture used to make that scene clearly readable in the edited screencast.

The visual screencast draft is 5 minutes 33 seconds at 1280 by 720 pixels. It is edited from two genuine browser captures, with no simulated tool results. Narration and final hosting are being completed separately. Source recordings and API credentials are excluded from the submission package.
