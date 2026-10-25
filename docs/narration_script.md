# Screencast narration

Five complete live browser query-to-answer captures at original speed; cuts only between chapters. Static introduction, architecture and summary cards. Previously approved synthesized narration from the speaker's explicitly authorized voice sample; no voice reference included.

## 0:00

This is Campus Study Planner, a three-tool Model Context Protocol project for the Agent Tools assignment. It connects an OpenAI Agents SDK host to a separate FastMCP server, using Groq for real model inference. The catalog is explicitly fictional sample data. The tasks saved during the demonstration are real SQLite records. There are exactly three exposed tools: one Data tool, one Action tool, and one Orchestration tool.

## 0:35

The host is the Python application that runs the agent. MCPServerStdio is the client inside that host. It connects to the FastMCP server over standard input and output, discovers the typed tool schemas, and routes the model's selected calls. A server result returns through the client to the model, which then produces a final answer. The host does not route prompts with keyword matching. The same three tools can be used by another compatible MCP host.

## 1:10

The first request asks for a resource about Python asynchronous programming and explicitly says not to save a task. The live model selects find study resource, our Data tool. On the left are the actual arguments and the observed round trip. On the right are fields from the real MCP result and the agent's final answer. The sample flag makes the data's status explicit. This operation reads the catalog and never opens task storage. That separation keeps an information request free of persistent side effects.

## 1:53

The second request already provides a resource title and asks to save a twenty-five minute task. The model chooses create study task, the Action tool. The server validates the title, duration and request identifier, then commits one SQLite record. Its result includes a task identifier, original creation timestamp and planned status. The title can be a student's own notes, so this tool does not hide a catalog search inside a write operation. A study task is a saved intention; it does not create a calendar booking.

## 2:41

The third request asks for an MCP resource and a saved forty-minute session. The model chooses plan study session, the Orchestration tool. The server calls the same lookup operation followed by the same creation operation, then returns both typed results. The resource and saved task titles agree. This is one external MCP call coordinating two internal operations. If lookup fails, task creation is never reached.

## 3:23

The fourth request tries an unavailable topic, underwater basket weaving. The lookup returns a clear error and lists the supported topics. Notice the error result and the agent's explanation. A failed operation must not be described as successful, and the model must not invent a resource. The tests also cover invalid durations, empty inputs, conflicting retry identifiers and unavailable task storage. The tool contract makes those failures predictable and useful to the agent.

## 4:07

The final request repeats the earlier orchestration payload with the same request identifier. Compare the task identifier and creation timestamp with the original plan. They remain the same, and no duplicate task is inserted. The request identifier represents one intended task. A different title or duration with that identifier is rejected instead of silently changing the original. A SQLite transaction and unique constraint protect this behavior, including concurrent retries. This makes a repeated request safe when the caller is uncertain whether an earlier save completed.

## 4:54

The live outcomes and persisted tasks are now checked. Forty-three automated tests also pass, including real MCP transport and persistence across a server restart. The main design challenge was keeping lookup and saving separate while letting a student request both. I solved this with shared service operations and one orchestration tool, so validation rules stay consistent. Another challenge was retries after an uncertain save. Atomic transactions and a unique request identifier return the original task without inserting duplicates. Three tools fit these three user intentions. The fictional catalog keeps the demonstration reproducible, but limits it to three supported topics. Future work could add an authenticated catalog and separate task completion. The source, reading summary, reflection and evidence accompany this recording.
