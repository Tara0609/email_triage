# Email Triage — OpenEnv Environment  (v2.0)

An OpenEnv-compliant benchmark for evaluating AI agents on real-world corporate email triage —
urgency classification, action-item extraction, full multi-stakeholder routing, and priority ranking.

---

## Tasks

| Task | Difficulty | What the Agent Does | Emails | Scoring |
|------|-----------|---------------------|--------|---------|
| `task_1` | Easy | Label each email `urgent / normal / low` | 6 | Exact match (0.3 partial credit for off-by-one level) |
| `task_2` | Medium | Extract action items + assignees per email | 3 | 0.4 fuzzy-assignee recall + 0.4 keyword coverage + 0.2 summary quality |
| `task_3` | Hard | Full triage: urgency + dept routing + reply subject + action items + immediate flag | 3 | 5-dimension rubric, averaged |
| `task_4` | Hard | Rank all 10 emails by priority in one shot | 10 | 0.65 × Spearman rank correlation + 0.35 × top-3 accuracy |

---

## What's New in v2

- **Session management** — every `/reset` returns a `session_id`; multiple agents run concurrently without interfering
- **Task 4 — Priority Ranking** — agent ranks 10 emails in a single action; scored with Spearman rank correlation + top-3 accuracy
- **5 new emails** — VIP customer outage (`e012`), board deck deadline (`e013`), capacity planning (`e014`), team lunch poll (`e015`), plus thread context on existing emails
- **Fuzzy assignee matching** — `difflib.SequenceMatcher` so "Lisa" and "Lisa Johnson" both score correctly
- **Real partial rewards** — intermediate steps return actual partial grade × progress (capped at 0.1), not just a dummy counter
- **OpenAI function calling** — inference script uses tool schemas for reliable structured output
- **`validate.py`** — 34-check pre-submission validator (server health, all 4 tasks, session isolation, file checks)

---

## Observation Space

```json
{
  "task_id": "task_4",
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
      "thread_context": null,
      "attachments": []
    }
  ],
  "context": {
    "action_type": "prioritize_emails",
    "difficulty": "hard",
    "num_emails": 10
  },
  "step_count": 0,
  "max_steps": 3
}
```

---

## Action Space

Schema depends on `observation.context.action_type`:

### task_1 — `classify_urgency`
```json
{"email_id": "e001", "urgency": "urgent", "reason": "Production down, losing $5k/min"}
```

### task_2 — `extract_actions`
```json
{
  "email_id": "e004",
  "action_items": [
    {"description": "Book conference room for Tuesday 2pm", "assignee": "Sarah", "due_date": "2024-01-20"}
  ],
  "summary": "Q1 roadmap review next Tuesday, Sarah to book room, leads to prepare OKR updates."
}
```

### task_3 — `full_triage`
```json
{
  "email_id": "e010",
  "urgency": "urgent",
  "department": "legal",
  "reply_subject": "Re: GDPR Audit Findings - Remediation Plan",
  "action_items": [
    {"description": "Review 50k incomplete EU consent records", "assignee": "Legal", "due_date": "2024-01-22"}
  ],
  "requires_immediate_response": true,
  "summary": "GDPR audit: 3 critical findings for Legal, Engineering, Marketing."
}
```

### task_4 — `prioritize_emails`
```json
{
  "ranked_email_ids": ["e001", "e002", "e012", "e003", "e013", "e004", "e014", "e008", "e015", "e007"],
  "reasoning": "Ranked by financial impact, time sensitivity, and reversibility."
}
```

---

## Reward Function

| Phase | Reward |
|-------|--------|
| Intermediate steps | `min(0.1, partial_grade × progress)` — real partial score, capped at 0.1 |
| Episode completion | Full grader score in `[0.0, 1.0]` |

Partial credit is enabled in all tasks.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reset` | Start episode. Body: `{"task_id": "task_1"}`. Returns `session_id`. |
| `POST` | `/step` | Submit action. Body: `{"session_id": "...", "action": {...}}` |
| `GET` | `/state?session_id=...` | Inspect current episode state |
| `GET` | `/tasks` | List all tasks |
| `GET` | `/health` | Health check |
| `DELETE` | `/session/{id}` | Clean up a finished session |

---

## Setup & Running

### Local Python
```bash
pip install -r requirements.txt
python app.py        # server on http://localhost:7861
```

### Docker
```bash
docker build -t email-triage .
docker run -p 7861:7861 email-triage
```

---

## Running Inference

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export HF_TOKEN="your-api-key"
export ENV_URL="http://localhost:7861"

python inference.py
```

### Expected output
```
{"event": "START", "task_id": "task_1", "task_description": "..."}
{"event": "STEP", "task_id": "task_1", "step": 1, "action": {...}, "reward": 0.1, "done": false, "info": {...}}
{"event": "END", "task_id": "task_1", "final_score": 0.8833, "total_steps": 6}
```

### Baseline Scores (GPT-4o)

| Task | Score |
|------|-------|
| task_1 (easy) | ~0.88 |
| task_2 (medium) | ~0.74 |
| task_3 (hard) | ~0.67 |
| task_4 (hard) | ~0.71 |
| **Average** | **~0.75** |

---

## Pre-Submission Validation

```bash
python app.py &        # start server first
python validate.py     # runs 34 automated checks
```

Checks: server health, all 4 tasks reset/step/grade, session isolation, file existence, openenv.yaml fields.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | LLM API endpoint (e.g., `https://api.openai.com/v1`) |
| `MODEL_NAME` | Model identifier (e.g., `gpt-4o`) |
| `HF_TOKEN` | Hugging Face / API key |
| `ENV_URL` | Running environment server URL (default: `http://localhost:7861`) |
