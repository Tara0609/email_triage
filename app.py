"""
FastAPI server implementing the OpenEnv HTTP spec for Email Triage.

Session-based: every /reset call returns a unique session_id.
All subsequent /step and /state calls must include that session_id,
allowing multiple agents to run concurrently without interference.

Endpoints:
  POST /reset   – start a new episode, returns session_id
  POST /step    – submit one action for a session
  GET  /state   – inspect current episode state  (?session_id=...)
  GET  /tasks   – list available tasks
  GET  /health  – health check
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from env import EmailTriageEnv
from env.models import StepResult, StateResponse, ResetResponse

app = FastAPI(
    title="Email Triage OpenEnv",
    description=(
        "An OpenEnv-compliant environment for evaluating AI agents on "
        "real-world email triage tasks across 4 difficulty levels."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Session store  — { session_id: EmailTriageEnv }
# ---------------------------------------------------------------------------
_sessions: Dict[str, EmailTriageEnv] = {}


def _get_session(session_id: str) -> EmailTriageEnv:
    env = _sessions.get(session_id)
    if env is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Call POST /reset first.",
        )
    return env


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_id: str = "task_1"
    session_id: Optional[str] = None   # client may supply one; else auto-generated


class StepRequest(BaseModel):
    session_id: str
    action: Dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Space homepage — confirms the server is live."""
    return {
        "service": "email-triage-openenv",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "tasks": "/tasks",
        "usage": {
            "reset": "POST /reset  body: {task_id: task_1|task_2|task_3|task_4}",
            "step":  "POST /step   body: {session_id, action}",
            "state": "GET  /state  query: ?session_id=...",
        },
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "email-triage-openenv",
        "version": "2.0.0",
        "active_sessions": len(_sessions),
    }


@app.get("/tasks")
def list_tasks():
    from env.tasks import TASKS
    return {
        "tasks": [
            {
                "id": t["id"],
                "name": t["name"],
                "difficulty": t["difficulty"],
                "num_emails": len(t["email_ids"]),
                "action_type": t["action_type"],
                "max_steps": t["max_steps"],
            }
            for t in TASKS.values()
        ]
    }


@app.post("/reset", response_model=ResetResponse)
def reset(body: Optional[ResetRequest] = Body(default=None)):
    """
    Start a new episode.
    Body is fully optional — bare POST /reset uses task_1 by default.
    Accepts: no body, empty {}, or {"task_id": "task_1", "session_id": null}
    """
    request = body if body is not None else ResetRequest()
    sid = request.session_id or str(uuid.uuid4())
    env = EmailTriageEnv()
    _sessions[sid] = env

    try:
        obs = env.reset(task_id=request.task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

    from env.tasks import TASKS
    task = TASKS[request.task_id]
    return ResetResponse(
        session_id=sid,
        observation=obs,
        info={"task_name": task["name"], "difficulty": task["difficulty"]},
    )


@app.post("/step", response_model=StepResult)
def step(request: StepRequest):
    env = _get_session(request.session_id)
    try:
        return env.step(request.action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=StateResponse)
def state(session_id: str = Query(..., description="Session ID from /reset")):
    env = _get_session(session_id)
    try:
        return env.state()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Clean up a finished session to free memory."""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"deleted": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "7860"))   # 7860 = HF Spaces default
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
