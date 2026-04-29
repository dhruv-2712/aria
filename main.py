# main.py
import json
import threading
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from core.memory import init_db, get_session_logs, get_report
from orchestrator import Orchestrator

app = FastAPI(title="ARIA Research API", version="1.0.0")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# session_id → {status, metadata, report}
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
    _jobs[session_id] = {"status": "researching", "metadata": {}, "report": None}

    def run_job():
        try:
            def push_status(status):
                _jobs[session_id]["status"] = status

            orchestrator = Orchestrator()
            result = orchestrator.run(request.query, on_status=push_status)
            real_id = result.get("session_id", session_id)
            _jobs[session_id]["status"] = result.get("status", "failed")
            _jobs[session_id]["metadata"] = result.get("metadata", {})
            _jobs[session_id]["report"] = result.get("report", {})
            _jobs[session_id]["real_session_id"] = real_id
        except Exception as e:
            _jobs[session_id]["status"] = "failed"
            _jobs[session_id]["error"] = str(e)
            print(f"[API] Job failed: {e}")

    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()

    return {
        "session_id": session_id,
        "message": "Research job started",
        "query": request.query
    }


@app.get("/status/latest")
def get_latest_status():
    if not _jobs:
        return {"status": "no_jobs", "session_id": None}
    latest_id = list(_jobs.keys())[-1]
    job = _jobs[latest_id]
    return {
        "session_id": latest_id,
        "status": job["status"],
        "metadata": job.get("metadata", {})
    }


@app.get("/status/{session_id}")
def get_status(session_id: str):
    if session_id not in _jobs:
        raise HTTPException(status_code=404, detail="Session not found")
    job = _jobs[session_id]
    return {
        "session_id": session_id,
        "status": job["status"],
        "metadata": job.get("metadata", {})
    }


@app.get("/report/{session_id}")
def get_report_endpoint(session_id: str):
    if session_id in _jobs and _jobs[session_id].get("report"):
        return _jobs[session_id]["report"]
    # Fallback to DB
    real_id = _jobs.get(session_id, {}).get("real_session_id", session_id)
    report = get_report(real_id)
    if report:
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

from fastapi.responses import StreamingResponse
import asyncio

@app.get("/stream/{session_id}")
async def stream_status(session_id: str):
    async def event_generator():
        last_status = None
        for _ in range(200):  # max 10 minutes
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