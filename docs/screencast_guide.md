# Six-minute screencast guide

This is a recording guide, not a completed video. Record an actual model-backed run. Use your own voice and explain the code you submit.

## Before recording

1. Install the project and run the tests using the README.
2. Configure a valid provider key locally. Test one real request before starting the recording. Stay on the free plan if using Groq.
3. Open the README, `src/study_planner/server.py`, `service.py`, and a terminal. Close key files and account pages containing credentials.
4. Increase terminal text size. Keep the real tool call and result visible long enough to read.
5. Start the paused demonstration command below. It uses a separate task database and unique request IDs for each new demonstration, so old demonstrations cannot cause retry conflicts.

```powershell
.\.venv\Scripts\python.exe -m study_planner.client --demo --pause --database data/recording.sqlite3 --report evidence/live-agent.json
```

The prompts are supplied automatically, but the live model selects the tools. Press Enter between scenarios. On a free API tier, use the narration pauses to respect quota; if you receive 429, wait for the provider's limit window rather than repeatedly retrying. An incomplete or failed run needs another recording.

## 0:00-0:40 - Introduce the project

Show the README's three-tool table.

Suggested narration: "My project is Campus Study Planner. It connects an OpenAI Agents SDK agent to a separate FastMCP server. There are exactly three tools: find_study_resource is the Data tool, create_study_task is the Action tool, and plan_study_session is the Orchestration tool. The catalog is fictional sample data; saving a task produces a real SQLite record."

## 0:40-1:20 - Explain MCP and tool boundaries

Show the architecture and three registrations in `server.py`.

Suggested narration: "The Python application is the Host. MCPServerStdio is the Client inside it. The FastMCP process is the Server. The client discovers the tool schemas, the model selects a tool, and the SDK sends the call over stdio. The server returns structured data for the model's answer. Typed inputs and Pydantic output models define the interface. I kept lookup separate from saving so an information request has no persistent effect."

Point to `plan_study_session` in `service.py`: it calls the same lookup and creation operations in sequence. Explain that this is one external orchestration call and two internal operations.

## 1:20-2:05 - Demonstrate the Data tool

Press Enter for the first scenario:

```text
Find a study resource about Python async. Do not save a task.
```

Show the selected `find_study_resource` name, typed arguments, returned resource, and final answer. Note `is_sample: true`. Explain that the lookup reads the catalog and never opens task storage.

## 2:05-2:50 - Demonstrate the Action tool

Press Enter for the second scenario, which asks to save an already supplied title for 25 minutes.

Show `create_study_task`, the returned task ID, `minutes`, and `status`. Explain that the title can be the student's own notes, so this tool does not perform a hidden catalog search.

## 2:50-3:40 - Demonstrate the Orchestration tool

Press Enter for the third scenario, which asks to find an MCP resource and save a 40-minute session.

Show `plan_study_session` and the server's real step-one lookup / step-two save logs. Explain how the returned resource title matches the saved task's title. Do not call the Action tool again: orchestration already saved the task.

## 3:40-4:25 - Demonstrate a predictable failure

Press Enter for the unavailable-topic lookup.

Show the explicit MCP error and the supported-topic information. Explain: "An unavailable resource is a failed lookup, and the agent should report that result accurately. It must not claim a task was saved. The server validates inputs, and the tests also verify that a failed orchestration lookup writes nothing."

If the model responds without calling the lookup tool, point out the failed demonstration and rerun with a clearer request; do not claim it showed a round trip.

## 4:25-5:10 - Retry and persistent state

Press Enter for the final scenario. It repeats the same orchestration payload and request ID.

Compare the returned task ID and creation time with the earlier orchestration result. Explain that the retry returns the original record. Show tasks using:

```powershell
.\.venv\Scripts\python.exe scripts/show_tasks.py --database data/recording.sqlite3
```

If the database was new at recording start, there should be two tasks: one direct Action result and one Orchestration result. A prior demonstration can leave additional rows; compare the current demonstration's request IDs rather than making an incorrect total-count claim.

## 5:10-6:10 - Challenges, tests, reflection, and links

Show the actual test summary and the live JSON evidence file.

Suggested narration: "The main challenge was drawing the boundary around orchestration without duplicating logic. Shared operations and explicit sequencing keep the behavior consistent. Another challenge was safe retries: the request ID and an atomic SQLite transaction prevent duplicate tasks. Tests cover invalid input, storage failure, retry conflicts, read-only lookup, and persistence after a server restart. Three tools fit this small use case. Future work could add a real catalog and task completion as separate capabilities."

Finish by showing the real repository URL and telling the viewer where the recording is hosted. Aim for 5-7 minutes; allow for actual API latency and adjust explanation time to stay inside that range.

## Before submitting

- Watch the complete recording and confirm the voice and terminal text are understandable.
- Confirm each of the three tools was selected and executed through the live SDK/MCP path.
- Confirm errors are reported honestly and the retry task ID matches.
- Confirm no key appears in the recording, repository, ZIP, screenshots, or logs.
- Publish the code and video where your instructor can access them.
- Put the actual repository and video URLs into `docs/submission_notes.md`.
