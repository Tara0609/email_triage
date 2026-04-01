"""
Task definitions and agent graders for the Email Triage environment.

Tasks:
  task_1 (easy):   Classify urgency of 6 emails
  task_2 (medium): Extract action items from 3 emails
  task_3 (hard):   Full triage of 3 complex multi-department emails
"""

from typing import List, Dict, Any
from .models import (
    Email, UrgencyLevel, Department,
    ClassifyUrgencyAction, ExtractActionsAction, FullTriageAction,
    EmailObservation,
)
from .data import EMAILS_BY_ID, TASK_1_EMAILS, TASK_2_EMAILS, TASK_3_EMAILS


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------

URGENCY_GT: Dict[str, UrgencyLevel] = {
    "e001": UrgencyLevel.urgent,
    "e002": UrgencyLevel.urgent,
    "e003": UrgencyLevel.urgent,
    "e004": UrgencyLevel.normal,
    "e005": UrgencyLevel.normal,
    "e006": UrgencyLevel.normal,
    "e007": UrgencyLevel.low,
    "e008": UrgencyLevel.low,
    "e009": UrgencyLevel.low,
    "e010": UrgencyLevel.urgent,
    "e011": UrgencyLevel.urgent,
}

DEPARTMENT_GT: Dict[str, Department] = {
    "e003": Department.sales,
    "e010": Department.legal,
    "e011": Department.sales,
}

# Expected action-item assignees per email (for partial scoring)
ACTION_ASSIGNEES_GT: Dict[str, List[str]] = {
    "e004": ["sarah", "engineering leads", "engineering"],
    "e005": ["it", "lisa", "lisa johnson"],
    "e006": ["finance", "devops"],
}

# Required action-item keywords per email
ACTION_KEYWORDS_GT: Dict[str, List[str]] = {
    "e004": ["conference room", "roadmap", "okr", "capacity", "q2"],
    "e005": ["laptop", "github", "slack", "jira", "onboarding", "buddy", "provision"],
    "e006": ["invoice", "payment", "finance", "ec2", "rds", "cost"],
}


# ---------------------------------------------------------------------------
# Task metadata
# ---------------------------------------------------------------------------

TASKS = {
    "task_1": {
        "id": "task_1",
        "name": "Email Urgency Classification",
        "difficulty": "easy",
        "description": (
            "You are an email triage assistant. Classify each of the 6 emails below "
            "by urgency level: 'urgent' (requires immediate attention, business-critical), "
            "'normal' (requires action within 1-2 days), or 'low' (informational, can wait). "
            "For each email, call the classify_urgency action with the email_id and urgency level."
        ),
        "email_ids": TASK_1_EMAILS,
        "action_type": "classify_urgency",
        "max_steps": 10,
    },
    "task_2": {
        "id": "task_2",
        "name": "Action Item Extraction",
        "difficulty": "medium",
        "description": (
            "You are an executive assistant. For each of the 3 emails below, extract all "
            "concrete action items (tasks that need to be done by someone). For each email, "
            "call extract_actions with: the email_id, a list of action_items (each with "
            "description and assignee), and a brief summary of the email. "
            "Be specific about WHO is responsible for each action."
        ),
        "email_ids": TASK_2_EMAILS,
        "action_type": "extract_actions",
        "max_steps": 10,
    },
    "task_3": {
        "id": "task_3",
        "name": "Full Email Triage",
        "difficulty": "hard",
        "description": (
            "You are a senior operations manager handling critical business emails. "
            "For each of the 3 complex emails below, perform a full triage by calling "
            "full_triage with: email_id, urgency (urgent/normal/low), department to route to "
            "(engineering/sales/support/hr/finance/legal/management), reply_subject (a clear "
            "subject for your reply), action_items (all tasks with assignees and due dates), "
            "requires_immediate_response (true/false), and a concise summary. "
            "These emails involve multiple stakeholders — be thorough."
        ),
        "email_ids": TASK_3_EMAILS,
        "action_type": "full_triage",
        "max_steps": 15,
    },
}


# ---------------------------------------------------------------------------
# Grader functions
# ---------------------------------------------------------------------------

def grade_task_1(actions: List[ClassifyUrgencyAction]) -> Dict[str, Any]:
    """
    Score: 1 point per correct urgency classification.
    Final score = correct / total (0.0 – 1.0).
    Partial credit via per-email scoring.
    """
    results = {}
    correct = 0
    total = len(TASK_1_EMAILS)

    for email_id in TASK_1_EMAILS:
        action = next((a for a in actions if a.email_id == email_id), None)
        if action is None:
            results[email_id] = {"score": 0.0, "reason": "no action submitted"}
            continue
        expected = URGENCY_GT[email_id]
        if action.urgency == expected:
            results[email_id] = {"score": 1.0, "reason": "correct"}
            correct += 1
        else:
            # Partial credit: off by one level (urgent<->normal or normal<->low) = 0.3
            levels = [UrgencyLevel.urgent, UrgencyLevel.normal, UrgencyLevel.low]
            diff = abs(levels.index(action.urgency) - levels.index(expected))
            partial = 0.3 if diff == 1 else 0.0
            results[email_id] = {
                "score": partial,
                "reason": f"expected {expected}, got {action.urgency}",
            }
            correct += partial

    final_score = round(correct / total, 4)
    return {"score": final_score, "per_email": results, "correct": correct, "total": total}


