"""Synthetic email dataset for Email Triage environment."""

from .models import Email

EMAILS = [
    # ================================================================
    # URGENT
    # ================================================================
    Email(
        id="e001",
        subject="CRITICAL: Production database down",
        sender="Alice Chen",
        sender_email="alice.chen@company.com",
        body=(
            "Our production PostgreSQL cluster crashed 10 minutes ago. "
            "All customer-facing services are down. Error logs show: "
            "FATAL: could not write to file 'pg_wal/000000010000003C00000001': "
            "No space left on device. We're losing ~$5k/minute. "
            "Need DevOps and backend team to jump on this NOW. "
            "I'll be in the war room (conf room B) immediately."
        ),
        timestamp="2024-01-15T09:03:00Z",
        thread_id="thread_001",
    ),
    Email(
        id="e002",
        subject="Security breach detected - immediate action required",
        sender="Security Team",
        sender_email="security@company.com",
        body=(
            "Our SIEM has flagged unusual activity on 3 employee accounts. "
            "Potential credential compromise. Affected accounts: "
            "john.doe@company.com, jane.smith@company.com, bob.jones@company.com. "
            "Passwords must be reset immediately and MFA enforced. "
            "IT must disable these accounts within the next 30 minutes. "
            "Legal should also be notified per our incident response policy."
        ),
        timestamp="2024-01-15T10:15:00Z",
        thread_id="thread_002",
    ),
    Email(
        id="e003",
        subject="Contract renewal deadline TODAY - $2M deal at risk",
        sender="Marcus Rodriguez",
        sender_email="m.rodriguez@bigclient.com",
        body=(
            "Hi team, I've been trying to reach your sales team all week. "
            "Our current contract expires at midnight tonight and we need the "
            "renewal signed before then. We're prepared to renew at the current "
            "terms ($2M annually) but I need a signed document by 5pm EST today. "
            "If we don't have this sorted by EOD, our legal team has instructed "
            "us to engage with CompetitorX. Please get Sarah (our account manager) "
            "to call me immediately: +1-555-0123."
        ),
        timestamp="2024-01-15T08:45:00Z",
        thread_id="thread_003",
        thread_context=(
            "[Previous message — Jan 8]\n"
            "From: Sarah Kim <s.kim@company.com>\n"
            "Hi Marcus, just following up on the renewal — we'll have the docs ready "
            "well before the deadline. No need to worry!"
        ),
    ),
    Email(
        id="e012",
        subject="URGENT: GlobalCorp users locked out after your v2.3.1 update",
        sender="Derek Walsh",
        sender_email="d.walsh@globalcorp.com",
        body=(
            "Since your 2.3.1 release pushed last night, our entire 200-person team "
            "cannot authenticate. SSO is returning a 403 on every login attempt. "
            "This is blocking ALL operations at GlobalCorp. We have a board presentation "
            "in 3 hours and nobody can access your platform. "
            "Our contract ($800K/year) is up for renewal next month. "
            "Engineering needs to rollback or hotfix IMMEDIATELY. "
            "I'm escalating to your CEO if this isn't resolved in 30 minutes."
        ),
        timestamp="2024-01-15T07:30:00Z",
        thread_id="thread_012",
        thread_context=(
            "[Previous message — Jan 14, 11 PM]\n"
            "From: Deploy Bot <deploy@company.com>\n"
            "v2.3.1 successfully deployed to production. Changes: SSO token refresh "
            "logic updated, session timeout reduced to 8 hours."
        ),
    ),

    # ================================================================
    # NORMAL
    # ================================================================
    Email(
        id="e004",
        subject="Q1 engineering roadmap review - next Tuesday",
        sender="David Park",
        sender_email="d.park@company.com",
        body=(
            "Hi everyone, I'd like to schedule our Q1 roadmap review for next "
            "Tuesday at 2pm. Please come prepared with your team's progress "
            "updates against OKRs. Engineering leads should bring capacity "
            "estimates for Q2. Sarah, can you book a conference room? "
            "Also, please review the draft roadmap doc I shared last week "
            "and add your comments by Monday EOD."
        ),
        timestamp="2024-01-15T11:30:00Z",
        thread_id="thread_004",
    ),
    Email(
        id="e005",
        subject="New employee onboarding - Tom Wilson starts Monday",
        sender="HR Department",
        sender_email="hr@company.com",
        body=(
            "Please be informed that Tom Wilson will be joining as Senior Backend "
            "Engineer on Monday Jan 20. His manager will be Lisa Johnson. "
            "IT needs to provision: laptop (MacBook Pro 14\"), dev environment access, "
            "GitHub organization access, Slack, Jira, and Confluence accounts. "
            "Lisa, please assign an onboarding buddy and prepare a 30-60-90 day plan. "
            "Tom's start package and NDA were completed last week."
        ),
        timestamp="2024-01-15T09:45:00Z",
        thread_id="thread_005",
    ),
    Email(
        id="e006",
        subject="Invoice #INV-2024-089 for cloud services - $12,400",
        sender="AWS Billing",
        sender_email="billing@aws.amazon.com",
        body=(
            "Your AWS invoice for December 2023 is ready. Total amount: $12,400.00. "
            "This is 23% higher than last month ($10,081). "
            "Primary cost drivers: EC2 (+$1,200), RDS (+$800), data transfer (+$320). "
            "Payment is due by January 31, 2024. "
            "Please have the finance team process this and DevOps should review "
            "the cost spike in EC2/RDS usage."
        ),
        timestamp="2024-01-15T07:00:00Z",
        thread_id="thread_006",
    ),
    Email(
        id="e013",
        subject="Board meeting Thursday - slide deck needed by Wednesday noon",
        sender="CEO Office",
        sender_email="ceo.office@company.com",
        body=(
            "Reminder: our quarterly board meeting is this Thursday at 10am. "
            "Each department head must submit their slide deck (max 5 slides) "
            "to me by Wednesday at noon sharp for final compilation. "
            "Topics required: Q4 actuals vs. targets, Q1 OKR status, headcount plan, "
            "and top 3 risks with mitigations. Finance, please include the P&L summary. "
            "No exceptions on the deadline — the board package goes to print at 2pm Wednesday."
        ),
        timestamp="2024-01-15T08:30:00Z",
        thread_id="thread_013",
    ),
    Email(
        id="e014",
        subject="Q2 server capacity planning - need estimates by Jan 24",
        sender="Infrastructure Team",
        sender_email="infra@company.com",
        body=(
            "We're kicking off Q2 capacity planning. To avoid last quarter's "
            "resource crunch, we need each engineering team to submit their "
            "compute/storage estimates by January 24. "
            "Please use the capacity planning template in Confluence. "
            "Key fields: peak RPS forecast, storage growth %, new services launching. "
            "Procurement lead time is 6 weeks, so late submissions will delay Q2 launches. "
            "Questions? Ping @infra-team in Slack."
        ),
        timestamp="2024-01-15T10:00:00Z",
        thread_id="thread_014",
    ),

    # ================================================================
    # LOW
    # ================================================================
    Email(
        id="e007",
        subject="Office holiday party photos",
        sender="Rebecca Thompson",
        sender_email="r.thompson@company.com",
        body=(
            "Hi all! I finally got around to uploading the holiday party photos "
            "from last month. You can find them in the shared Google Drive folder "
            "'Company Events 2023'. There are about 200 photos. I've already done "
            "a first pass to remove the blurry ones. Let me know if you'd like "
            "me to remove any photos with you in them."
        ),
        timestamp="2024-01-15T14:00:00Z",
    ),
    Email(
        id="e008",
        subject="Reminder: Mandatory security training due Friday",
        sender="IT Compliance",
        sender_email="compliance@company.com",
        body=(
            "This is a friendly reminder that the annual security awareness "
            "training must be completed by this Friday. As of today, 34% of "
            "employees have not yet completed the training. The training takes "
            "approximately 45 minutes and can be accessed via the HR portal. "
            "Managers: please follow up with your direct reports who haven't "
            "completed it yet."
        ),
        timestamp="2024-01-15T08:00:00Z",
    ),
    Email(
        id="e009",
        subject="Re: Ping pong table for the office?",
        sender="James Liu",
        sender_email="j.liu@company.com",
        body=(
            "Following up on last week's discussion about adding a ping pong table "
            "to the break room. I found a good one for $350 on Amazon. "
            "If we split it among the 5 of us who wanted it, that's only $70 each. "
            "Let me know if you're still in! I'll order it by end of week if "
            "we have enough interest."
        ),
        timestamp="2024-01-15T13:15:00Z",
    ),
    Email(
        id="e015",
        subject="Team lunch poll - pick your restaurant!",
        sender="People Ops",
        sender_email="people@company.com",
        body=(
            "We're doing a team lunch next Friday to celebrate Q4 hitting our targets! "
            "Please vote for your preferred restaurant by clicking the link below. "
            "Options: 1) Trattoria Roma (Italian), 2) The Golden Chopstick (Chinese), "
            "3) La Parrilla (Mexican). Poll closes Thursday. "
            "Lunch is on the company — $40 per person budget."
        ),
        timestamp="2024-01-15T12:00:00Z",
    ),

    # ================================================================
    # COMPLEX / MULTI-DEPARTMENT (task_3)
    # ================================================================
    Email(
        id="e010",
        subject="Multi-department issue: GDPR compliance audit findings",
        sender="External Auditor",
        sender_email="auditor@gdpr-compliance.eu",
        body=(
            "Following our audit of your data processing activities, we have "
            "identified 3 critical findings that require immediate remediation:\n\n"
            "1. [CRITICAL] User consent records for EU customers are incomplete "
            "   (affects ~50,000 records). Legal must review by Jan 22.\n"
            "2. [HIGH] Data retention policy not enforced in your CRM system. "
            "   Engineering must implement automated deletion within 30 days.\n"
            "3. [MEDIUM] Privacy policy on website does not reflect current "
            "   data processing activities. Marketing/Legal must update within 2 weeks.\n\n"
            "Non-compliance could result in fines up to 4% of annual global turnover. "
            "Please confirm receipt and provide a remediation plan within 5 business days."
        ),
        timestamp="2024-01-15T09:00:00Z",
        thread_id="thread_010",
    ),
    Email(
        id="e011",
        subject="Enterprise deal closing - need exec sign-off + legal + finance",
        sender="Sarah Kim",
        sender_email="s.kim@company.com",
        body=(
            "We're closing a $500K enterprise deal with TechCorp by end of week. "
            "Here's what needs to happen:\n\n"
            "1. CEO/CTO sign-off on custom SLA terms (respond to me by tomorrow noon)\n"
            "2. Legal needs to review and approve the modified MSA by Wednesday\n"
            "3. Finance needs to set up the billing structure (net-60, annual)\n"
            "4. Engineering needs to confirm feasibility of their custom integration "
            "   request (SSO via SAML 2.0 + custom API rate limits)\n\n"
            "If we miss this deadline, the deal goes to Q2 which impacts our "
            "quarterly targets. This is our biggest deal this quarter."
        ),
        timestamp="2024-01-15T10:00:00Z",
        thread_id="thread_011",
    ),
]

EMAILS_BY_ID = {e.id: e for e in EMAILS}

# -----------------------------------------------------------------------
# Task-specific email sets
# -----------------------------------------------------------------------
TASK_1_EMAILS = ["e001", "e004", "e007", "e002", "e008", "e009"]   # 2 each of urgent/normal/low
TASK_2_EMAILS = ["e004", "e005", "e006"]                            # action-heavy
TASK_3_EMAILS = ["e010", "e011", "e003"]                            # complex multi-dept
TASK_4_EMAILS = [                                                    # all urgency levels mixed
    "e001", "e002", "e003", "e012",   # urgent
    "e004", "e013", "e014",           # normal
    "e008", "e015", "e007",           # low / very low
]
