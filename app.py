"""
FastAPI server implementing the OpenEnv HTTP spec for Email Triage.

Endpoints:
  POST /reset          - start a new episode
  POST /step           - submit an action
  GET  /state          - inspect current episode state
  GET  /tasks          - list available tasks
  GET  /health         - health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, Optional
import uvicorn

from env import EmailTriageEnv
from env.models import ResetResponse, StepResult, StateResponse

app = FastAPI(
    title="Email Triage OpenEnv",
    description=(
        "An OpenEnv-compliant environment for evaluating AI agents on "
        "real-world email triage tasks: urgency classification, action item extraction, "
        "and full multi-stakeholder email triage."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single global environment instance (stateful per session)
_env = EmailTriageEnv()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_id: str = "task_1"


class StepRequest(BaseModel):
    action: Dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "email-triage-openenv"}


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
def reset(request: ResetRequest):
    try:
        result = _env.reset(task_id=request.task_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResult)
def step(request: StepRequest):
    try:
        result = _env.step(request.action)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=StateResponse)
def state():
    try:
        return _env.state()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=7861, reload=False)
