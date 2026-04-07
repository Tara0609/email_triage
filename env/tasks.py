"""
Task definitions and agent graders for the Email Triage environment.

Tasks:
  task_1 (easy):   Classify urgency of 6 emails
  task_2 (medium): Extract action items from 3 emails
  task_3 (hard):   Full triage of 3 complex multi-department emails
  task_4 (hard):   Rank 10 emails by priority order (Spearman + top-K)
"""

from difflib import SequenceMatcher
from typing import List, Dict, Any
from .models import (
    UrgencyLevel, Department,
    ClassifyUrgencyAction, ExtractActionsAction, FullTriageAction,
    PrioritizeEmailsAction,
)
from .data import (
    EMAILS_BY_ID,
    TASK_1_EMAILS, TASK_2_EMAILS, TASK_3_EMAILS, TASK_4_EMAILS,
)


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
    "e012": UrgencyLevel.urgent,
    "e013": UrgencyLevel.normal,
    "e014": UrgencyLevel.normal,
    "e015": UrgencyLevel.low,
}

DEPARTMENT_GT: Dict[str, Department] = {
    "e003": Department.sales,
    "e010": Department.legal,
    "e011": Department.sales,
}

# True priority order for task_4 (most → least urgent)
PRIORITY_GT: List[str] = [
    "e001",   # prod down — losing $5k/min RIGHT NOW
    "e002",   # security breach — 30-min window to disable accounts
    "e012",   # VIP customer locked out — board meeting in 3 hours
    "e003",   # $2M contract expires midnight TODAY
    "e013",   # board deck due Wednesday noon — tight deadline
    "e004",   # roadmap review next Tuesday — needs prep
    "e014",   # capacity estimates due Jan 24 — 9 days out
    "e008",   # mandatory training due Friday
    "e015",   # team lunch poll — fun, low stakes
    "e007",   # holiday photos — purely informational
]

# Expected assignees per email for task_2
ACTION_ASSIGNEES_GT: Dict[str, List[str]] = {
    "e004": ["sarah", "engineering leads", "engineering"],
    "e005": ["it", "lisa", "lisa johnson"],
    "e006": ["finance", "devops"],
}

# Keywords that must appear in action descriptions for task_2
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
    "task_4": {
        "id": "task_4",
        "name": "Email Priority Ranking",
        "difficulty": "hard",
        "description": (
            "You are a chief of staff. You have received 10 emails simultaneously. "
            "Your job is to rank ALL 10 emails from most urgent to least urgent in a "
            "SINGLE action by calling prioritize_emails with a ranked_email_ids list "
            "(most urgent first) and an optional reasoning string explaining your ordering. "
            "Consider: financial impact, time sensitivity, number of people affected, "
            "legal/compliance risk, and reversibility of consequences."
        ),
        "email_ids": TASK_4_EMAILS,
        "action_type": "prioritize_emails",
        "max_steps": 3,   # one main attempt + 2 retries
    },
}


# ---------------------------------------------------------------------------
# Fuzzy match helper  (difflib, no extra dependency)
# ---------------------------------------------------------------------------

def _fuzzy_match(a: str, b: str, threshold: float = 0.55) -> bool:
    """Return True if strings are similar enough (case-insensitive)."""
    a, b = a.lower().strip(), b.lower().strip()
    if a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= threshold


# ---------------------------------------------------------------------------
# Grader: task_1 — Urgency Classification
# ---------------------------------------------------------------------------

