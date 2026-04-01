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
    attachments: List[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    description: str
    assignee: str
    due_date: Optional[str] = None


# --- Action Spaces ---

class ClassifyUrgencyAction(BaseModel):
    email_id: str
    urgency: UrgencyLevel
    reason: Optional[str] = None


class ExtractActionsAction(BaseModel):
    email_id: str
    action_items: List[ActionItem]
    summary: str


class FullTriageAction(BaseModel):
    email_id: str
    urgency: UrgencyLevel
    department: Department
    reply_subject: str
    action_items: List[ActionItem]
    requires_immediate_response: bool
    summary: str


# --- Observation Space ---

class EmailObservation(BaseModel):
    task_id: str
    task_description: str
    emails: List[Email]
    context: dict = Field(default_factory=dict)
    step_count: int = 0
    max_steps: int = 10


# --- Step Response ---

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
    observation: EmailObservation
    info: dict = Field(default_factory=dict)
