# main.py
import json
import os
import threading
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.memory import (
    init_db, get_session, get_session_logs, get_report, get_all_sessions
)
from orchestrator import Orchestrator
import asyncio

app = FastAPI(title="ARIA Research API", version="2.0.0")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

# session_id → {status, metadata, report, follow_ups, executive_tokens, executive_complete}
_jobs: dict = {}


class ResearchRequest(BaseModel):
    query: str


@app.on_event("startup")
def startup():
    init_db()
    print("[ARIA] API ready.")


@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")


@app.post("/research")
def start_research(request: ResearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    session_id = str(uuid.uuid4())
    _jobs[session_id] = {
        "status": "researching",
        "metadata": {},
        "report": None,
        "follow_ups": [],
        "executive_tokens": [],
        "executive_complete": False,
    }

    def run_job():
        try:
            def push_status(status):
                _jobs[session_id]["status"] = status

            def on_token(t):
                _jobs[session_id]["executive_tokens"].append(t)

            orchestrator = Orchestrator()
            result = orchestrator.run(
                request.query,
                on_status=push_status,
                on_executive_token=on_token,
            )
            real_id = result.get("session_id", session_id)
            _jobs[session_id]["status"] = result.get("status", "failed")
            _jobs[session_id]["metadata"] = result.get("metadata", {})
            _jobs[session_id]["report"] = result.get("report", {})
            _jobs[session_id]["follow_ups"] = result.get("follow_ups", [])
            _jobs[session_id]["real_session_id"] = real_id
            _jobs[session_id]["executive_complete"] = True
            _send_webhook(real_id, request.query, result.get("metadata", {}), result.get("follow_ups", []))
        except Exception as e:
            _jobs[session_id]["status"] = "failed"
            _jobs[session_id]["error"] = str(e)
            _jobs[session_id]["executive_complete"] = True
            print(f"[API] Job failed: {e}")

    threading.Thread(target=run_job, daemon=True).start()
    return {"session_id": session_id, "message": "Research job started", "query": request.query}


def _send_webhook(session_id: str, query: str, metadata: dict, follow_ups: list):
    if not WEBHOOK_URL:
        return
    try:
        import httpx
        httpx.post(WEBHOOK_URL, json={
            "session_id": session_id,
            "query": query,
            "status": "done",
            "metadata": metadata,
            "follow_ups": follow_ups,
            "share_url": f"/r/{session_id}",
        }, timeout=5)
        print(f"[API] Webhook sent to {WEBHOOK_URL}")
    except Exception as e:
        print(f"[API] Webhook failed: {e}")


@app.get("/status/latest")
def get_latest_status():
    if not _jobs:
        return {"status": "no_jobs", "session_id": None}
    latest_id = list(_jobs.keys())[-1]
    job = _jobs[latest_id]
    return {"session_id": latest_id, "status": job["status"], "metadata": job.get("metadata", {})}


@app.get("/status/{session_id}")
def get_status(session_id: str):
    if session_id not in _jobs:
        raise HTTPException(status_code=404, detail="Session not found")
    job = _jobs[session_id]
    return {"session_id": session_id, "status": job["status"], "metadata": job.get("metadata", {})}


@app.get("/report/{session_id}")
def get_report_endpoint(session_id: str):
    if session_id in _jobs and _jobs[session_id].get("report"):
        report_data = dict(_jobs[session_id]["report"])
        report_data["follow_ups"] = _jobs[session_id].get("follow_ups", [])
        return report_data
    real_id = _jobs.get(session_id, {}).get("real_session_id", session_id)
    report = get_report(real_id)
    if report:
        if report.get("follow_ups_json"):
            report["follow_ups"] = json.loads(report["follow_ups_json"])
        else:
            report["follow_ups"] = []
        return report
    raise HTTPException(status_code=404, detail="Report not found or still generating")


@app.get("/logs/{session_id}")
def get_logs_endpoint(session_id: str):
    real_id = _jobs.get(session_id, {}).get("real_session_id", session_id)
    logs = get_session_logs(real_id)
    if not logs:
        raise HTTPException(status_code=404, detail="No logs found")
    return {"session_id": real_id, "logs": logs}


@app.get("/health")
def health():
    return {"status": "ok", "active_jobs": len(_jobs)}


@app.get("/sessions")
def get_sessions_endpoint():
    return get_all_sessions(limit=20)


@app.get("/stream-report/{session_id}")
async def stream_report(session_id: str):
    async def generator():
        pos = 0
        for _ in range(600):
            await asyncio.sleep(0.1)
            if session_id not in _jobs:
                break
            job    = _jobs[session_id]
            tokens = job.get("executive_tokens", [])
            while pos < len(tokens):
                yield f"data: {json.dumps({'token': tokens[pos]})}\n\n"
                pos += 1
                await asyncio.sleep(0)
            if job.get("executive_complete") and pos >= len(tokens):
                yield f"data: {json.dumps({'done': True})}\n\n"
                break
    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/stream/{session_id}")
async def stream_status(session_id: str):
    async def event_generator():
        last_status = None
        for _ in range(200):
            await asyncio.sleep(2)
            if session_id not in _jobs:
                continue
            job = _jobs[session_id]
            status = job["status"]
            if status != last_status:
                last_status = status
                yield f"data: {json.dumps({'status': status})}\n\n"
            if status in ("done", "failed"):
                break
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Share Link ──────────────────────────────────────────────────────────────

_SHARE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ARIA · ARIA_QUERY_TOKEN</title>
  <style>
    :root{--acc:#00cff5;--bg:#010407;--bg2:rgba(4,12,24,0.9);--text:#c5e4f5;--muted:#4580a0;--faint:#224055;--mono:ui-monospace,'JetBrains Mono',monospace;}
    *{box-sizing:border-box;margin:0;padding:0;}
    html{scroll-behavior:smooth;}
    body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;max-width:880px;margin:0 auto;padding:2rem 1.25rem 5rem;line-height:1.75;}
    .brand{font-family:var(--mono);font-size:0.62rem;color:var(--acc);letter-spacing:0.3em;opacity:0.65;margin-bottom:0.65rem;}
    h1.query{font-size:1.45rem;font-weight:600;color:#e8f4fc;line-height:1.35;margin-bottom:0.5rem;}
    .meta{font-family:var(--mono);font-size:0.62rem;color:var(--faint);margin-bottom:1.75rem;padding-bottom:1.25rem;border-bottom:1px solid rgba(0,200,240,0.1);}
    .tab-bar{display:flex;gap:0.25rem;margin-bottom:1.25rem;flex-wrap:wrap;}
    .tab{background:none;border:1px solid rgba(0,200,240,0.15);color:var(--faint);padding:0.32rem 0.85rem;border-radius:4px;cursor:pointer;font-family:var(--mono);font-size:0.67rem;letter-spacing:0.08em;transition:all 0.18s;}
    .tab.active{border-color:var(--acc);color:var(--acc);background:rgba(0,207,245,0.07);}
    .content{min-height:300px;}
    .content h1{font-size:1.15rem;color:#00eeff;margin:0 0 1rem;padding-bottom:0.6rem;border-bottom:1px solid rgba(0,200,240,0.1);}
    .content h2{font-size:0.95rem;color:var(--acc);margin:1.75rem 0 0.6rem;}
    .content h3{font-size:0.83rem;color:var(--text);margin:1.25rem 0 0.4rem;text-transform:uppercase;letter-spacing:0.06em;}
    .content p{margin-bottom:0.85rem;}
    .content strong{color:#00eeff;}
    .content em{color:var(--muted);font-style:italic;}
    .content ul{padding-left:1.25rem;margin-bottom:0.85rem;}
    .content li{margin-bottom:0.3rem;}
    .content blockquote{border-left:2px solid var(--acc);padding-left:1rem;color:var(--muted);margin:1rem 0;font-style:italic;}
    .content code{font-family:var(--mono);font-size:0.82em;background:rgba(0,200,240,0.06);border:1px solid rgba(0,200,240,0.15);padding:0.1em 0.38em;border-radius:3px;color:var(--acc);}
    .citation-item{border:1px solid rgba(0,200,240,0.1);border-radius:4px;padding:0.5rem 0.85rem;margin-bottom:0.35rem;display:flex;gap:0.75rem;align-items:flex-start;}
    .ci-num{color:var(--acc);font-family:var(--mono);font-size:0.6rem;flex-shrink:0;opacity:0.5;padding-top:0.1rem;}
    .ci-url a{color:var(--muted);text-decoration:none;word-break:break-all;font-size:0.76rem;}
    .ci-url a:hover{color:var(--acc);}
    .footer{margin-top:3rem;padding-top:1.25rem;border-top:1px solid rgba(0,200,240,0.08);font-family:var(--mono);font-size:0.6rem;color:var(--faint);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;}
    .footer a{color:var(--acc);text-decoration:none;opacity:0.7;}
    .footer a:hover{opacity:1;}
    @media(max-width:600px){body{padding:1.25rem 0.85rem 4rem;}h1.query{font-size:1.2rem;}}
    @media print{body{background:#fff;color:#111;padding:0;}a{color:#00b}h1.query{color:#000;}.content h1{color:#000;border-color:#ccc;}.content h2{color:#111;}.content h3{color:#222;}.content strong{color:#000;}.tab-bar,.footer{display:none;}}
  </style>
</head>
<body>
  <div class="brand">[ ARIA ] — INTELLIGENCE REPORT</div>
  <h1 class="query">ARIA_QUERY_TOKEN</h1>
  <div class="meta">Generated ARIA_DATE_TOKEN &nbsp;·&nbsp; aria-emh3.onrender.com</div>
  <div class="tab-bar">
    <button class="tab active" onclick="showTab('executive',this)">Executive</button>
    <button class="tab" onclick="showTab('standard',this)">Full Report</button>
    <button class="tab" onclick="showTab('citations',this)">Citations</button>
  </div>
  <div class="content" id="content"></div>
  <div class="footer">
    <span>Shared via ARIA Autonomous Research Pipeline</span>
    <a href="/">Run your own research →</a>
  </div>
  <script>
    const R = ARIA_REPORT_JSON_TOKEN;
    function md(t){
      return t
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/^### (.+)$/gm,'<h3>$1</h3>')
        .replace(/^## (.+)$/gm,'<h2>$1</h2>')
        .replace(/^# (.+)$/gm,'<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
        .replace(/\*(.+?)\*/g,'<em>$1</em>')
        .replace(/`([^`]+)`/g,'<code>$1</code>')
        .replace(/((?:^[*\-] .+\n?)+)/gm,m=>'<ul>'+m.trim().split('\n').map(l=>'<li>'+l.replace(/^[*\-] /,'')+'</li>').join('')+'</ul>')
        .replace(/^> (.+)$/gm,'<blockquote>$1</blockquote>')
        .replace(/\n\n+/g,'</p><p>').replace(/\n/g,'<br>')
        .replace(/^/,'<p>').replace(/$/,'</p>')
        .replace(/<p>(<(?:h[123]|ul|blockquote))/g,'$1')
        .replace(/(<\/(?:h[123]|ul|blockquote)>)<\/p>/g,'$1')
        .replace(/<p><\/p>/g,'');
    }
    function showTab(tab,btn){
      document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
      if(btn) btn.classList.add('active');
      const c=document.getElementById('content');
      if(tab==='citations'){
        const cits=R.citations_json?JSON.parse(R.citations_json):(R.citations||[]);
        c.innerHTML=cits.length?cits.map((ci,i)=>'<div class="citation-item"><span class="ci-num">['+(i+1).toString().padStart(2,'0')+']</span><span class="ci-url"><a href="'+ci.url+'" target="_blank" rel="noopener">'+ci.url+'</a></span></div>').join(''):'<p style="color:#224055">No citations recorded.</p>';
      }else{
        c.innerHTML=md(R[tab]||'Not available.');
      }
    }
    showTab('executive',document.querySelector('.tab'));
  </script>
</body>
</html>"""


@app.get("/r/{session_id}")
def share_report_page(session_id: str):
    real_id = _jobs.get(session_id, {}).get("real_session_id", session_id)
    report  = get_report(real_id)
    session = get_session(real_id)
    if not report or not session:
        return HTMLResponse(
            "<h1 style='font-family:monospace;padding:2rem;color:#ccc;background:#010407;min-height:100vh'>Report not found.</h1>",
            status_code=404
        )

    query      = session.get("query", "Research Report")
    created_at = report.get("created_at", "")[:16].replace("T", " ") + " UTC"
    query_safe = (query.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        .replace('"', "&quot;").replace("'", "&#39;"))

    report_payload = {
        "executive":       report.get("executive", ""),
        "standard":        report.get("standard", ""),
        "technical":       report.get("technical", ""),
        "citations_json":  report.get("citations_json", "[]"),
    }

    html = (_SHARE_TEMPLATE
            .replace("ARIA_QUERY_TOKEN",       query_safe)
            .replace("ARIA_DATE_TOKEN",        created_at)
            .replace("ARIA_REPORT_JSON_TOKEN", json.dumps(report_payload)))
    return HTMLResponse(html)