def grade_task_1(actions: List[ClassifyUrgencyAction]) -> Dict[str, Any]:
    """
    1.0  correct label
    0.3  off by one level  (urgent↔normal or normal↔low)
    0.0  wrong
    Final = sum / total
    """
    levels = [UrgencyLevel.urgent, UrgencyLevel.normal, UrgencyLevel.low]
    results: Dict[str, Any] = {}
    correct = 0.0

    for email_id in TASK_1_EMAILS:
        action = next((a for a in actions if a.email_id == email_id), None)
        if action is None:
            results[email_id] = {"score": 0.0, "reason": "no action submitted"}
            continue
        expected = URGENCY_GT[email_id]
        if action.urgency == expected:
            results[email_id] = {"score": 1.0, "reason": "correct"}
            correct += 1.0
        else:
            diff = abs(levels.index(action.urgency) - levels.index(expected))
            partial = 0.3 if diff == 1 else 0.0
            results[email_id] = {
                "score": partial,
                "reason": f"expected {expected.value}, got {action.urgency.value}",
            }
            correct += partial

    final_score = round(correct / len(TASK_1_EMAILS), 4)
    return {
        "score": final_score,
        "per_email": results,
        "correct": correct,
        "total": len(TASK_1_EMAILS),
    }


# ---------------------------------------------------------------------------
# Grader: task_2 — Action Item Extraction
# ---------------------------------------------------------------------------

def grade_task_2(actions: List[ExtractActionsAction]) -> Dict[str, Any]:
    """
    Per email (averaged over 3):
      0.40  assignee recall  — fuzzy-matched against ground truth
      0.40  keyword coverage — keywords in descriptions + summary
      0.20  summary quality  — length > 20 chars
    """
    results: Dict[str, Any] = {}
    total_score = 0.0

    for email_id in TASK_2_EMAILS:
        action = next((a for a in actions if a.email_id == email_id), None)
        if action is None:
            results[email_id] = {"score": 0.0, "reason": "no action submitted"}
            continue

        email_score = 0.0
        breakdown: Dict[str, Any] = {}

        # --- Assignee recall (fuzzy) ---
        expected_assignees = ACTION_ASSIGNEES_GT.get(email_id, [])
        found_assignees = [ai.assignee.lower() for ai in action.action_items]

        assignee_hits = sum(
            1 for ea in expected_assignees
            if any(_fuzzy_match(ea, fa) for fa in found_assignees)
        )
        assignee_score = min(1.0, assignee_hits / max(len(expected_assignees), 1))
        email_score += 0.40 * assignee_score
        breakdown["assignee_score"] = round(assignee_score, 3)

        # --- Keyword coverage ---
        expected_kws = ACTION_KEYWORDS_GT.get(email_id, [])
        all_text = (
            " ".join(ai.description.lower() for ai in action.action_items)
            + " " + action.summary.lower()
        )
        kw_hits = sum(1 for kw in expected_kws if kw in all_text)
        kw_score = min(1.0, kw_hits / max(len(expected_kws), 1))
        email_score += 0.40 * kw_score
        breakdown["keyword_score"] = round(kw_score, 3)

        # --- Summary quality ---
        summary_score = 1.0 if len(action.summary.strip()) > 20 else 0.0
        email_score += 0.20 * summary_score
        breakdown["summary_score"] = summary_score

        results[email_id] = {"score": round(email_score, 4), "breakdown": breakdown}
        total_score += email_score

    final_score = round(total_score / len(TASK_2_EMAILS), 4)
    return {"score": final_score, "per_email": results}


# ---------------------------------------------------------------------------
# Grader: task_3 — Full Email Triage
# ---------------------------------------------------------------------------

