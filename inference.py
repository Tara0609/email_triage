"""
Baseline inference script for Email Triage OpenEnv.

Uses the OpenAI client pointed at API_BASE_URL to call MODEL_NAME.
Emits structured stdout logs in [START] / [STEP] / [END] format.

Required environment variables:
  API_BASE_URL   e.g. https://api.openai.com/v1  or  https://api.anthropic.com/v1
  MODEL_NAME     e.g. gpt-4o  or  claude-sonnet-4-6
  HF_TOKEN       Your Hugging Face / API key
"""

import os
import sys
import json
import time
import requests
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
ENV_URL      = os.environ.get("ENV_URL", "http://localhost:7860")

client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

TASKS = ["task_1", "task_2", "task_3"]

# ---------------------------------------------------------------------------
# Logging helpers (strict format required by evaluator)
# ---------------------------------------------------------------------------

def log_start(task_id: str, task_description: str):
    print(json.dumps({
        "event": "START",
        "task_id": task_id,
        "task_description": task_description,
    }), flush=True)


def log_step(task_id: str, step: int, action: dict, reward: float, done: bool, info: dict):
    print(json.dumps({
        "event": "STEP",
        "task_id": task_id,
        "step": step,
        "action": action,
        "reward": reward,
        "done": done,
        "info": info,
    }), flush=True)


def log_end(task_id: str, final_score: float, total_steps: int):
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


def env_step(action: dict) -> dict:
    r = requests.post(f"{ENV_URL}/step", json={"action": action}, timeout=30)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Prompts per task type
# ---------------------------------------------------------------------------

def build_system_prompt(action_type: str) -> str:
    if action_type == "classify_urgency":
        return (
            "You are an expert email triage assistant. Classify the urgency of emails.\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            '{"email_id": "<id>", "urgency": "<urgent|normal|low>", "reason": "<brief reason>"}\n'
            "Do not add any other text."
        )
    elif action_type == "extract_actions":
        return (
            "You are an expert executive assistant. Extract all action items from emails.\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            '{"email_id": "<id>", "action_items": [{"description": "<task>", "assignee": "<person/team>", "due_date": "<date or null>"}], "summary": "<brief summary>"}\n'
            "Do not add any other text."
        )
    elif action_type == "full_triage":
        return (
            "You are a senior operations manager performing full email triage.\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            '{"email_id": "<id>", "urgency": "<urgent|normal|low>", '
            '"department": "<engineering|sales|support|hr|finance|legal|management>", '
            '"reply_subject": "<subject for your reply>", '
            '"action_items": [{"description": "<task>", "assignee": "<person/team>", "due_date": "<date or null>"}], '
            '"requires_immediate_response": <true|false>, '
            '"summary": "<concise summary>"}\n'
            "Do not add any other text."
        )
    return "You are a helpful assistant."


def build_user_prompt(email: dict, action_type: str) -> str:
    return (
        f"Email ID: {email['id']}\n"
        f"Subject: {email['subject']}\n"
        f"From: {email['sender']} <{email['sender_email']}>\n"
        f"Timestamp: {email['timestamp']}\n\n"
        f"Body:\n{email['body']}\n\n"
        f"Please perform the required action ({action_type}) for this email."
    )


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def call_llm(system: str, user: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return ""


def run_task(task_id: str) -> float:
    # Reset environment
    reset_resp = env_reset(task_id)
    obs = reset_resp["observation"]
    action_type = obs["context"]["action_type"]
    task_description = obs["task_description"]
    emails = obs["emails"]

    log_start(task_id, task_description)

    system_prompt = build_system_prompt(action_type)
    step_count = 0
    final_score = 0.0

    for email in emails:
        user_prompt = build_user_prompt(email, action_type)

        # Call LLM
        raw_response = call_llm(system_prompt, user_prompt)

        # Parse JSON action
        try:
            action = json.loads(raw_response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if match:
                try:
                    action = json.loads(match.group())
                except json.JSONDecodeError:
                    action = {"email_id": email["id"], "_parse_error": raw_response[:200]}
            else:
                action = {"email_id": email["id"], "_parse_error": raw_response[:200]}

        # Ensure email_id is set
        if "email_id" not in action:
            action["email_id"] = email["id"]

        # Submit to environment
        step_result = env_step(action)
        step_count += 1
        reward = step_result["reward"]
        done = step_result["done"]
        info = step_result.get("info", {})

        log_step(task_id, step_count, action, reward, done, info)

        if done:
            final_score = info.get("final_score", {}).get("score", reward)
            break

    log_end(task_id, final_score, step_count)
    return final_score


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Validate env vars
    missing = [v for v in ["API_BASE_URL", "MODEL_NAME", "HF_TOKEN"] if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing environment variables: {missing}", file=sys.stderr)
        sys.exit(1)

    # Wait for environment server to be ready
    for attempt in range(30):
        try:
            r = requests.get(f"{ENV_URL}/health", timeout=5)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        print("ERROR: Environment server not reachable", file=sys.stderr)
        sys.exit(1)

    scores = {}
    for task_id in TASKS:
        print(f"\n{'='*60}", flush=True)
        print(f"Running {task_id}", flush=True)
        print('='*60, flush=True)
        score = run_task(task_id)
        scores[task_id] = score
        print(f"[RESULT] {task_id}: {score:.4f}", flush=True)

    print("\n" + "="*60, flush=True)
    print("FINAL SCORES:", flush=True)
    for task_id, score in scores.items():
        print(f"  {task_id}: {score:.4f}", flush=True)
    avg = sum(scores.values()) / len(scores)
    print(f"  AVERAGE: {avg:.4f}", flush=True)
    print("="*60, flush=True)


if __name__ == "__main__":
    main()
