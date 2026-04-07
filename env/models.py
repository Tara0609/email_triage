from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Any
from enum import Enum


class UrgencyLevel(str, Enum):
    urgent = "urgent"
    normal = "normal"
    low = "low"


class Department(str, Enum):
    engineering = "engineering"
    sales = "sales"
    support = "support"
    hr = "hr"
    finance = "finance"
    legal = "legal"
    management = "management"


class Email(BaseModel):
    id: str
    subject: str
    sender: str
    sender_email: str
    body: str
    timestamp: str
    thread_id: Optional[str] = None
    thread_context: Optional[str] = None   # previous message in thread (if any)
    attachments: List[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    description: str
    assignee: str
    due_date: Optional[str] = None


# ---------------------------------------------------------------------------
# Action Spaces  (one per task type)
# ---------------------------------------------------------------------------

class ClassifyUrgencyAction(BaseModel):
    """task_1 — label one email's urgency"""
    email_id: str
    urgency: UrgencyLevel
    reason: Optional[str] = None


class ExtractActionsAction(BaseModel):
    """task_2 — pull out all to-dos from one email"""
    email_id: str
    action_items: List[ActionItem]
    summary: str


class FullTriageAction(BaseModel):
    """task_3 — full multi-field triage of one complex email"""
    email_id: str
    urgency: UrgencyLevel
    department: Department
    reply_subject: str
    action_items: List[ActionItem]
    requires_immediate_response: bool
    summary: str


class PrioritizeEmailsAction(BaseModel):
    """task_4 — rank ALL emails from most to least urgent in one shot"""
    ranked_email_ids: List[str]            # most urgent first
    reasoning: Optional[str] = None


# ---------------------------------------------------------------------------
# Observation / Response shapes
# ---------------------------------------------------------------------------

class EmailObservation(BaseModel):
    task_id: str
    task_description: str
    emails: List[Email]
    context: dict = Field(default_factory=dict)
    step_count: int = 0
    max_steps: int = 10


class StepResult(BaseModel):
    observation: EmailObservation
    reward: float = Field(ge=0.0, le=1.0)
    done: bool
    info: dict = Field(default_factory=dict)


class StateResponse(BaseModel):
    task_id: str
    step_count: int
    done: bool
    current_observation: EmailObservation
    cumulative_reward: float


class ResetResponse(BaseModel):
    session_id: str
    observation: EmailObservation
    info: dict = Field(default_factory=dict)