def grade_task_3(actions: List[FullTriageAction]) -> Dict[str, Any]:
    """
    Per email (averaged over 3):
      0.25  correct urgency
      0.25  correct department
      0.20  action items quality (count ≥2, assignees, due dates)
      0.15  reply_subject descriptive (>10 chars)
      0.15  requires_immediate_response correct
    """
    IMMEDIATE_GT = {"e003": True, "e010": True, "e011": True}
    results: Dict[str, Any] = {}
    total_score = 0.0

    for email_id in TASK_3_EMAILS:
        action = next((a for a in actions if a.email_id == email_id), None)
        if action is None:
            results[email_id] = {"score": 0.0, "reason": "no action submitted"}
            continue

        email_score = 0.0
        breakdown: Dict[str, Any] = {}

        # Urgency
        u_score = 1.0 if action.urgency == URGENCY_GT.get(email_id) else 0.0
        email_score += 0.25 * u_score
        breakdown["urgency_score"] = u_score

        # Department
        d_score = 1.0 if action.department == DEPARTMENT_GT.get(email_id) else 0.0
        email_score += 0.25 * d_score
        breakdown["department_score"] = d_score

        # Action items quality
        n = len(action.action_items)
        all_have_assignees = all(
            len(ai.assignee.strip()) > 0 for ai in action.action_items
        ) if n > 0 else False
        due_dates_count = sum(
            1 for ai in action.action_items
            if ai.due_date and len(ai.due_date.strip()) > 0
        )
        a_score = 0.0
        if n >= 2:          a_score += 0.5
        if all_have_assignees: a_score += 0.3
        if due_dates_count >= 1: a_score += 0.2
        a_score = min(1.0, a_score)
        email_score += 0.20 * a_score
        breakdown["action_items_score"] = round(a_score, 3)

        # Reply subject
        s_score = 1.0 if len(action.reply_subject.strip()) > 10 else 0.0
        email_score += 0.15 * s_score
        breakdown["reply_subject_score"] = s_score

        # Immediate response flag
        expected_imm = IMMEDIATE_GT.get(email_id, False)
        i_score = 1.0 if action.requires_immediate_response == expected_imm else 0.0
        email_score += 0.15 * i_score
        breakdown["immediate_response_score"] = i_score

        results[email_id] = {"score": round(email_score, 4), "breakdown": breakdown}
        total_score += email_score

    final_score = round(total_score / len(TASK_3_EMAILS), 4)
    return {"score": final_score, "per_email": results}


# ---------------------------------------------------------------------------
# Grader: task_4 — Email Priority Ranking
# ---------------------------------------------------------------------------

def _spearman_score(predicted: List[str], true_order: List[str]) -> float:
    """
    Spearman rank correlation, normalized from [-1,1] → [0,1].
    Only scores emails that appear in both lists.
    """
    true_ranks = {eid: i for i, eid in enumerate(true_order)}
    pred_ranks = {eid: i for i, eid in enumerate(predicted)}
    common = [e for e in true_order if e in pred_ranks]
    n = len(common)
    if n <= 1:
        return 0.0
    d_sq = sum((true_ranks[e] - pred_ranks[e]) ** 2 for e in common)
    rho = 1.0 - (6.0 * d_sq) / (n * (n ** 2 - 1))
    return max(0.0, min(1.0, (rho + 1.0) / 2.0))


def _top_k_accuracy(predicted: List[str], true_order: List[str], k: int = 3) -> float:
    """Fraction of top-k true emails that appear in the predicted top-k."""
    true_top = set(true_order[:k])
    pred_top = set(predicted[:k])
    return len(true_top & pred_top) / k


def grade_task_4(actions: List[PrioritizeEmailsAction]) -> Dict[str, Any]:
    """
    Single action grader (agent submits one ranked list).
    Score = 0.65 * spearman + 0.35 * top3_accuracy
    """
    action = actions[-1] if actions else None   # use last submitted (agent may retry)
    if action is None:
        return {"score": 0.0, "reason": "no action submitted"}

    predicted = action.ranked_email_ids
    true_order = PRIORITY_GT

    spearman = _spearman_score(predicted, true_order)
    top3     = _top_k_accuracy(predicted, true_order, k=3)

    final_score = round(0.65 * spearman + 0.35 * top3, 4)

    # Per-position breakdown for transparency
    true_ranks = {eid: i for i, eid in enumerate(true_order)}
    position_errors = {
        eid: abs(true_ranks.get(eid, 9) - predicted.index(eid))
        for eid in predicted
        if eid in true_ranks
    }

    return {
        "score": final_score,
        "spearman_score": round(spearman, 4),
        "top3_accuracy": round(top3, 4),
        "position_errors": position_errors,
        "predicted_order": predicted,
        "true_order": true_order,
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

GRADERS = {
    "task_1": grade_task_1,
    "task_2": grade_task_2,
    "task_3": grade_task_3,
    "task_4": grade_task_4,
}
