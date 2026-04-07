"""
Core Email Triage environment implementing the OpenEnv spec:
  reset(task_id) -> ResetResponse
  step(action)   -> StepResult
  state()        -> StateResponse
"""

from typing import Any, Dict, List, Optional
from .models import (
    EmailObservation, StepResult, StateResponse, ResetResponse,
    ClassifyUrgencyAction, ExtractActionsAction, FullTriageAction,
    PrioritizeEmailsAction,
)
from .data import EMAILS_BY_ID
from .tasks import TASKS, GRADERS


class EmailTriageEnv:
    def __init__(self):
        self._task_id: Optional[str] = None
        self._step_count: int = 0
        self._done: bool = False
        self._cumulative_reward: float = 0.0
        self._submitted_actions: List[Any] = []
        self._current_observation: Optional[EmailObservation] = None

    # ------------------------------------------------------------------
    def reset(self, task_id: str = "task_1") -> EmailObservation:
        if task_id not in TASKS:
            raise ValueError(f"Unknown task_id '{task_id}'. Valid: {list(TASKS.keys())}")

        task = TASKS[task_id]
        self._task_id = task_id
        self._step_count = 0
        self._done = False
        self._cumulative_reward = 0.0
        self._submitted_actions = []

        emails = [EMAILS_BY_ID[eid] for eid in task["email_ids"]]
        obs = EmailObservation(
            task_id=task_id,
            task_description=task["description"],
            emails=emails,
            context={
                "action_type": task["action_type"],
                "difficulty": task["difficulty"],
                "num_emails": len(emails),
            },
            step_count=0,
            max_steps=task["max_steps"],
        )
        self._current_observation = obs
        return obs

    # ------------------------------------------------------------------
    def step(self, action: Dict[str, Any]) -> StepResult:
        if self._task_id is None:
            raise RuntimeError("Call reset() before step()")
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        task = TASKS[self._task_id]
        self._step_count += 1
        action_type = task["action_type"]

        parsed = self._parse_action(action_type, action)
        if parsed is None:
            reward = 0.0
            info: Dict[str, Any] = {"error": "invalid_action", "details": str(action)[:200]}
        else:
            self._submitted_actions.append(parsed)
            reward, info = self._intermediate_reward()

        # Termination check
        email_ids_covered = self._covered_email_ids()
        task_email_ids = set(task["email_ids"])
        all_covered = task_email_ids.issubset(email_ids_covered)

        if all_covered or self._step_count >= task["max_steps"]:
            self._done = True
            final_result = self._final_grade()
            reward = final_result["score"]
            self._cumulative_reward = reward
            info["final_score"] = final_result
            info["done_reason"] = (
                "all_emails_processed" if all_covered else "max_steps_reached"
            )

        self._current_observation = EmailObservation(
            task_id=self._task_id,
            task_description=task["description"],
            emails=[EMAILS_BY_ID[eid] for eid in task["email_ids"]],
            context={
                "action_type": action_type,
                "difficulty": task["difficulty"],
                "emails_processed": len(email_ids_covered),
                "emails_remaining": len(task_email_ids - email_ids_covered),
            },
            step_count=self._step_count,
            max_steps=task["max_steps"],
        )

        return StepResult(
            observation=self._current_observation,
            reward=reward,
            done=self._done,
            info=info,
        )

    # ------------------------------------------------------------------
    def state(self) -> StateResponse:
        if self._task_id is None:
            raise RuntimeError("Call reset() before state()")
        return StateResponse(
            task_id=self._task_id,
            step_count=self._step_count,
            done=self._done,
            current_observation=self._current_observation,
            cumulative_reward=self._cumulative_reward,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_action(self, action_type: str, raw: Dict[str, Any]) -> Optional[Any]:
        try:
            if action_type == "classify_urgency":
                return ClassifyUrgencyAction(**raw)
            elif action_type == "extract_actions":
                return ExtractActionsAction(**raw)
            elif action_type == "full_triage":
                return FullTriageAction(**raw)
            elif action_type == "prioritize_emails":
                return PrioritizeEmailsAction(**raw)
        except Exception:
            return None

    def _covered_email_ids(self) -> set:
        """Return set of email IDs that have been processed by submitted actions."""
        covered = set()
        for a in self._submitted_actions:
            if hasattr(a, "email_id"):
                covered.add(a.email_id)
            elif hasattr(a, "ranked_email_ids"):
                # task_4 single-action covers all emails in the ranking
                covered.update(a.ranked_email_ids)
        return covered

    def _intermediate_reward(self) -> tuple:
        """
        Compute a real partial grade on submitted actions so far,
        dampened to max 0.1 so it doesn't spoil the final score.
        """
        try:
            partial_result = self._final_grade()
            partial_score = partial_result.get("score", 0.0)
        except Exception:
            partial_score = 0.0

        email_ids_covered = self._covered_email_ids()
        task_email_ids = set(TASKS[self._task_id]["email_ids"])
        progress = len(email_ids_covered) / max(len(task_email_ids), 1)

        # Intermediate reward: real partial score * progress, capped at 0.1
        reward = round(min(0.1, partial_score * progress), 4)
        info = {
            "progress": round(progress, 3),
            "emails_processed": len(email_ids_covered),
            "emails_remaining": len(task_email_ids - email_ids_covered),
            "partial_score": round(partial_score, 4),
        }
        return reward, info

    def _final_grade(self) -> Dict[str, Any]:
        grader = GRADERS[self._task_id]
        return grader(self._submitted_actions)