def grade_task_2(actions: List[ExtractActionsAction]) -> Dict[str, Any]:
    """
    Per-email scoring (weight 1/3 each):
      - 0.4 pts: correct assignees identified (normalized recall)
      - 0.4 pts: relevant keywords covered in descriptions
      - 0.2 pts: summary is non-trivial (>20 chars and not just the subject)
    """
    results = {}
    total_score = 0.0

    for email_id in TASK_2_EMAILS:
        action = next((a for a in actions if a.email_id == email_id), None)
        if action is None:
            results[email_id] = {"score": 0.0, "reason": "no action submitted"}
            continue

        email_score = 0.0
        breakdown = {}

        # Assignee recall
        expected_assignees = ACTION_ASSIGNEES_GT.get(email_id, [])
        found_assignees = [ai.assignee.lower() for ai in action.action_items]
        assignee_hits = sum(
            1 for ea in expected_assignees
            if any(ea in fa or fa in ea for fa in found_assignees)
        )
        assignee_score = min(1.0, assignee_hits / max(len(expected_assignees), 1))
        email_score += 0.4 * assignee_score
        breakdown["assignee_score"] = round(assignee_score, 3)

        # Keyword coverage in action descriptions
        expected_keywords = ACTION_KEYWORDS_GT.get(email_id, [])
        all_desc_text = " ".join(
            ai.description.lower() for ai in action.action_items
        ) + " " + action.summary.lower()
        kw_hits = sum(1 for kw in expected_keywords if kw in all_desc_text)
        kw_score = min(1.0, kw_hits / max(len(expected_keywords), 1))
        email_score += 0.4 * kw_score
        breakdown["keyword_score"] = round(kw_score, 3)

        # Summary quality
        summary_score = 1.0 if len(action.summary) > 20 else 0.0
        email_score += 0.2 * summary_score
        breakdown["summary_score"] = summary_score

        results[email_id] = {"score": round(email_score, 4), "breakdown": breakdown}
        total_score += email_score

    final_score = round(total_score / len(TASK_2_EMAILS), 4)
    return {"score": final_score, "per_email": results}


def grade_task_3(actions: List[FullTriageAction]) -> Dict[str, Any]:
    """
    Per-email scoring (weight 1/3 each):
      - 0.25 pts: correct urgency
      - 0.25 pts: correct department routing
      - 0.20 pts: action items have assignees + due dates
      - 0.15 pts: reply_subject is descriptive (>10 chars)
      - 0.15 pts: requires_immediate_response is correct
    """
    results = {}
    total_score = 0.0

    immediate_response_gt = {
        "e003": True,
        "e010": True,
        "e011": True,
    }

    for email_id in TASK_3_EMAILS:
        action = next((a for a in actions if a.email_id == email_id), None)
        if action is None:
            results[email_id] = {"score": 0.0, "reason": "no action submitted"}
            continue

        email_score = 0.0
        breakdown = {}

        # Urgency
        urgency_correct = action.urgency == URGENCY_GT.get(email_id)
        urgency_score = 1.0 if urgency_correct else 0.0
        email_score += 0.25 * urgency_score
        breakdown["urgency_score"] = urgency_score

        # Department routing
        dept_correct = action.department == DEPARTMENT_GT.get(email_id)
        dept_score = 1.0 if dept_correct else 0.0
        email_score += 0.25 * dept_score
        breakdown["department_score"] = dept_score

        # Action items quality
        has_assignees = all(
            len(ai.assignee.strip()) > 0 for ai in action.action_items
        ) if action.action_items else False
        has_due_dates = sum(
            1 for ai in action.action_items if ai.due_date and len(ai.due_date) > 0
        )
        action_count = len(action.action_items)
        action_score = 0.0
        if action_count >= 2:
            action_score += 0.5
        if has_assignees:
            action_score += 0.3
        if has_due_dates >= 1:
            action_score += 0.2
        action_score = min(1.0, action_score)
        email_score += 0.20 * action_score
        breakdown["action_items_score"] = round(action_score, 3)

        # Reply subject
        subject_score = 1.0 if len(action.reply_subject) > 10 else 0.0
        email_score += 0.15 * subject_score
        breakdown["reply_subject_score"] = subject_score

        # Immediate response flag
        expected_immediate = immediate_response_gt.get(email_id, False)
        immediate_score = 1.0 if action.requires_immediate_response == expected_immediate else 0.0
        email_score += 0.15 * immediate_score
        breakdown["immediate_response_score"] = immediate_score

        results[email_id] = {"score": round(email_score, 4), "breakdown": breakdown}
        total_score += email_score

    final_score = round(total_score / len(TASK_3_EMAILS), 4)
    return {"score": final_score, "per_email": results}


GRADERS = {
    "task_1": grade_task_1,
    "task_2": grade_task_2,
    "task_3": grade_task_3,
}
