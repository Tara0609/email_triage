"""
Baseline inference script for Email Triage OpenEnv.

Uses OpenAI function calling (tools API) for reliable structured output,
with a plain-JSON fallback for models that do not support tool calling.
Emits structured stdout logs in strict [START] / [STEP] / [END] format.

Required environment variables:
  API_BASE_URL   e.g. https://api.openai.com/v1
  MODEL_NAME     e.g. gpt-4o
  HF_TOKEN       Your API key
  ENV_URL        Environment server URL (default: http://localhost:7860)
"""

import os
import sys
import json
import re
import time
from typing import Tuple

import requests
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config  (all values come from environment variables)
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o")
HF_TOKEN     = os.environ.get("HF_TOKEN")          # NO default — must be set explicitly
ENV_URL      = os.environ.get("ENV_URL", "http://localhost:7860")

client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

TASKS = ["task_1", "task_2", "task_3", "task_4"]

# ---------------------------------------------------------------------------
# Structured log format
# Evaluator parses these lines — do NOT change field names or ordering.
# ---------------------------------------------------------------------------

def log_start(task_id: str, task_description: str) -> None:
    print(json.dumps({
        "event": "START",
        "task_id": task_id,
        "task_description": task_description,
    }), flush=True)


def log_step(
    task_id: str,
    step: int,
    action: dict,
    reward: float,
    done: bool,
    info: dict,
) -> None:
    print(json.dumps({
        "event": "STEP",
        "task_id": task_id,
        "step": step,
        "action": action,
        "reward": reward,
        "done": done,
        "info": info,
    }), flush=True)


def log_end(task_id: str, final_score: float, total_steps: int) -> None:
    print(json.dumps({
        "event": "END",
        "task_id": task_id,
        "final_score": final_score,
        "total_steps": total_steps,
    }), flush=True)


# ---------------------------------------------------------------------------
# Environment API helpers
# ---------------------------------------------------------------------------

def env_reset(task_id: str) -> dict:
    r = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=30)
    r.raise_for_status()
    return r.json()


def env_step(session_id: str, action: dict) -> dict:
    r = requests.post(
        f"{ENV_URL}/step",
        json={"session_id": session_id, "action": action},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# OpenAI tool schemas — one per task action_type
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = {
    "classify_urgency": [{
        "type": "function",
        "function": {
            "name": "classify_urgency",
            "description": "Classify the urgency of one email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {"type": "string"},
                    "urgency":  {"type": "string", "enum": ["urgent", "normal", "low"]},
                    "reason":   {"type": "string"},
                },
                "required": ["email_id", "urgency"],
            },
        },
    }],
    "extract_actions": [{
        "type": "function",
        "function": {
            "name": "extract_actions",
            "description": "Extract all action items from one email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {"type": "string"},
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "assignee":    {"type": "string"},
                                "due_date":    {"type": "string"},
                            },
                            "required": ["description", "assignee"],
                        },
                    },
                    "summary": {"type": "string"},
                },
                "required": ["email_id", "action_items", "summary"],
            },
        },
    }],
    "full_triage": [{
        "type": "function",
        "function": {
            "name": "full_triage",
            "description": "Perform full triage on one complex email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id":   {"type": "string"},
                    "urgency":    {"type": "string", "enum": ["urgent", "normal", "low"]},
                    "department": {
                        "type": "string",
                        "enum": ["engineering", "sales", "support", "hr",
                                 "finance", "legal", "management"],
                    },
                    "reply_subject":  {"type": "string"},
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "assignee":    {"type": "string"},
                                "due_date":    {"type": "string"},
                            },
                            "required": ["description", "assignee"],
                        },
                    },
                    "requires_immediate_response": {"type": "boolean"},
                    "summary": {"type": "string"},
                },
                "required": [
                    "email_id", "urgency", "department", "reply_subject",
                    "action_items", "requires_immediate_response", "summary",
                ],
            },
        },
    }],
    "prioritize_emails": [{
        "type": "function",
        "function": {
            "name": "prioritize_emails",
            "description": "Rank ALL emails from most urgent to least urgent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ranked_email_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "All email IDs, most-urgent first",
                    },
                    "reasoning": {"type": "string"},
                },
                "required": ["ranked_email_ids"],
            },
        },
    }],
}

