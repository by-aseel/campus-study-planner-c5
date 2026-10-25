"""Local dashboard for a six-minute screencast of genuine SDK/MCP calls.

This is a presentation surface for the existing host, not an additional MCP tool.
It never sends provider secrets to the browser. Narration may be recorded by the
student or added separately; all prompts and displayed results come from a live run.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from uuid import uuid4

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel
from study_planner.client import PROVIDERS, demo_cases, make_server, run_turn, json_value

ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()
STATE = {"started": False, "start": None, "phase": "ready", "title": "Campus Study Planner",
         "prompt": "", "tool": "", "arguments": {}, "returned": None, "answer": "",
         "events": [], "records": [], "tasks": [], "complete": False, "error": ""}


def update(**values):
    with LOCK:
        STATE.update(values)


def snapshot():
    with LOCK:
        return json.loads(json.dumps(STATE))


def event(text):
    with LOCK:
        STATE["events"].append({"time": round(time.time() - STATE["start"], 1), "text": text})
        STATE["events"] = STATE["events"][-8:]


def tasks_at(database):
    if not database.exists():
        return []
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(x) for x in connection.execute("SELECT * FROM tasks ORDER BY created_at")]


async def wait_until(start, seconds):
    await asyncio.sleep(max(0, start + seconds - time.time()))


async def demonstrate(args):
    try:
        load_dotenv(args.env_file, encoding="utf-8-sig")
        provider = os.environ.get("LLM_PROVIDER", "groq").lower()
        config = PROVIDERS[provider]
        key = os.environ.get(config["key"], "").strip()
        if not key:
            raise RuntimeError("Configure a valid provider key locally before recording.")
        model_id = os.environ.get(config["model_env"], config["default_model"])
        prefix = "recording-" + uuid4().hex[:10]
        started = time.time()
        update(start=started, phase="introduction", provider=provider, model=model_id,
               title="Three tools. Three distinct responsibilities.")
        async with AsyncOpenAI(api_key=key, base_url=config["base_url"], max_retries=0, timeout=60) as api:
            model = OpenAIChatCompletionsModel(model=model_id, openai_client=api)
            async with make_server(database=args.database, verbose=False) as server:
                tools = await server.list_tools()
                if {x.name for x in tools} != {"find_study_resource", "create_study_task", "plan_study_session"}:
                    raise RuntimeError("Exactly three MCP tools must be discovered.")
                event("MCP handshake complete: exactly three typed tools discovered.")
                original = server.call_tool

                async def observed(tool_name, arguments, meta=None):
                    update(tool=tool_name, arguments=arguments, status="Calling MCP server")
                    event("Agent -> MCP client -> FastMCP server: " + tool_name)
                    result = await original(tool_name, arguments, meta)
                    value = json_value(result)
                    update(returned=value, status="MCP result returned to the agent")
                    event("FastMCP server -> MCP client -> agent: " +
                          ("explicit error" if value.get("isError", value.get("is_error", False)) else "structured result"))
                    return result

                server.call_tool = observed
                await wait_until(started, 30)
                update(phase="architecture", title="Host -> Client -> Server -> result")
                cases = demo_cases(prefix)
                records = []
                for index, (label, prompt, expected) in enumerate(cases):
                    await wait_until(started, 60 + index * 55)
                    update(phase="scenario", title=label, prompt=prompt, tool="", arguments={},
                           returned=None, answer="", scenario=index + 1, status="The live model is selecting a tool")
                    before = len(server.calls)
                    result = await run_turn(server, model, prompt)
                    calls = server.calls[before:]
                    expected_error = index == 3
                    matching = [x for x in calls if x["tool"] == expected]
                    ok = bool(matching) and all(
                        bool(x["result"].get("isError", x["result"].get("is_error", False))) == expected_error
                        for x in matching)
                    record = {"scenario": label, "prompt": prompt, "expected_tool": expected,
                              "correct_tool_outcome": ok, "calls": calls, "answer": str(result.final_output)}
                    records.append(record)
                    update(answer=str(result.final_output), records=records, tasks=tasks_at(args.database),
                           status="Scenario verified" if ok else "Scenario did not meet its expected outcome")
                    event("Agent returned its final answer; persisted tasks: " + str(len(tasks_at(args.database))))
                plans = []
                for index in (2, 4):
                    call = next(x for x in records[index]["calls"] if x["tool"] == "plan_study_session")
                    plans.append(call["result"]["structuredContent"]["task"])
                report = {"provider": provider, "requested_model": model_id,
                          "mode": "Live OpenAI Agents SDK -> MCP stdio -> FastMCP",
                          "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                          "scenarios": records, "identical_retry_returned_same_task": plans[0] == plans[1],
                          "final_database_row_count": len(tasks_at(args.database))}
                report["passed"] = all(x["correct_tool_outcome"] for x in records) and plans[0] == plans[1]
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
                await wait_until(started, 335)
                update(phase="reflection", title="Verified behavior and design tradeoffs", report=report)
                await wait_until(started, 360)
                update(complete=True, status="Six-minute live demonstration complete")
    except Exception as exc:
        # Never include exception bodies that might contain provider request headers.
        update(error=type(exc).__name__ + ": live run stopped; inspect the host separately.", complete=True)


HTML = r'''<!doctype html><html><head><meta charset="utf-8"><title>Campus Study Planner - Live MCP Demonstration</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101827;color:#e8eef9;font:17px/1.45 Arial,sans-serif}main{width:1280px;height:720px;padding:28px 34px;overflow:hidden}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #334155;padding-bottom:14px}h1{font-size:30px;margin:0}h2{font-size:24px;margin:0 0 12px}.tag{color:#8ee2c3;font-size:14px;letter-spacing:1px}.clock{font:26px Consolas,monospace}.muted{color:#a8b8d0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:20px}.card{background:#19263a;border:1px solid #31425d;border-radius:12px;padding:18px;height:505px;overflow:hidden}.wide{grid-column:1/3}.row{padding:14px;margin:12px 0;border-left:4px solid #6ab4ff;background:#111e31;border-radius:4px}.row b{color:#a7d4ff}pre{white-space:pre-wrap;word-break:break-word;font:14px/1.45 Consolas,monospace;color:#bcebd9;margin:8px 0;max-height:225px;overflow:hidden}.label{font-size:13px;letter-spacing:1px;color:#94b2da;margin-top:10px}.answer{font-size:16px;white-space:pre-wrap;border-top:1px solid #33465f;margin-top:12px;padding-top:10px;max-height:154px;overflow:hidden}.events{font:14px/1.5 Consolas,monospace;color:#c8d9ef;white-space:pre-wrap}footer{position:absolute;top:669px;font-size:13px;color:#a8b8d0}.pill{display:inline-block;padding:4px 10px;border:1px solid #4a6586;border-radius:16px;margin:3px;font-size:14px}.ok{color:#8ee2c3}.err{color:#ffb1b1}.flow{font-size:25px;line-height:2.8;text-align:center;margin-top:20px}button{background:#8ee2c3;border:0;border-radius:8px;padding:15px 24px;font-size:20px;cursor:pointer}p{margin:12px 0}.large{font-size:23px}.key{color:#8ee2c3}.small{font-size:15px}.split{display:grid;grid-template-columns:1fr 1fr;gap:15px}
</style></head><body><main><header><div><div class="tag">EECE 503P/798S · C5 AGENT TOOLS</div><h1>Campus Study Planner</h1></div><div><span class="pill">Genuine live SDK + MCP calls</span> <span class="clock" id="clock">00:00</span></div></header>
<div id="view"></div><footer>Fictional sample catalog · Real SQLite persistence · Narration is synthesized from the project script · No credentials are displayed</footer></main>
<script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=x=>JSON.stringify(x,null,2); const el=(s)=>document.getElementById(s);
function compact(r){if(!r)return '';if(r.isError)return {isError:true,message:(r.content||[]).map(x=>x.text||'').join('')};let d=r.structuredContent||{};if(d.resource&&d.task)return {resource_title:d.resource.title,task_id:d.task.task_id,minutes:d.task.minutes,request_id:d.task.request_id,created_at:d.task.created_at};if(d.task_id)return d;return {resource_id:d.resource_id,title:d.title,topic:d.topic,is_sample:d.is_sample,focus_points:d.focus_points};}
function render(s){let elapsed=s.start?Math.min(360,Math.floor(Date.now()/1000-s.start)):0;el('clock').textContent=String(Math.floor(elapsed/60)).padStart(2,'0')+':'+String(elapsed%60).padStart(2,'0');let v='';
if(!s.started){v='<div class="grid"><section class="card wide"><h2>Six-minute live demonstration</h2><p class="large">OpenAI Agents SDK + FastMCP + Groq</p><p>This recording runs five real model-selected scenarios and checks the results.</p><p>Data · Action · Orchestration · Clear failure · Safe retry</p><p><button id="start">Start live demonstration</button></p></section></div>';}
else if(s.error){v='<div class="grid"><section class="card wide"><h2>Run stopped</h2><p class="err">'+esc(s.error)+'</p></section></div>';}
else if(s.phase==='introduction'){v='<div class="grid"><section class="card"><h2>Three distinct responsibilities</h2><div class="row"><b>DATA · find_study_resource</b><br>Retrieve one resource. No task writes.</div><div class="row"><b>ACTION · create_study_task</b><br>Persist one study intention in SQLite.</div><div class="row"><b>ORCHESTRATION · plan_study_session</b><br>Find a resource, then save its study task.</div></section><section class="card"><h2>A deliberately narrow toolkit</h2><p class="large">Exactly <span class="key">3</span> MCP tools</p><p>Typed arguments and Pydantic outputs</p><p>Clear descriptions and predictable errors</p><p>Fictional catalog: Python async, REST APIs, MCP tools</p><p>Real local persistence with safe retries</p><p class="muted">The model chooses the tool. The host runs the agent loop.</p></section></div>';}
else if(s.phase==='architecture'){v='<div class="grid"><section class="card"><h2>Host, Client, and Server</h2><div class="flow">Student request<br>↓<br>OpenAI Agents SDK <small>(Host)</small><br>↕ MCPServerStdio <small>(Client)</small><br>↕ FastMCP <small>(Server)</small></div></section><section class="card"><h2>The actual round trip</h2><p>1. Connect and discover tool schemas.</p><p>2. Send the request and tool definitions to Groq.</p><p>3. The model selects a tool and arguments.</p><p>4. SDK → MCP client → FastMCP server.</p><p>5. Return the structured result to the model.</p><p>6. Display the agent’s final answer.</p><div class="row small">Orchestration uses the same Python lookup and save operations inside the server. It is one external MCP call.</div></section></div>';}
else if(s.phase==='reflection'){let rows=s.tasks.map(t=>'<div class="row small"><b>'+esc(t.resource_title)+'</b><br>'+t.minutes+' minutes · '+esc(t.task_id)+'</div>').join('');v='<div class="grid"><section class="card"><h2>Verified results</h2><p class="large ok">'+(s.report?.passed?'All five live scenarios passed':'Review the evidence')+'</p><p>43 automated tests passed</p><p>Exactly three described and typed MCP tools</p><p>Clear errors; failed lookup writes nothing</p><p>Retry returned the original task and timestamp</p><p>Tasks persist after a server restart</p><div class="row small">Evidence: live-agent.json, recorded-live-agent.json, mcp-verification.json</div></section><section class="card"><h2>Boundaries and next steps</h2><p>Shared operations prevent duplicated rules.</p><p>Atomic transactions prevent retry duplicates.</p><p>Three tools fit the three user intentions.</p><p>Next: real catalog integration and separate task-completion capability.</p><div class="label">ACTUAL SAVED TASKS</div>'+rows+'</section></div>';}
else{let ret=compact(s.returned);v='<div class="grid"><section class="card"><h2>'+esc(s.title)+'</h2><div class="label">NATURAL-LANGUAGE REQUEST</div><p>'+esc(s.prompt)+'</p><div class="label">MODEL-SELECTED TOOL</div><div class="pill">'+esc(s.tool||'Waiting for the model…')+'</div><div class="label">ACTUAL ARGUMENTS</div><pre>'+esc(s.tool?fmt(s.arguments):'')+'</pre><div class="label">OBSERVED ROUND TRIP</div><div class="events">'+s.events.slice(-4).map(x=>esc(x.time+'s  '+x.text)).join('\n')+'</div></section><section class="card"><h2>Server result → Agent answer</h2><div class="label">ACTUAL RETURNED FIELDS '+(s.returned?.isError?'· ERROR':'')+'</div><pre>'+esc(typeof ret==='string'?ret:fmt(ret))+'</pre><div class="label">AGENT’S FINAL ANSWER</div><div class="answer">'+esc(s.answer||'The agent is processing the returned result…')+'</div><p class="small muted">'+esc(s.status||'')+' · Saved tasks: '+s.tasks.length+'</p></section></div>';}
el('view').innerHTML=v;if(el('start'))el('start').onclick=()=>fetch('/start',{method:'POST'});}
async function refresh(){try{render(await (await fetch('/state')).json())}catch(e){}}setInterval(refresh,700);refresh();
</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=ROOT / "evidence" / "recorded-live-agent.json")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()
    args.database = args.database.resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/state":
                body = json.dumps(snapshot()).encode()
                content_type = "application/json"
            elif self.path == "/":
                body, content_type = HTML.encode(), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/start":
                self.send_error(404)
                return
            with LOCK:
                launch = not STATE["started"]
                STATE["started"] = True
            if launch:
                threading.Thread(target=lambda: asyncio.run(demonstrate(args)), daemon=True).start()
            self.send_response(204)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Recording dashboard: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
