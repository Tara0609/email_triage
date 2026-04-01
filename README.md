# Email Triage — OpenEnv Environment

An OpenEnv-compliant environment for evaluating AI agents on real-world corporate email triage tasks.

---

## Environment Description

Agents receive batches of corporate emails and must perform triage operations across three difficulty levels:

| Task | Difficulty | Description | Emails |
|------|-----------|-------------|--------|
| `task_1` | Easy | Classify each email as `urgent`, `normal`, or `low` priority | 6 |
| `task_2` | Medium | Extract all action items with assignees from emails | 3 |
| `task_3` | Hard | Full triage: classify + route to department + draft reply subject + extract actions with due dates | 3 |

---

## Observation Space

```json
{
  "task_id": "task_1",
  "task_description": "Natural language instructions for the agent",
  "emails": [
    {
      "id": "e001",
      "subject": "CRITICAL: Production database down",
      "sender": "Alice Chen",
      "sender_email": "alice.chen@company.com",
      "body": "...",
      "timestamp": "2024-01-15T09:03:00Z",
      "thread_id": "thread_001",
      "attachments": []
    }
  ],
  "context": {
    "action_type": "classify_urgency",
    "difficulty": "easy",
    "num_emails": 6
  },
  "step_count": 0,
  "max_steps": 10
}
```

---

## Action Space

Actions are JSON objects. The schema depends on `observation.context.action_type`:

### Task 1 — `classify_urgency`
```json
{
  "email_id": "e001",
  "urgency": "urgent",
  "reason": "Production database down, losing $5k/minute"
}
```

### Task 2 — `extract_actions`
```json
{
  "email_id": "e004",
  "action_items": [
    {"description": "Book conference room for Tuesday 2pm", "assignee": "Sarah", "due_date": "2024-01-20"},
    {"description": "Review draft roadmap doc and add comments", "assignee": "engineering leads", "due_date": "2024-01-20"}
  ],
  "summary": "Q1 roadmap review scheduled for next Tuesday at 2pm"
}
```

### Task 3 — `full_triage`
```json
{
  "email_id": "e010",
  "urgency": "urgent",
  "department": "legal",
  "reply_subject": "Re: GDPR Audit Findings - Remediation Plan",
  "action_items": [
    {"description": "Review incomplete EU consent records (50k)", "assignee": "Legal", "due_date": "2024-01-22"},
    {"description": "Implement automated data deletion in CRM", "assignee": "Engineering", "due_date": "2024-02-15"}
  ],
  "requires_immediate_response": true,
  "summary": "GDPR audit found 3 critical findings requiring Legal, Engineering, and Marketing action"
}
```

---

## Reward Function

- **Range:** 0.0 – 1.0
- **Partial credit:** Yes — intermediate steps return small progress signals
- **Final scoring:** Computed by task-specific grader on episode completion

| Task | Scoring Breakdown |
|------|-------------------|
| task_1 | 1.0 per correct / 0.3 off-by-one / 0.0 wrong — averaged over 6 emails |
| task_2 | 0.4 assignee recall + 0.4 keyword coverage + 0.2 summary quality — averaged over 3 |
| task_3 | 0.25 urgency + 0.25 department + 0.20 action items + 0.15 reply subject + 0.15 immediate flag |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reset` | Start new episode. Body: `{"task_id": "task_1"}` |
| `POST` | `/step` | Submit action. Body: `{"action": {...}}` |
| `GET` | `/state` | Get current episode state |
| `GET` | `/tasks` | List all available tasks |
| `GET` | `/health` | Health check |

---

## Setup & Running Locally

### Prerequisites
- Python 3.11+
- Docker (for containerized run)

### Local Python

```bash
# Install dependencies
pip install -r requirements.txt

# Start the environment server
python app.py
# Server runs at http://localhost:7860
```

### Docker

```bash
docker build -t email-triage .
docker run -p 7860:7860 email-triage
```

---

## Running Inference

Set required environment variables:

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export HF_TOKEN="your-api-key-here"
export ENV_URL="http://localhost:7860"   # or your HF Space URL
```

Run the baseline inference script:

```bash
python inference.py
```

Expected output (per task):
```json
{"event": "START", "task_id": "task_1", "task_description": "..."}
{"event": "STEP", "task_id": "task_1", "step": 1, "action": {...}, "reward": 0.0083, "done": false, "info": {...}}
...
{"event": "END", "task_id": "task_1", "final_score": 0.8833, "total_steps": 6}
```

### Baseline Scores (GPT-4o)

| Task | Score |
|------|-------|
| task_1 (easy) | ~0.88 |
| task_2 (medium) | ~0.72 |
| task_3 (hard) | ~0.65 |
| **Average** | **~0.75** |

---

## Pre-submission Checklist

- [ ] `python app.py` starts without errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `POST /reset` with each task_id returns valid observation
- [ ] `python inference.py` completes without error and prints scores
- [ ] `docker build -t email-triage .` succeeds
- [ ] `docker run -p 7860:7860 email-triage` serves requests correctly
- [ ] All 3 tasks produce scores in [0.0, 1.0]

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | LLM API endpoint (e.g., `https://api.openai.com/v1`) |
| `MODEL_NAME` | Model identifier (e.g., `gpt-4o`) |
| `HF_TOKEN` | Hugging Face / API key for authentication |
| `ENV_URL` | URL of the running environment server (default: `http://localhost:7860`) |