# Plain-JSON fallback prompts (used when tool calling is unavailable)
JSON_FALLBACK_PROMPTS = {
    "classify_urgency": (
        'Respond ONLY with this JSON (no markdown, no extra text):\n'
        '{"email_id":"<id>","urgency":"<urgent|normal|low>","reason":"<one sentence>"}'
    ),
    "extract_actions": (
        'Respond ONLY with this JSON (no markdown, no extra text):\n'
        '{"email_id":"<id>","action_items":[{"description":"<task>","assignee":"<who>","due_date":"<date or null>"}],"summary":"<brief>"}'
    ),
    "full_triage": (
        'Respond ONLY with this JSON (no markdown, no extra text):\n'
        '{"email_id":"<id>","urgency":"<urgent|normal|low>","department":"<engineering|sales|support|hr|finance|legal|management>","reply_subject":"<subject>","action_items":[{"description":"<task>","assignee":"<who>","due_date":"<date or null>"}],"requires_immediate_response":<true|false>,"summary":"<brief>"}'
    ),
    "prioritize_emails": (
        'Respond ONLY with this JSON (no markdown, no extra text):\n'
        '{"ranked_email_ids":["<id1>","<id2>",...],"reasoning":"<brief>"}'
    ),
}


# ---------------------------------------------------------------------------
# LLM call  — tool calling with plain-JSON fallback
# ---------------------------------------------------------------------------

def call_llm(messages: list, action_type: str, retries: int = 3) -> dict:
    """
    Primary path: OpenAI function/tool calling.
    Fallback: plain-text JSON response if tool calling fails or is unsupported.
    """
    tools = TOOL_SCHEMAS[action_type]

    # --- Primary: tool calling ---
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": action_type}},
                temperature=0.0,
                max_tokens=1024,
            )
            tool_call = resp.choices[0].message.tool_calls[0]
            return json.loads(tool_call.function.arguments)
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    # --- Fallback: plain JSON ---
    print(f"  [WARN] Tool calling failed for {action_type}. Trying JSON fallback.",
          file=sys.stderr, flush=True)
    fallback_hint = JSON_FALLBACK_PROMPTS[action_type]
    fallback_messages = messages + [{"role": "user", "content": fallback_hint}]
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=fallback_messages,
                temperature=0.0,
                max_tokens=1024,
            )
            content = resp.choices[0].message.content.strip()
            # Strip markdown code fences if present
            content = re.sub(r"^```[a-z]*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    print(f"  [ERROR] Both tool calling and JSON fallback failed for {action_type}.",
          file=sys.stderr, flush=True)
    return {}


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "classify_urgency": (
        "You are an expert email triage assistant for a tech company. "
        "Classify each email as 'urgent' (business-critical, act RIGHT NOW), "
        "'normal' (act within 1-2 business days), or 'low' (no time pressure)."
    ),
    "extract_actions": (
        "You are a senior executive assistant. Extract EVERY concrete action item "
        "from the email — things someone must actually do. Always name exactly WHO "
        "is responsible. Include due dates when mentioned."
    ),
    "full_triage": (
        "You are a chief of staff handling complex multi-stakeholder emails. "
        "Determine urgency, route to the single most responsible department, "
        "write a clear reply subject, extract all action items with owners and due dates, "
        "and flag if an immediate response is needed."
    ),
    "prioritize_emails": (
        "You are a chief of staff who just received multiple emails simultaneously. "
        "Rank them ALL from most to least urgent considering: financial impact, "
        "time sensitivity, number of people affected, legal/compliance risk, "
        "and reversibility of consequences."
    ),
}


