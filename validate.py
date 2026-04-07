"""
Pre-submission validation script for Email Triage OpenEnv.

Checks:
  1. Environment server is reachable (/health returns 200)
  2. /tasks lists all 4 tasks
  3. Each task: reset → submit perfect actions → score in [0.0, 1.0]
  4. Session isolation (two concurrent sessions don't interfere)
  5. openenv.yaml has required fields
  6. inference.py exists in root

Usage:
  python validate.py                        (assumes server on localhost:7861)
  ENV_URL=http://... python validate.py
"""

import os
import sys
import json
import requests

ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = []


def check(name: str, passed: bool, detail: str = ""):
    icon = PASS if passed else FAIL
    msg = f"{icon} {name}"
    if detail:
        msg += f"  ->  {detail}"
    print(msg)
    results.append((name, passed))


# ---------------------------------------------------------------------------
# 1. Health check
# ---------------------------------------------------------------------------
print("\n=== 1. Server Health ===")
try:
    r = requests.get(f"{ENV_URL}/health", timeout=10)
    check("GET /health returns 200", r.status_code == 200, str(r.json()))
except Exception as e:
    check("GET /health returns 200", False, str(e))
    print(f"\n{FAIL} Server not reachable at {ENV_URL}. Start it first: python app.py")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 2. Task listing
# ---------------------------------------------------------------------------
print("\n=== 2. Task Listing ===")
r = requests.get(f"{ENV_URL}/tasks", timeout=10)
check("GET /tasks returns 200", r.status_code == 200)
tasks_data = r.json().get("tasks", [])
task_ids = [t["id"] for t in tasks_data]
for tid in ["task_1", "task_2", "task_3", "task_4"]:
    check(f"  {tid} present", tid in task_ids)

# ---------------------------------------------------------------------------
# 3. Per-task: reset + perfect actions + valid score
# ---------------------------------------------------------------------------
print("\n=== 3. Task Grading (perfect actions) ===")

PERFECT_ACTIONS = {
    "task_1": [
        {"email_id": "e001", "urgency": "urgent",  "reason": "prod down"},
        {"email_id": "e004", "urgency": "normal",  "reason": "roadmap review"},
        {"email_id": "e007", "urgency": "low",     "reason": "photos"},
        {"email_id": "e002", "urgency": "urgent",  "reason": "security breach"},
        {"email_id": "e008", "urgency": "low",     "reason": "training reminder"},
        {"email_id": "e009", "urgency": "low",     "reason": "ping pong"},
    ],
    "task_2": [
        {
            "email_id": "e004",
            "action_items": [
                {"description": "Book conference room for Tuesday 2pm roadmap review", "assignee": "Sarah", "due_date": "2024-01-20"},
                {"description": "Prepare Q2 capacity estimates for roadmap review", "assignee": "engineering leads", "due_date": "2024-01-20"},
                {"description": "Review draft roadmap doc and add OKR comments", "assignee": "engineering", "due_date": "2024-01-20"},
            ],
            "summary": "Q1 roadmap review scheduled for next Tuesday at 2pm, preparation required from Sarah and engineering leads.",
        },
        {
            "email_id": "e005",
            "action_items": [
                {"description": "Provision laptop MacBook Pro 14 inch for Tom Wilson", "assignee": "IT", "due_date": "2024-01-20"},
                {"description": "Set up GitHub, Slack, Jira and Confluence accounts", "assignee": "IT", "due_date": "2024-01-20"},
                {"description": "Assign onboarding buddy and prepare 30-60-90 day plan", "assignee": "Lisa Johnson", "due_date": "2024-01-20"},
            ],
            "summary": "Tom Wilson joins as Senior Backend Engineer on Monday. IT must provision laptop and accounts; Lisa Johnson must set up onboarding plan.",
        },
        {
            "email_id": "e006",
            "action_items": [
                {"description": "Process AWS invoice payment of $12,400 due Jan 31", "assignee": "Finance", "due_date": "2024-01-31"},
                {"description": "Review EC2 and RDS cost spike in December", "assignee": "DevOps", "due_date": "2024-01-31"},
            ],
            "summary": "AWS December invoice for $12,400 (23% increase). Finance to pay, DevOps to review cost spike.",
        },
    ],
    "task_3": [
        {
            "email_id": "e010",
            "urgency": "urgent",
            "department": "legal",
            "reply_subject": "Re: GDPR Audit Findings - Remediation Plan Received",
            "action_items": [
                {"description": "Review and remediate incomplete EU consent records (50k)", "assignee": "Legal", "due_date": "2024-01-22"},
                {"description": "Implement automated data deletion in CRM system", "assignee": "Engineering", "due_date": "2024-02-15"},
                {"description": "Update privacy policy to reflect current data processing", "assignee": "Legal", "due_date": "2024-01-29"},
            ],
            "requires_immediate_response": True,
            "summary": "GDPR audit identified 3 critical findings. Legal, Engineering, and Marketing must act within defined deadlines to avoid fines.",
        },
        {
            "email_id": "e011",
            "urgency": "urgent",
            "department": "sales",
            "reply_subject": "Re: TechCorp Enterprise Deal - Action Items Assigned",
            "action_items": [
                {"description": "CEO/CTO sign-off on custom SLA terms", "assignee": "management", "due_date": "2024-01-16"},
                {"description": "Legal review and approve modified MSA", "assignee": "Legal", "due_date": "2024-01-17"},
                {"description": "Set up net-60 annual billing structure", "assignee": "Finance", "due_date": "2024-01-19"},
                {"description": "Confirm SAML 2.0 SSO integration feasibility", "assignee": "Engineering", "due_date": "2024-01-16"},
            ],
            "requires_immediate_response": True,
            "summary": "$500K TechCorp deal closing this week. Requires exec sign-off, legal, finance, and engineering to act immediately.",
        },
        {
            "email_id": "e003",
            "urgency": "urgent",
            "department": "sales",
            "reply_subject": "Re: Contract Renewal - Calling You Immediately",
            "action_items": [
                {"description": "Call Marcus Rodriguez immediately at +1-555-0123", "assignee": "Sarah", "due_date": "2024-01-15"},
                {"description": "Prepare and send signed renewal contract by 5pm EST", "assignee": "sales", "due_date": "2024-01-15"},
            ],
            "requires_immediate_response": True,
            "summary": "$2M annual contract expires tonight. Sarah must call client immediately and send signed docs by 5pm EST.",
        },
    ],
    "task_4": [
        {
            "ranked_email_ids": ["e001", "e002", "e012", "e003", "e013", "e004", "e014", "e008", "e015", "e007"],
            "reasoning": "Ranked by financial impact, time sensitivity, and reversibility.",
        }
    ],
}


