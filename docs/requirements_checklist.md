# Assignment requirements checklist

Reviewed October 25, 2026 against the supplied C5 assignment. This distinguishes implemented and tested work from the remaining live demonstration and publication requirements.

| Assignment requirement | Evidence | Status |
|---|---|---|
| Read the assigned Hugging Face article | Written summary cites the assigned page and its linked full article. | Complete |
| Explore an existing MCP implementation | Summary critiques the official Fetch source and records its inspection date. | Complete; mutable branch source is disclosed. |
| Write 300-400 words | Summary is 368 words, excluding heading and source details. | Complete |
| Explain Host, Client, and Server | Summary and README explain the relationships and actual call flow. | Complete |
| Critique tool design | Source-level Fetch critique covers single purpose, clear interfaces and predictable behavior. | Complete |
| Choose a theme | Campus study planner with explicitly fictional sample catalog. | Complete |
| Exactly three MCP tools | Actual discovery in evidence/mcp-verification.json. | Verified |
| Data tool | find_study_resource reads catalog without accessing task storage. | Verified |
| Action tool | create_study_task persists real SQLite records. | Verified |
| Orchestration tool | plan_study_session uses shared lookup followed by shared creation. | Verified |
| Clear descriptions and typed inputs/outputs | Tool docstrings, annotated parameters, Pydantic models, discovered schemas. | Verified |
| Single-purpose boundaries | Separate read, write, and coordinated workflow; no extra exposed helpers. | Complete |
| Clear predictable failures | Unknown topic, invalid input, conflicting retry key, unavailable storage. | Verified |
| FastMCP server | src/study_planner/server.py over real stdio. | Verified |
| Resources for lookups exposed as resources | No separate resources are exposed; Data lookup is a callable tool. | Not applicable; no additional resource required. |
| OpenAI Agents SDK host/client | client.py uses Agent, Runner, MCPServerStdio and OpenAIChatCompletionsModel. | Verified through the real Groq-backed host, plus a scripted SDK regression test. |
| Live natural-language tool routing | Requires actual provider inference and live-agent.json. | Verified: all five real Groq-backed scenarios passed; see evidence/live-agent.json. |
| Configuration and setup README | README.md, .env.example, secure setup prompt, pinned dependencies and environment lock. | Complete |
| Tests including failures | 43 passing tests; 7 standalone checks and 11 real MCP calls including restart. | Verified; see evidence/. |
| Written summary deliverable | docs/written_summary.md in Markdown. | Complete |
| Source code deliverable | src/, tests/, scripts/, configuration and README. | Complete |
| 1-2 paragraph reflection | docs/reflection.md, two paragraphs. | Complete |
| 5-7 minute screencast | 5 minute 33 second visual screencast captured from two genuine live runs; narration is being completed. | Pending |
| Introduce all three tool categories in video | Covered by recording guide. | Pending recording |
| Show full live agent/client/server round trip | Host logs actual traffic; paused demo provides natural-language scenarios. | Live run verified; visual recording captured; final narration pending |
| Discuss challenges and solutions | Guide covers shared operations, side effects, failures and idempotency. | Pending recording |
| Repository URL | Add real URL to docs/submission_notes.md. | Pending publication |
| Video URL | Add real URL to docs/submission_notes.md. | Pending recording and hosting |

## Final steps

1. Keep the configured Groq key private. The approved assignment key uses a 30-day expiration.
2. Review the passing live reports and final narrated screencast.
3. Complete the authorized voice narration and watch the final video.
4. Publish the repository and video, then enter their actual URLs in the submission notes.

Local integration tests and a scripted model do not replace the required live model demonstration. No completed video or invented publication links are claimed.