def format_email(email: dict) -> str:
    parts = [
        f"Email ID: {email['id']}",
        f"Subject:  {email['subject']}",
        f"From:     {email['sender']} <{email['sender_email']}>",
        f"Time:     {email['timestamp']}",
    ]
    if email.get("thread_context"):
        parts.append(
            f"\n--- Thread context ---\n{email['thread_context']}\n--- End context ---"
        )
    parts.append(f"\nBody:\n{email['body']}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Per-email agent loop  (task_1 / task_2 / task_3)
# ---------------------------------------------------------------------------

def run_per_email_task(task_id: str, obs: dict, session_id: str) -> Tuple[float, int]:
    action_type = obs["context"]["action_type"]
    emails      = obs["emails"]
    system      = SYSTEM_PROMPTS[action_type]
    step_count  = 0
    final_score = 0.0

    log_start(task_id, obs["task_description"])

    for email in emails:
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": format_email(email)},
        ]
        action = call_llm(messages, action_type)

        # Always stamp the correct email_id (safety net)
        action["email_id"] = email["id"]

        result = env_step(session_id, action)
        step_count += 1
        reward = result["reward"]
        done   = result["done"]
        info   = result.get("info", {})

        log_step(task_id, step_count, action, reward, done, info)

        if done:
            final_score = info.get("final_score", {}).get("score", reward)
            break

    return final_score, step_count


# ---------------------------------------------------------------------------
# Single-action ranking loop  (task_4)
# ---------------------------------------------------------------------------

def run_ranking_task(task_id: str, obs: dict, session_id: str) -> Tuple[float, int]:
    emails      = obs["emails"]
    system      = SYSTEM_PROMPTS["prioritize_emails"]
    final_score = 0.0

    log_start(task_id, obs["task_description"])

    # Present all emails in one prompt
    email_summaries = "\n\n".join(
        f"[{e['id']}] {e['subject']}\n"
        f"From: {e['sender']} | {e['timestamp']}\n"
        f"{e['body'][:300]}..."
        for e in emails
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"You received {len(emails)} emails simultaneously. "
                f"Rank ALL {len(emails)} by priority (most urgent first).\n\n"
                f"{email_summaries}"
            ),
        },
    ]

    action = call_llm(messages, "prioritize_emails")

    # Guarantee every email ID is present (append any omitted ones at end)
    all_ids = [e["id"] for e in emails]
    ranked  = action.get("ranked_email_ids", [])
    missing = [eid for eid in all_ids if eid not in ranked]
    action["ranked_email_ids"] = ranked + missing

    result = env_step(session_id, action)
    step_count = 1
    reward = result["reward"]
    done   = result["done"]
    info   = result.get("info", {})

    log_step(task_id, step_count, action, reward, done, info)

    if done:
        final_score = info.get("final_score", {}).get("score", reward)

    return final_score, step_count


# ---------------------------------------------------------------------------
# Master task runner
# ---------------------------------------------------------------------------

def run_task(task_id: str) -> float:
    reset_resp  = env_reset(task_id)
    session_id  = reset_resp["session_id"]
    obs         = reset_resp["observation"]
    action_type = obs["context"]["action_type"]

    if action_type == "prioritize_emails":
        final_score, step_count = run_ranking_task(task_id, obs, session_id)
    else:
        final_score, step_count = run_per_email_task(task_id, obs, session_id)

    log_end(task_id, final_score, step_count)
    return final_score


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # Validate required environment variables (only HF_TOKEN has no default)
    if not os.environ.get("HF_TOKEN"):
        print(json.dumps({"error": "missing_env_vars", "vars": ["HF_TOKEN"]}),
              file=sys.stderr, flush=True)
        sys.exit(1)

    # Wait for environment server to be ready (up to 60 s)
    print(f"Connecting to environment at {ENV_URL} ...", flush=True)
    for attempt in range(30):
        try:
            r = requests.get(f"{ENV_URL}/health", timeout=5)
            if r.status_code == 200:
                print(f"Environment ready. {r.json()}", flush=True)
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        print("ERROR: Environment server not reachable after 60s.", file=sys.stderr)
        sys.exit(1)

    scores: dict = {}
    for task_id in TASKS:
        print(f"\n{'='*60}", flush=True)
        print(f"Running {task_id}", flush=True)
        print("="*60, flush=True)
        score = run_task(task_id)
        scores[task_id] = score
        print(f"[RESULT] {task_id}: {score:.4f}", flush=True)

    # Final summary
    print("\n" + "="*60, flush=True)
    print("FINAL SCORES:", flush=True)
    for task_id, score in scores.items():
        print(f"  {task_id}: {score:.4f}", flush=True)
    avg = sum(scores.values()) / len(scores)
    print(f"  AVERAGE:  {avg:.4f}", flush=True)
    print("="*60, flush=True)


if __name__ == "__main__":
    main()
