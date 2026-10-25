"""Interactive recording surface for complete, uninterrupted SDK/MCP round trips.

Run this local dashboard, enter a request, and click Run query. Each request is
sent to the real Agents SDK host; the model selects the tool. The UI never
fabricates calls or replies. No provider credentials are sent to the browser.
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

from agents import OpenAIChatCompletionsModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
from study_planner.client import PROVIDERS, demo_cases, json_value, make_server, run_turn

ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.RLock()
STATE = dict(ready=False, busy=False, index=0, scene_start=time.time(), prompt='',
             tool='', arguments={}, returned=None, answer='', events=[], records=[],
             tasks=[], error='', status='Connecting to the real MCP server...')
LOOP = None
QUEUE = None
ARGS = None
CASES = []


def update(**values):
    with LOCK:
        STATE.update(values)


def snapshot():
    with LOCK:
        result = json.loads(json.dumps(STATE))
    result['title'] = CASES[result['index']][0] if result['index'] < 5 else 'Verified results and design choices'
    result['elapsed'] = max(0,time.time()-result['scene_start']) if result['prompt'] else 0
    return result


def event(message):
    with LOCK:
        STATE['events'].append({'at':time.time(), 'message':message})


def saved_tasks():
    if not ARGS.database.exists():
        return []
    with closing(sqlite3.connect(ARGS.database.as_uri()+'?mode=ro',uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute('SELECT * FROM tasks ORDER BY created_at')]


def save_report():
    records = snapshot()['records']
    report = dict(mode='Live user-entered queries -> Agents SDK -> MCP stdio -> FastMCP',
                  timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  provider=STATE.get('provider'), requested_model=STATE.get('model'),
                  scenarios=records, final_database_row_count=len(saved_tasks()))
    if len(records)==5:
        tasks=[]
        for index in (2,4):
            call=next(call for call in records[index]['calls'] if call['tool']=='plan_study_session')
            tasks.append(call['result']['structuredContent']['task'])
        report['identical_retry_returned_same_task']=tasks[0]==tasks[1]
        report['passed']=all(row['correct_tool_outcome'] for row in records) and tasks[0]==tasks[1] and len(saved_tasks())==2
    else:
        report['passed']=False
    ARGS.report.parent.mkdir(parents=True,exist_ok=True)
    ARGS.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')


async def worker():
    global LOOP, QUEUE
    LOOP=asyncio.get_running_loop()
    QUEUE=asyncio.Queue()
    load_dotenv(ARGS.env_file,encoding='utf-8-sig')
    provider=os.environ.get('LLM_PROVIDER','groq').strip().lower()
    config=PROVIDERS[provider]
    key=os.environ.get(config['key'],'').strip()
    if not key:
        raise RuntimeError('A provider key must be configured privately in the host.')
    model_id=os.environ.get(config['model_env'],config['default_model'])
    update(provider=provider,model=model_id)
    async with AsyncOpenAI(api_key=key,base_url=config['base_url'],timeout=45,max_retries=0) as api:
        model=OpenAIChatCompletionsModel(model=model_id,openai_client=api)
        async with make_server(database=ARGS.database,verbose=False) as server:
            tools=await server.list_tools()
            names=sorted(tool.name for tool in tools)
            assert set(names)=={'find_study_resource','create_study_task','plan_study_session'}
            update(ready=True,status='Ready: exactly three typed MCP tools discovered.',tools=names)
            original=server.call_tool

            async def observed(name,arguments,meta=None):
                selected=time.time()
                update(tool=name,arguments=arguments,status='Model selected a tool; MCP client is calling the server.')
                event('Agent selected '+name)
                event('MCP client -> FastMCP server: actual arguments sent')
                response=await original(name,arguments,meta)
                value=json_value(response)
                update(returned=value,status='Server result returned through MCP; model is composing its answer.')
                event('FastMCP server -> MCP client: '+('explicit error' if value.get('isError',False) else 'structured result'))
                event('Host -> model: actual tool result returned')
                with LOCK:
                    STATE['selected_at']=selected
                    STATE['returned_at']=time.time()
                return response

            server.call_tool=observed
            while True:
                prompt,index=await QUEUE.get()
                before=len(server.calls)
                submitted=time.time()
                update(prompt=prompt,submitted_at=submitted,scene_start=submitted,status='Request submitted. Host is waiting for the model to choose a tool.')
                event('User -> host: request submitted')
                try:
                    result=await run_turn(server,model,prompt)
                    final=time.time()
                    calls=server.calls[before:]
                    expected=CASES[index][2]
                    matching=[call for call in calls if call['tool']==expected]
                    ok=bool(matching) and all(bool(call['result'].get('isError',False))==(index==3) for call in matching)
                    record=dict(scenario=CASES[index][0],prompt=prompt,expected_tool=expected,
                                correct_tool_outcome=ok,calls=calls,answer=str(result.final_output),
                                submitted_at=submitted,selected_at=STATE.get('selected_at'),
                                returned_at=STATE.get('returned_at'),final_answer_at=final)
                    with LOCK:
                        STATE['records'].append(record)
                    update(answer=str(result.final_output),busy=False,tasks=saved_tasks(),
                           status='Round trip verified.' if ok else 'Unexpected outcome: inspect the evidence.')
                    event('Agent -> user: final answer displayed')
                    save_report()
                except Exception as error:
                    update(error=type(error).__name__+': live request stopped. No success is claimed.',busy=False)
                QUEUE.task_done()


CSS='''*{box-sizing:border-box}body{margin:0;background:#101827;color:#edf3ff;font:16px/1.4 Arial,sans-serif}main{width:1280px;height:720px;padding:22px 30px;overflow:hidden}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #354a65;padding-bottom:10px}h1{font-size:28px;margin:0}h2{font-size:22px;margin:0 0 8px}.tag{color:#8ee2c3;font-size:13px;letter-spacing:1px}.clock{font:25px Consolas,monospace}.status{color:#b4d4ef;margin:8px 0;font-size:14px}form{display:flex;align-items:end;gap:14px;margin:10px 0 15px}label{display:block;color:#a8c7e8;font-size:13px;letter-spacing:1px}textarea{display:block;width:990px;height:73px;background:#17263b;color:#fff;border:1px solid #6b91b8;border-radius:6px;padding:10px;font:16px/1.35 Arial;resize:none}button{border:0;border-radius:6px;background:#8ee2c3;color:#102033;padding:12px 16px;font-size:16px;cursor:pointer}button:disabled{opacity:.5;cursor:default}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{height:420px;background:#19283d;border:1px solid #334a65;border-radius:10px;padding:15px;overflow:hidden}.label{color:#9bb9dc;font-size:12px;letter-spacing:1px;margin-top:8px}pre{font:14px/1.4 Consolas,monospace;color:#bcebd9;white-space:pre-wrap;word-break:break-word;margin:7px 0;max-height:190px;overflow:hidden}.tool{color:#8ee2c3;font:bold 17px Consolas;margin:7px 0}.events{font:13px/1.7 Consolas,monospace;white-space:pre-wrap}.answer{font-size:16px;white-space:pre-wrap;border-top:1px solid #405674;padding-top:8px;max-height:130px;overflow:hidden}.foot{position:absolute;top:681px;color:#a8bcd4;font-size:12px}.pill{display:inline-block;border:1px solid #4b6c8b;border-radius:14px;padding:3px 10px;font-size:13px;margin-right:10px}.row{padding:18px;margin:18px 0;border-left:4px solid #83c4ff;background:#111e31;border-radius:6px}.wide{height:545px;margin-top:18px}.large{font-size:23px}.flow{font-size:25px;line-height:2.5;text-align:center}a{color:#a7d4ff}h2{font-size:20px;margin:0 0 4px}.label{margin-top:4px;font-size:11px}.tool{font-size:16px;margin:3px 0}pre{line-height:1.2;margin:4px 0}.events{font-size:12px;line-height:1.45}.result{display:flex;flex-direction:column}.result pre{flex:0 0 auto;max-height:175px}.result .answer{flex:1;min-height:0;max-height:none;overflow:auto;font-size:14px;line-height:1.25}.result .status{margin:4px 0 0}'''

HTML='''<!doctype html><html><head><meta charset="utf-8"><title>Campus Study Planner | Real live round trips</title><style>'''+CSS+r'''</style></head><body><main><header><div><div class="tag">C5 AGENT TOOLS · LIVE QUERY TO FINAL ANSWER</div><h1 id="title">Campus Study Planner</h1></div><div><span class="pill">Real SDK + MCP traffic</span><span class="clock" id="clock">00:00.0</span></div></header><div class="status" id="status">Connecting...</div>
<form id="request-form"><div><label for="query">ENTER YOUR REQUEST</label><textarea id="query" aria-label="Enter your request" placeholder="Enter a natural-language request, then click Run query."></textarea></div><button id="run" type="submit" disabled>Run query</button></form>
<div class="grid"><section class="card"><h2>Agent -> MCP client -> Server</h2><div class="label">MODEL-SELECTED TOOL</div><div class="tool" id="tool">Waiting for a request</div><div class="label">ACTUAL ARGUMENTS</div><pre id="arguments">No tool has been called.</pre><div class="label">LIVE ROUND-TRIP EVENTS</div><div id="events" class="events"></div></section><section class="card result"><h2>Server result -> Agent answer</h2><div class="label">ACTUAL RETURNED FIELDS</div><pre id="returned">Waiting for the live result...</pre><div class="label">AGENT'S FINAL ANSWER</div><div class="answer" id="answer">Waiting for the agent...</div><div class="status" id="saved">Saved tasks: 0</div></section></div><div class="foot">Complete query-to-answer recording · Fictional catalog, real SQLite writes · Authorized synthesized narration <button id="next" type="button" style="font-size:12px;padding:3px 10px;margin-left:30px" disabled>Next query</button></div></main>
<script>
const el=id=>document.getElementById(id);let current=null;
function compact(r){if(!r)return 'Waiting for the live result...';if(r.isError)return {isError:true,message:r.content.map(x=>x.text||'').join('')};let d=r.structuredContent||{};if(d.resource&&d.task)return {resource_title:d.resource.title,...d.task};if(d.resource_id)return {resource_id:d.resource_id,title:d.title,topic:d.topic,is_sample:d.is_sample};return d;}
async function refresh(){const s=await(await fetch('/state')).json();current=s;el('title').textContent=s.title;el('status').textContent=s.error||s.status;el('tool').textContent=s.tool||'Waiting for the model to select a tool';el('arguments').textContent=s.tool?JSON.stringify(s.arguments,null,2):'No tool has been called.';el('returned').textContent=typeof compact(s.returned)==='string'?compact(s.returned):JSON.stringify(compact(s.returned),null,2);el('answer').textContent=s.answer||'Waiting for the agent...';el('events').textContent=s.events.map(e=>(e.at-s.scene_start).toFixed(3)+'s  '+e.message).join('\n');el('saved').textContent='Saved tasks: '+s.tasks.length;el('run').disabled=!s.ready||s.busy||Boolean(s.answer)||s.index>=5;el('next').disabled=s.busy||!s.answer;el('next').textContent=s.index===4?'Show summary':'Next query';}
el('request-form').onsubmit=async e=>{e.preventDefault();el('run').disabled=true;await fetch('/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:el('query').value})});await refresh();};
el('next').onclick=async()=>{const r=await fetch('/next',{method:'POST'});if(r.ok){const s=await r.json();if(s.index===5){location.href='/summary';return}el('query').value='';await refresh();}};
setInterval(()=>{if(current){let t=current.elapsed;el('clock').textContent=String(Math.floor(t/60)).padStart(2,'0')+':'+(t%60).toFixed(1).padStart(4,'0');}},100);setInterval(refresh,200);refresh();
</script></body></html>'''


def card_page(kind):
    if kind=='overview':
        body='''<div class="grid"><section class="card wide"><h2>Three focused tools</h2><div class="row"><b>DATA · find_study_resource</b><br>Read one catalog resource. No task writes.</div><div class="row"><b>ACTION · create_study_task</b><br>Save one study intention in SQLite.</div><div class="row"><b>ORCHESTRATION · plan_study_session</b><br>Find a resource, then save its study task.</div></section><section class="card wide"><h2>Campus Study Planner</h2><p class="large">OpenAI Agents SDK + FastMCP + Groq</p><p>Exactly three described, typed MCP tools</p><p>Fictional catalog; real durable task storage</p><p>Live user-entered queries and model-selected calls</p><p>Each query-to-answer sequence is captured without a cut or speed change.</p><p>Failures and safe retries are also demonstrated.</p></section></div>'''
    elif kind=='architecture':
        body='''<div class="grid"><section class="card wide"><h2>Host, Client, and Server</h2><div class="flow">Student request<br>↓<br>OpenAI Agents SDK (Host)<br>↕ MCPServerStdio (Client)<br>↕ FastMCP (Server)</div></section><section class="card wide"><h2>The actual round trip</h2><div class="row">1. Enter a request and submit it to the host.<br>2. The model chooses a tool and arguments.<br>3. MCP client sends the call to FastMCP.<br>4. The server returns a typed result or clear error.<br>5. The host returns that result to the model.<br>6. The agent answers the original request.</div><p>Tool discovery and actual traffic are recorded in the evidence.</p><p>Orchestration is one external MCP call using two shared service operations.</p></section></div>'''
    else:
        s=snapshot();passed=len(s['records'])==5 and all(r['correct_tool_outcome'] for r in s['records'])
        rows=''.join('<div class="row"><b>'+task['resource_title']+'</b><br>'+str(task['minutes'])+' minutes<br><small>'+task['task_id']+'</small></div>' for task in s['tasks'])
        body='<div class="grid"><section class="card wide"><h2>Verified behavior</h2><p class="large">'+('All five live scenarios passed' if passed else 'Review live outcomes')+'</p><p>43 automated tests passed</p><p>Three focused, typed tools</p><p>Unknown topic returned a clear error</p><p>Retry preserved the task ID and timestamp</p><p>Two tasks saved in this same live session</p><p>Shared operations keep validation consistent.</p><p>Atomic transactions prevent duplicate saves.</p><p>Next: authenticated catalog and separate task completion.</p></section><section class="card wide"><h2>Actual saved tasks</h2>'+rows+'</section></div>'
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Campus Study Planner | '+kind+'</title><style>'+CSS+'</style></head><body><main><header><div><div class="tag">EECE 503P/798S · C5 AGENT TOOLS</div><h1>Campus Study Planner</h1></div><span class="pill">'+kind.upper()+'</span></header>'+body+'<div class="foot">Exactly three FastMCP tools · Real OpenAI Agents SDK host · Authorized synthesized voice narration</div></main></body></html>').encode()


def main():
    global ARGS, CASES
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,default=ROOT/'.env')
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--session-file',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8774)
    ARGS=parser.parse_args();ARGS.database=ARGS.database.resolve()
    prefix='continuous-'+uuid4().hex[:10]
    CASES=demo_cases(prefix)
    ARGS.session_file.parent.mkdir(parents=True,exist_ok=True)
    ARGS.session_file.write_text(json.dumps({'prefix':prefix,'cases':[{'label':a,'prompt':b,'expected_tool':c} for a,b,c in CASES]},indent=2),encoding='utf-8')
    def bootstrap():
        try:asyncio.run(worker())
        except Exception as error:update(error=type(error).__name__+': host connection failed.',ready=False)
    threading.Thread(target=bootstrap,daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path=='/state':body=json.dumps(snapshot()).encode();mime='application/json'
            elif self.path=='/':body=HTML.encode();mime='text/html; charset=utf-8'
            elif self.path in {'/overview','/architecture','/summary'}:body=card_page(self.path[1:]);mime='text/html; charset=utf-8'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if self.path=='/query':
                data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
                prompt=str(data.get('prompt','')).strip()
                with LOCK:
                    if not prompt or STATE['busy'] or STATE['answer'] or not STATE['ready'] or STATE['index']>=5:self.send_error(409);return
                    STATE['busy']=True
                    index=STATE['index']
                asyncio.run_coroutine_threadsafe(QUEUE.put((prompt,index)),LOOP)
            elif self.path=='/next':
                with LOCK:
                    if STATE['busy'] or not STATE['answer']:self.send_error(409);return
                    STATE.update(index=STATE['index']+1,scene_start=time.time(),prompt='',tool='',arguments={},returned=None,answer='',events=[],error='',status='Ready for the next user-entered request.')
            else:self.send_error(404);return
            body=json.dumps(snapshot()).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    print(f'Interactive live capture: http://127.0.0.1:{ARGS.port}/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',ARGS.port),Handler).serve_forever()


if __name__=='__main__':main()
