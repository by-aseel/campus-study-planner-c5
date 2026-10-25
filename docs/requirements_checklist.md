# Assignment requirements checklist

Reviewed October 25, 2026 against the supplied C5 assignment. The status below is grounded in source, test reports, actual live model calls, and the final narrated video.

| Assignment requirement | Evidence | Status |
|---|---|---|
| Read the assigned Hugging Face article | Written summary cites the assigned page and its linked full article. | Complete |
| Explore an existing MCP implementation | Summary critiques the official Fetch source and records its inspection date. | Complete; mutable branch source is disclosed. |
| Write 300-400 words | Summary is 371 words, excluding heading and source details. | Complete |
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
| 5-7 minute screencast | 5 minutes 31 seconds; final narrated MP4. | Complete |
| Introduce all three tool categories in video | Opening and each narrated tool demonstration. | Complete |
| Show full live agent/client/server round trip | Real model-selected tool, arguments, returned result, observed call log, and final agent answer. | Complete |
| Discuss challenges and solutions | Narration explains read/write boundaries, shared operations, predictable errors, and atomic retry handling. | Complete |
| Repository URL | https://github.com/by-aseel/campus-study-planner-c5 (public). | Published |
| Video URL | https://github.com/by-aseel/campus-study-planner-c5/raw/refs/heads/main/media/campus-study-planner-demonstration.mp4 | Published |

## Submission review

Keep API keys private. Submit the reading summary, reflection, source repository link, and actual hosted video link listed in `submission_notes.md`. The narration is synthesized with the speaker's explicit authorization.

## Submission review

Keep API keys private. Submit the reading summary, reflection, source repository link, and actual hosted video link listed in `submission_notes.md`. The narration is synthesized with the speaker's explicit authorization.

## Submission review

Keep API keys private. Submit the reading summary, reflection, source repository link, and actual hosted video link listed in `submission_notes.md`. The narration is synthesized with the speaker's explicit authorization.