for task_info in tasks_data:
    tid = task_info["id"]
    actions = PERFECT_ACTIONS.get(tid, [])
    if not actions:
        check(f"{tid}: perfect actions defined", False, "no test actions")
        continue

    # Reset
    r = requests.post(f"{ENV_URL}/reset", json={"task_id": tid}, timeout=15)
    check(f"{tid}: POST /reset -> 200", r.status_code == 200)
    if r.status_code != 200:
        continue

    session_id = r.json()["session_id"]
    check(f"{tid}: session_id returned", bool(session_id), session_id[:8] + "...")

    # Submit actions
    final_reward = 0.0
    for action in actions:
        sr = requests.post(
            f"{ENV_URL}/step",
            json={"session_id": session_id, "action": action},
            timeout=15,
        )
        if sr.status_code != 200:
            check(f"{tid}: step returned 200", False, sr.text[:100])
            break
        step_data = sr.json()
        final_reward = step_data["reward"]
        if step_data["done"]:
            fs = step_data["info"].get("final_score", {})
            final_reward = fs.get("score", final_reward)
            break

    check(f"{tid}: score in [0.0, 1.0]", 0.0 <= final_reward <= 1.0, f"score={final_reward:.4f}")
    check(f"{tid}: perfect score >= 0.9", final_reward >= 0.9, f"score={final_reward:.4f}")

# ---------------------------------------------------------------------------
# 4. Session isolation
# ---------------------------------------------------------------------------
print("\n=== 4. Session Isolation ===")
r1 = requests.post(f"{ENV_URL}/reset", json={"task_id": "task_1"}, timeout=10).json()
r2 = requests.post(f"{ENV_URL}/reset", json={"task_id": "task_2"}, timeout=10).json()
s1, s2 = r1["session_id"], r2["session_id"]
check("Two concurrent sessions have different IDs", s1 != s2, f"{s1[:8]} != {s2[:8]}")

# Step session 1 only
requests.post(f"{ENV_URL}/step", json={"session_id": s1, "action": {"email_id": "e001", "urgency": "urgent"}}, timeout=10)
state1 = requests.get(f"{ENV_URL}/state", params={"session_id": s1}, timeout=10).json()
state2 = requests.get(f"{ENV_URL}/state", params={"session_id": s2}, timeout=10).json()
check("Sessions have independent step counts",
      state1["step_count"] != state2["step_count"],
      f"s1={state1['step_count']}, s2={state2['step_count']}")

# ---------------------------------------------------------------------------
# 5. File checks
# ---------------------------------------------------------------------------
print("\n=== 5. Required Files ===")
check("inference.py exists", os.path.isfile("inference.py"))
check("openenv.yaml exists", os.path.isfile("openenv.yaml"))
check("Dockerfile exists",   os.path.isfile("Dockerfile"))
check("requirements.txt exists", os.path.isfile("requirements.txt"))

if os.path.isfile("openenv.yaml"):
    with open("openenv.yaml") as f:
        content = f.read()
    for field in ["name", "version", "tasks", "observation_space", "action_space", "reward"]:
        check(f"  openenv.yaml has '{field}'", field in content)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "="*50)
passed = sum(1 for _, ok in results if ok)
total  = len(results)
print(f"Result: {passed}/{total} checks passed")
if passed == total:
    print("All checks passed -- ready to submit!")
else:
    failed = [name for name, ok in results if not ok]
    print(f"Failed checks: {failed}")
    sys.exit(1)
