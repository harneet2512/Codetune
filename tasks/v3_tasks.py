"""ToolTune v3 task definitions for the 17 connector tools (GitHub, Drive, Gmail).

Generates tasks across 4 tiers:
- Tier 1: Single tool calls (100 tasks)
- Tier 2: Restraint / no tools needed (80 tasks)
- Tier 3: Multi-step cross-service chains (50 tasks)
- Tier 4: Error recovery with unexpected results (20 tasks)

All prompts are natural language — no templated garbage. Each feels like
something a real developer would type into an assistant.
"""

from __future__ import annotations

import random

from tooltune.contracts import TaskRecord


# ---------------------------------------------------------------------------
# Tier 1 — Single Tool (100 tasks)
# ---------------------------------------------------------------------------

def _build_github_search_code_tasks(rng: random.Random) -> list[TaskRecord]:
    """~12 tasks using github_search_code."""
    prompts = [
        ("Search for the checkout handler in acmecorp/backend", "acmecorp/backend", "checkout",
         "PaymentProcessor.charge found in src/api/payments.py"),
        ("Find where JWT tokens are validated in the backend repo", "acmecorp/backend", "jwt",
         "jwt.decode in src/api/auth.py"),
        ("Look for the authenticate function in acmecorp/backend", "acmecorp/backend", "authenticate",
         "authenticate function in src/api/auth.py"),
        ("Search for any references to Stripe in acmecorp/backend", "acmecorp/backend", "stripe",
         "stripe.charges.create in src/api/payments.py"),
        ("Where is the PaymentProcessor class defined?", "acmecorp/backend", "PaymentProcessor",
         "PaymentProcessor in src/api/payments.py"),
        ("Find code that handles user authentication in the backend", "acmecorp/backend", "AuthError",
         "AuthError raised in src/api/auth.py"),
        ("Search for dataclass definitions in acmecorp/backend", "acmecorp/backend", "dataclass",
         "User dataclass in src/models/user.py"),
        ("Where is the User model defined in the backend?", "acmecorp/backend", "User",
         "User model in src/models/user.py"),
        ("Find any payment-related code in acmecorp/backend", "acmecorp/backend", "payment",
         "PaymentProcessor in src/api/payments.py"),
        ("Search for test files in acmecorp/backend", "acmecorp/backend", "test_",
         "test_authenticate_valid_token in tests/test_auth.py"),
        ("Look up how authentication tests are structured", "acmecorp/backend", "test_authenticate",
         "test_authenticate_valid_token in tests/test_auth.py"),
        ("Find the SECRET_KEY usage in the backend", "acmecorp/backend", "SECRET_KEY",
         "SECRET_KEY used in jwt.decode in src/api/auth.py"),
    ]
    tasks = []
    for i, (prompt, repo, query, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-gh-search-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["github_search_code"],
            metadata={"category": "github", "tool": "github_search_code",
                       "args": {"repo": repo, "query": query}},
        ))
    return tasks


def _build_github_read_file_tasks(rng: random.Random) -> list[TaskRecord]:
    """~8 tasks using github_read_file."""
    prompts = [
        ("Read the file src/api/auth.py from acmecorp/backend", "acmecorp/backend", "src/api/auth.py",
         "def authenticate(token: str) -> User"),
        ("Show me the contents of src/api/payments.py in the backend repo", "acmecorp/backend", "src/api/payments.py",
         "class PaymentProcessor"),
        ("What's in the User model file?", "acmecorp/backend", "src/models/user.py",
         "@dataclass class User with fields id, email, name, role"),
        ("Pull up the README for acmecorp/backend", "acmecorp/backend", "README.md",
         "Production API service for AcmeCorp platform"),
        ("Let me see the architecture docs", "acmecorp/backend", "docs/architecture.md",
         "Layered architecture: API layer, Service layer, Data layer, External integrations"),
        ("Read the auth test file from the backend repo", "acmecorp/backend", "tests/test_auth.py",
         "test_authenticate_valid_token asserts user_123 is active"),
        ("Open src/models/user.py on the main branch", "acmecorp/backend", "src/models/user.py",
         "User dataclass with id, email, name, role, created_at, is_active"),
        ("What does the payments module look like?", "acmecorp/backend", "src/api/payments.py",
         "PaymentProcessor.charge processes payments via Stripe"),
    ]
    tasks = []
    for i, (prompt, repo, path, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-gh-read-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["github_read_file"],
            metadata={"category": "github", "tool": "github_read_file",
                       "args": {"repo": repo, "path": path}},
        ))
    return tasks


def _build_github_list_issues_tasks(rng: random.Random) -> list[TaskRecord]:
    """~8 tasks using github_list_issues."""
    prompts = [
        ("List open issues in acmecorp/backend", "acmecorp/backend", "open", None,
         "4 open issues including #42 Payment timeout, #41 Rate limiting, #40 User model teams, #38 Webhook docs"),
        ("Any urgent bugs in the backend repo?", "acmecorp/backend", "open", "bug,urgent",
         "Issue #42: Payment timeout on large orders (bug, urgent)"),
        ("What enhancement requests are open for the backend?", "acmecorp/backend", "open", "enhancement",
         "Issue #41: Rate limiting and #40: User model teams support"),
        ("Show me all closed issues in acmecorp/backend", "acmecorp/backend", "closed", None,
         "Issue #39: Fix CORS headers for staging env (closed)"),
        ("Are there any documentation issues filed?", "acmecorp/backend", "open", "documentation",
         "Issue #38: Document webhook integration"),
        ("What bugs are currently open in the backend?", "acmecorp/backend", "open", "bug",
         "Issue #42: Payment timeout on large orders"),
        ("List all issues regardless of state in acmecorp/backend", "acmecorp/backend", "all", None,
         "5 issues total: #42 Payment timeout, #41 Rate limiting, #40 User model, #39 CORS fix, #38 Webhook docs"),
        ("Show me the backend issues tagged as good first issue", "acmecorp/backend", "open", "good first issue",
         "No issues found with good first issue label"),
    ]
    tasks = []
    for i, (prompt, repo, state, labels, gt) in enumerate(prompts):
        args: dict = {"repo": repo, "state": state}
        if labels:
            args["labels"] = labels
        tasks.append(TaskRecord(
            id=f"v3-t1-gh-issues-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["github_list_issues"],
            metadata={"category": "github", "tool": "github_list_issues", "args": args},
        ))
    return tasks


def _build_github_list_prs_tasks(rng: random.Random) -> list[TaskRecord]:
    """~7 tasks using github_list_prs."""
    prompts = [
        ("List open PRs in acmecorp/frontend", "acmecorp/frontend", "open",
         "3 open PRs: #15 JWT refresh rotation, #14 payment timeout fix, #13 dependency update (draft)"),
        ("What PRs are open in acmecorp/backend?", "acmecorp/backend", "open",
         "3 open PRs: #15 JWT refresh rotation, #14 payment timeout fix, #13 dependency update"),
        ("Show me merged PRs in the backend", "acmecorp/backend", "closed",
         "PR #12: dashboard chart components (closed, by dave)"),
        ("Any pull requests waiting for review in the infra repo?", "acmecorp/infra", "open",
         "3 open PRs: #15 JWT refresh, #14 payment timeout, #13 deps update"),
        ("What's the current PR situation in acmecorp/backend?", "acmecorp/backend", "all",
         "4 PRs total: 3 open (#15, #14, #13), 1 closed (#12)"),
        ("List all pull requests for the ml-pipeline repo", "acmecorp/ml-pipeline", "all",
         "4 PRs: #15 JWT refresh, #14 payment timeout, #13 deps, #12 dashboard charts"),
        ("Are there any draft PRs in the backend?", "acmecorp/backend", "open",
         "PR #13: chore: update dependencies is in draft state"),
    ]
    tasks = []
    for i, (prompt, repo, state, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-gh-prs-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["github_list_prs"],
            metadata={"category": "github", "tool": "github_list_prs",
                       "args": {"repo": repo, "state": state}},
        ))
    return tasks


def _build_drive_search_tasks(rng: random.Random) -> list[TaskRecord]:
    """~10 tasks using drive_search."""
    prompts = [
        ("Find the product roadmap in Drive", "Roadmap",
         "Q1 2025 Product Roadmap (doc_001)"),
        ("Search for the revenue tracker spreadsheet", "Revenue",
         "Revenue Tracker 2025 (sheet_001)"),
        ("Where's the engineering onboarding doc?", "Onboarding",
         "Engineering Onboarding Guide (doc_002)"),
        ("Find the security audit report in Google Drive", "Security",
         "API Security Audit Report (doc_003)"),
        ("Look for the sprint planning board", "Sprint",
         "Sprint Planning Board (sheet_002)"),
        ("Is there a SOC2 compliance document in Drive?", "SOC2",
         "SOC2 Compliance Checklist.pdf (pdf_001)"),
        ("Search Drive for anything about planning", "Planning",
         "Sprint Planning Board (sheet_002)"),
        ("Find the Q1 roadmap document", "Q1",
         "Q1 2025 Product Roadmap (doc_001)"),
        ("Search for spreadsheets about revenue", "Revenue",
         "Revenue Tracker 2025 (sheet_001)"),
        ("Look for the audit report Dave wrote", "Audit",
         "API Security Audit Report (doc_003) by Dave Kim"),
    ]
    tasks = []
    for i, (prompt, query, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-drive-search-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["drive_search"],
            metadata={"category": "drive", "tool": "drive_search",
                       "args": {"query": query}},
        ))
    return tasks


def _build_drive_read_file_tasks(rng: random.Random) -> list[TaskRecord]:
    """~10 tasks using drive_read_file."""
    prompts = [
        ("What's in the product roadmap doc?", "doc_001",
         "Q1 priorities: billing portal, team collaboration, SOC2 cert, mobile app beta. MRR target $250K"),
        ("Show me the revenue numbers", "sheet_001",
         "Jan $180K/320 customers, Feb $210K/355, Mar $245K/390"),
        ("Pull up the engineering onboarding guide", "doc_002",
         "Clone backend/frontend/infra repos, run make setup, get creds from 1Password"),
        ("Read the security audit report", "doc_003",
         "3 findings: HIGH JWT expiry, MEDIUM rate limiting on login, LOW CORS wildcard in staging"),
        ("What does the roadmap say about Q1 priorities?", "doc_001",
         "Launch self-serve billing portal, ship team collaboration, SOC2 certification, mobile app beta"),
        ("Give me the latest revenue figures from the tracker", "sheet_001",
         "March 2025: $245K revenue, 390 customers, 2.4% churn"),
        ("What are the onboarding steps for new engineers?", "doc_002",
         "Clone repos, run make setup, get creds from 1Password, architecture overview"),
        ("What were the audit findings and severity levels?", "doc_003",
         "HIGH: JWT tokens lack expiry validation, MEDIUM: rate limiting not enforced, LOW: CORS wildcard"),
        ("What's our MRR target according to the roadmap?", "doc_001",
         "MRR target: $250K, DAU target: 5,000, Churn target: <3%"),
        ("How's our churn rate trending?", "sheet_001",
         "Jan 2.1%, Feb 1.8%, Mar 2.4% — slight increase in March"),
    ]
    tasks = []
    for i, (prompt, file_id, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-drive-read-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["drive_read_file"],
            metadata={"category": "drive", "tool": "drive_read_file",
                       "args": {"file_id": file_id}},
        ))
    return tasks


def _build_drive_list_recent_tasks(rng: random.Random) -> list[TaskRecord]:
    """~10 tasks using drive_list_recent."""
    prompts = [
        ("What files were recently modified in Drive?",
         "Sprint Planning Board, Revenue Tracker, API Security Audit Report, Q1 Roadmap, Onboarding Guide, SOC2 Checklist"),
        ("Show me the latest documents that were updated",
         "Most recent: Sprint Planning Board (Mar 22), Revenue Tracker (Mar 20), Security Audit (Mar 18)"),
        ("What has the team been working on in Drive recently?",
         "Recent activity: Sprint Planning, Revenue Tracker, Security Audit Report, Product Roadmap"),
        ("Which Drive files were touched this month?",
         "6 files modified, most recent Sprint Planning Board on 2025-03-22"),
        ("Any recent document updates I should know about?",
         "Sprint Planning Board updated Mar 22, Revenue Tracker Mar 20, Security Audit Mar 18"),
        ("Pull up the most recently edited files",
         "Sprint Planning Board (Eve), Revenue Tracker (Bob), API Security Audit (Dave)"),
        ("What's been updated lately across our Drive?",
         "6 files ranging from SOC2 Checklist (Jan 10) to Sprint Planning Board (Mar 22)"),
        ("Show me Drive activity sorted by recency",
         "Latest: Sprint Planning Board, Revenue Tracker 2025, API Security Audit Report"),
        ("Which documents have been modified in the last week?",
         "Sprint Planning Board (Mar 22), Revenue Tracker 2025 (Mar 20)"),
        ("Give me a rundown of recent Drive changes",
         "Sprint Planning Board by Eve (Mar 22), Revenue Tracker by Bob (Mar 20), Security Audit by Dave (Mar 18)"),
    ]
    tasks = []
    for i, (prompt, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-drive-recent-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["drive_list_recent"],
            metadata={"category": "drive", "tool": "drive_list_recent", "args": {}},
        ))
    return tasks


def _build_gmail_search_tasks(rng: random.Random) -> list[TaskRecord]:
    """~15 tasks using gmail_search."""
    prompts = [
        ("Check for emails about the payment processor outage", "payment",
         "Email from alice@acmecorp.com: Stripe webhook timeout resolved, Bob's PR #14 fixes retry logic"),
        ("Any emails from Alice?", "from:alice",
         "Re: Payment processor outage — Stripe webhook timeout issue resolved"),
        ("Search for security-related emails", "security audit",
         "SOC2 audit action items from Dave — 3 findings need immediate attention"),
        ("Find emails about sprint planning", "sprint planning",
         "Sprint planning March 24 from Carol — meeting at 2pm, update Linear tickets"),
        ("Any hiring announcements recently?", "new team member",
         "Frank Torres joining as Senior Backend Engineer, starting Monday March 24"),
        ("What's the latest about the Stripe issue?", "stripe",
         "Alice reports Stripe webhook timeout resolved with exponential backoff in PR #14"),
        ("Look for emails from Dave", "from:dave",
         "SOC2 audit action items: JWT expiry, rate limiting, CORS issues"),
        ("Find emails about the deployment", "deploy",
         "No emails found matching deploy"),
        ("Any emails from Carol about meetings?", "from:carol sprint",
         "Sprint planning at 2pm in Elm conference room, review sprint board before meeting"),
        ("Search for emails about onboarding", "onboarding",
         "Frank Torres onboarding — Carol is his buddy, he comes from Datadog"),
        ("Are there any urgent emails about the API?", "api",
         "No emails found matching api"),
        ("Find emails about PR reviews", "PR",
         "Alice asks team to review PR #14 for payment timeout fix"),
        ("Any messages about rate limiting?", "rate limiting",
         "Dave's security audit email mentions rate limiting on login as MEDIUM finding, Issue #41 filed"),
        ("Search for emails from Eve about the team", "from:eve",
         "New team member announcement: Frank Torres, Senior Backend Engineer from Datadog"),
        ("What did engineering discuss this week?", "engineering",
         "Payment outage resolved (Alice), sprint planning at 2pm (Carol), new hire Frank Torres (Eve)"),
    ]
    tasks = []
    for i, (prompt, query, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-gmail-search-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["gmail_search"],
            metadata={"category": "gmail", "tool": "gmail_search",
                       "args": {"query": query}},
        ))
    return tasks


def _build_gmail_read_email_tasks(rng: random.Random) -> list[TaskRecord]:
    """~10 tasks using gmail_read_email."""
    prompts = [
        ("Read the full email about the payment processor outage", "msg_001",
         "Alice reports 3 key changes: exponential backoff retries, timeout increase 5s to 15s, dead letter queue"),
        ("Open the SOC2 audit email from Dave", "msg_002",
         "3 findings: JWT token expiry HIGH, rate limiting MEDIUM, CORS wildcard LOW. Issue #41 filed for rate limiting"),
        ("Let me read the sprint planning email", "msg_003",
         "Sprint planning at 2pm in Elm room. Update Linear tickets, flag blockers, review sprint board"),
        ("Show me the full new hire announcement", "msg_004",
         "Frank Torres joining as Senior Backend Engineer from Datadog, focusing on observability. Carol is onboarding buddy"),
        ("Read Alice's email about the webhook fix", "msg_001",
         "Stripe webhook timeout fixed with exponential backoff, timeout 5s->15s, added dead letter queue for failed webhooks"),
        ("What exactly did Dave say about the security audit?", "msg_002",
         "External team found 3 issues: JWT validation skipped on 2 endpoints, no brute force protection, CORS wildcard in staging"),
        ("Open Carol's email about the sprint", "msg_003",
         "Sprint planning agenda: review velocity, triage issues, assign stories. Elm conference room at 2pm"),
        ("Read the email about Frank starting", "msg_004",
         "Frank Torres starts Monday March 24 as Senior Backend Engineer, came from Datadog metrics pipeline"),
        ("Pull up the payment outage resolution email", "msg_001",
         "Alice confirms Stripe timeout resolved. PR #14 adds retry with backoff and dead letter queue"),
        ("What action items did Dave list in the audit email?", "msg_002",
         "1. Fix JWT expiry validation (HIGH), 2. Add rate limiting to login (MEDIUM), 3. Restrict CORS (LOW)"),
    ]
    tasks = []
    for i, (prompt, msg_id, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-gmail-read-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["gmail_read_email"],
            metadata={"category": "gmail", "tool": "gmail_read_email",
                       "args": {"message_id": msg_id}},
        ))
    return tasks


def _build_gmail_list_labels_tasks(rng: random.Random) -> list[TaskRecord]:
    """~10 tasks using gmail_list_labels."""
    prompts = [
        ("List all my email labels",
         "9 labels: INBOX, SENT, DRAFT, TRASH, SPAM, Engineering, Security, Sprint, Hiring"),
        ("What Gmail labels do I have set up?",
         "System labels: INBOX, SENT, DRAFT, TRASH, SPAM. Custom labels: Engineering, Security, Sprint, Hiring"),
        ("Show me my custom email labels",
         "4 custom labels: Engineering, Security, Sprint, Hiring"),
        ("How is my email organized?",
         "9 labels total — 5 system (INBOX, SENT, DRAFT, TRASH, SPAM) and 4 user-created"),
        ("Do I have a label for security emails?",
         "Yes, Security label exists (Label_2, user type)"),
        ("What labels can I use to categorize emails?",
         "Available labels: Engineering, Security, Sprint, Hiring (plus system labels)"),
        ("Check if there's an Engineering label in Gmail",
         "Yes, Engineering label exists (Label_1, user type)"),
        ("Show me all available Gmail labels",
         "INBOX, SENT, DRAFT, TRASH, SPAM, Engineering, Security, Sprint, Hiring"),
        ("Am I using any custom labels for organizing email?",
         "Yes, 4 custom labels: Engineering, Security, Sprint, Hiring"),
        ("List the email labels I've created",
         "Custom labels: Engineering (Label_1), Security (Label_2), Sprint (Label_3), Hiring (Label_4)"),
    ]
    tasks = []
    for i, (prompt, gt) in enumerate(prompts):
        tasks.append(TaskRecord(
            id=f"v3-t1-gmail-labels-{i+1}",
            tier="tier1_single_tool",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=["gmail_list_labels"],
            metadata={"category": "gmail", "tool": "gmail_list_labels", "args": {}},
        ))
    return tasks


def build_tier1(count: int = 100) -> list[TaskRecord]:
    """Build Tier 1 single-tool tasks. Target: 100."""
    rng = random.Random(42)
    tasks: list[TaskRecord] = []

    # GitHub tasks (~35)
    tasks.extend(_build_github_search_code_tasks(rng))   # 12
    tasks.extend(_build_github_read_file_tasks(rng))      # 8
    tasks.extend(_build_github_list_issues_tasks(rng))    # 8
    tasks.extend(_build_github_list_prs_tasks(rng))       # 7

    # Drive tasks (~30)
    tasks.extend(_build_drive_search_tasks(rng))          # 10
    tasks.extend(_build_drive_read_file_tasks(rng))       # 10
    tasks.extend(_build_drive_list_recent_tasks(rng))     # 10

    # Gmail tasks (~35)
    tasks.extend(_build_gmail_search_tasks(rng))          # 15
    tasks.extend(_build_gmail_read_email_tasks(rng))      # 10
    tasks.extend(_build_gmail_list_labels_tasks(rng))     # 10

    rng.shuffle(tasks)
    return tasks[:count]


# ---------------------------------------------------------------------------
# Tier 2 — Restraint / No Tools Needed (80 tasks)
# ---------------------------------------------------------------------------

_RESTRAINT_QUESTIONS: list[tuple[str, str]] = [
    # CS fundamentals
    ("What HTTP status code means rate limited?", "429 Too Many Requests"),
    ("What HTTP status code means not found?", "404 Not Found"),
    ("What HTTP status code means unauthorized?", "401 Unauthorized"),
    ("What HTTP status code means internal server error?", "500 Internal Server Error"),
    ("What HTTP status code means created?", "201 Created"),
    ("What HTTP status code means bad request?", "400 Bad Request"),
    ("What HTTP status code means forbidden?", "403 Forbidden"),
    ("What HTTP status code means conflict?", "409 Conflict"),
    ("What's the time complexity of binary search?", "O(log n)"),
    ("What's the time complexity of quicksort on average?", "O(n log n)"),
    ("What's the time complexity of inserting into a hash table?", "O(1) amortized"),
    ("What's the time complexity of BFS on a graph?", "O(V + E)"),
    ("What data structure uses FIFO ordering?", "Queue"),
    ("What data structure uses LIFO ordering?", "Stack"),
    ("What's the difference between a list and a tuple in Python?", "Lists are mutable, tuples are immutable"),
    ("Is Python dynamically typed or statically typed?", "Python is dynamically typed"),
    ("What does GIL stand for in Python?", "Global Interpreter Lock"),
    ("What port does HTTPS use by default?", "443"),
    ("What port does HTTP use by default?", "80"),
    ("What port does SSH use by default?", "22"),
    ("What port does PostgreSQL listen on by default?", "5432"),
    ("What port does Redis use by default?", "6379"),
    ("What does DNS stand for?", "Domain Name System"),
    ("What does TCP stand for?", "Transmission Control Protocol"),
    ("What does REST stand for?", "Representational State Transfer"),

    # API / web concepts
    ("What does idempotent mean in REST APIs?", "An operation that produces the same result regardless of how many times it is called"),
    ("What HTTP methods are considered idempotent?", "GET, PUT, DELETE, HEAD, OPTIONS are idempotent; POST and PATCH are not"),
    ("What's the difference between PUT and PATCH?", "PUT replaces the entire resource, PATCH partially updates it"),
    ("What is CORS?", "Cross-Origin Resource Sharing — a browser security mechanism that controls which origins can access resources"),
    ("What does JWT stand for?", "JSON Web Token"),
    ("What are the three parts of a JWT?", "Header, Payload, and Signature"),
    ("What's the difference between authentication and authorization?", "Authentication verifies identity (who you are), authorization verifies permissions (what you can do)"),
    ("What is a webhook?", "A callback mechanism where a server sends HTTP requests to a client URL when events occur"),
    ("What does CRUD stand for?", "Create, Read, Update, Delete"),
    ("What is rate limiting?", "Restricting the number of API requests a client can make within a time window"),
    ("What is an API gateway?", "A server that acts as a single entry point for API requests, handling routing, auth, rate limiting, and load balancing"),

    # ML/AI concepts
    ("What's the difference between SFT and RLHF?", "SFT (Supervised Fine-Tuning) trains on example completions, RLHF (Reinforcement Learning from Human Feedback) uses a reward model trained on preference data"),
    ("What does GRPO stand for in language model training?", "Group Relative Policy Optimization — a reinforcement learning method for LLM alignment"),
    ("What is a transformer in machine learning?", "A neural network architecture using self-attention mechanisms, introduced in the 'Attention Is All You Need' paper"),
    ("What does GPT stand for?", "Generative Pre-trained Transformer"),
    ("What is the difference between precision and recall?", "Precision is the ratio of true positives to all predicted positives; recall is the ratio of true positives to all actual positives"),
    ("What is overfitting?", "When a model learns the training data too well, including noise, and fails to generalize to new data"),
    ("What is a loss function?", "A function that measures how well a model's predictions match the expected output — training minimizes this"),
    ("What is gradient descent?", "An optimization algorithm that iteratively adjusts parameters in the direction that reduces the loss function"),
    ("What's the difference between a CNN and an RNN?", "CNNs use convolutional layers for spatial patterns (images), RNNs use recurrent connections for sequential data (text, time series)"),
    ("What is batch normalization?", "A technique that normalizes layer inputs to stabilize and accelerate neural network training"),
    ("What does the softmax function do?", "Converts a vector of real numbers into a probability distribution that sums to 1"),
    ("What is the vanishing gradient problem?", "When gradients become extremely small during backpropagation through many layers, preventing effective learning in early layers"),

    # DevOps / infrastructure
    ("What is the difference between Docker and Kubernetes?", "Docker is a container runtime for packaging applications; Kubernetes is an orchestration platform for managing containers at scale"),
    ("What does CI/CD stand for?", "Continuous Integration / Continuous Delivery (or Deployment)"),
    ("What is a load balancer?", "A system that distributes incoming traffic across multiple servers to improve availability and performance"),
    ("What is blue-green deployment?", "A deployment strategy with two identical environments where traffic is switched from the old (blue) to the new (green) version"),
    ("What is a canary deployment?", "Gradually rolling out a change to a small subset of users before deploying to the full infrastructure"),
    ("What is infrastructure as code?", "Managing and provisioning infrastructure through machine-readable configuration files rather than manual processes"),
    ("What does MTTR stand for?", "Mean Time To Recovery — the average time to restore service after a failure"),
    ("What is an SLA?", "Service Level Agreement — a commitment between a provider and client on service quality metrics like uptime"),
    ("What is observability?", "The ability to understand a system's internal state from its external outputs: logs, metrics, and traces"),
    ("What are the three pillars of observability?", "Logs, metrics, and traces"),

    # Database concepts
    ("What does ACID stand for in databases?", "Atomicity, Consistency, Isolation, Durability"),
    ("What is the difference between SQL and NoSQL?", "SQL databases are relational with structured schemas; NoSQL databases are non-relational with flexible schemas"),
    ("What is an index in a database?", "A data structure that speeds up data retrieval by providing quick lookup paths, at the cost of extra storage and slower writes"),
    ("What is database sharding?", "Splitting a database into smaller, independent partitions (shards) distributed across multiple servers"),
    ("What is eventual consistency?", "A consistency model where replicas may temporarily diverge but will eventually converge to the same state"),
    ("What does ORM stand for?", "Object-Relational Mapping — a technique for converting between database rows and programming language objects"),

    # Git concepts
    ("What does git rebase do?", "Reapplies commits from the current branch on top of another branch, creating a linear commit history"),
    ("What's the difference between git merge and git rebase?", "Merge creates a merge commit preserving branch history; rebase replays commits for a linear history"),
    ("What is a git hook?", "A script that runs automatically at certain points in the git workflow, like pre-commit or post-push"),
    ("What does git stash do?", "Temporarily saves uncommitted changes so you can work on something else and reapply them later"),
    ("What is a detached HEAD state in git?", "When HEAD points to a specific commit instead of a branch, meaning new commits won't belong to any branch"),

    # Security concepts
    ("What is SQL injection?", "An attack where malicious SQL code is inserted into application queries through user input to manipulate the database"),
    ("What is XSS?", "Cross-Site Scripting — an attack where malicious scripts are injected into web pages viewed by other users"),
    ("What is CSRF?", "Cross-Site Request Forgery — an attack that tricks a user's browser into making unwanted requests to a site where they're authenticated"),
    ("What is the principle of least privilege?", "Users and systems should have only the minimum permissions necessary to perform their intended function"),
    ("What is two-factor authentication?", "An authentication method requiring two different types of verification, typically something you know and something you have"),

    # Python specifics
    ("What is a Python decorator?", "A function that wraps another function to extend its behavior without modifying its code, using @syntax"),
    ("What is a context manager in Python?", "An object that defines __enter__ and __exit__ methods for resource management, used with the with statement"),
    ("What does *args and **kwargs mean in Python?", "*args collects positional arguments into a tuple, **kwargs collects keyword arguments into a dictionary"),
    ("What is a Python generator?", "A function that uses yield to produce a sequence of values lazily, one at a time, without storing the entire sequence in memory"),
    ("What is the difference between deepcopy and copy in Python?", "copy creates a shallow copy (references nested objects), deepcopy recursively copies all nested objects"),
    ("What is a Python virtual environment?", "An isolated Python installation that allows projects to have their own dependencies independent of system packages"),
]


def build_tier2(count: int = 80) -> list[TaskRecord]:
    """Build Tier 2 restraint tasks. Target: 80."""
    rng = random.Random(42)
    questions = list(_RESTRAINT_QUESTIONS)
    rng.shuffle(questions)
    tasks = []
    for i in range(min(count, len(questions))):
        prompt, gt = questions[i]
        tasks.append(TaskRecord(
            id=f"v3-t2-restraint-{i+1}",
            tier="tier2_restraint",
            prompt=prompt,
            ground_truth=gt,
            expected_tools=[],
            metadata={"category": "restraint"},
        ))
    return tasks


# ---------------------------------------------------------------------------
# Tier 3 — Multi-Step (50 tasks)
# ---------------------------------------------------------------------------

_MULTI_STEP_TASKS: list[dict] = [
    # GitHub + GitHub cross-tool patterns
    {
        "prompt": "Find the checkout bug in GitHub and tell me what the code looks like",
        "ground_truth": "Issue #42 Payment timeout on large orders; PaymentProcessor.charge in src/api/payments.py processes via Stripe",
        "expected_tools": ["github_list_issues", "github_search_code"],
        "steps": [
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open", "labels": "bug"}},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "payment"}},
        ],
    },
    {
        "prompt": "Check if there are any open issues about authentication, and pull up the related code",
        "ground_truth": "Issue #41 Add rate limiting to auth endpoints; authenticate function in src/api/auth.py validates JWT tokens",
        "expected_tools": ["github_list_issues", "github_read_file"],
        "steps": [
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open"}},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "src/api/auth.py"}},
        ],
    },
    {
        "prompt": "Find all open PRs in the backend and read the details of the JWT refresh PR",
        "ground_truth": "3 open PRs; PR #15 adds JWT refresh token rotation with 142 additions, 38 deletions across 4 files",
        "expected_tools": ["github_list_prs", "github_read_pr"],
        "steps": [
            {"tool": "github_list_prs", "args": {"repo": "acmecorp/backend", "state": "open"}},
            {"tool": "github_read_pr", "args": {"repo": "acmecorp/backend", "pr_number": 15}},
        ],
    },
    {
        "prompt": "What PRs are addressing the payment timeout issue? Show me the PR details",
        "ground_truth": "PR #14 fix: payment processor timeout handling by Bob, 142 additions, 38 deletions, mergeable",
        "expected_tools": ["github_list_prs", "github_read_pr"],
        "steps": [
            {"tool": "github_list_prs", "args": {"repo": "acmecorp/backend", "state": "open"}},
            {"tool": "github_read_pr", "args": {"repo": "acmecorp/backend", "pr_number": 14}},
        ],
    },
    {
        "prompt": "List the bugs in the backend repo and then find the related code for the most urgent one",
        "ground_truth": "Issue #42 Payment timeout (urgent); PaymentProcessor in src/api/payments.py with charge method using Stripe",
        "expected_tools": ["github_list_issues", "github_search_code"],
        "steps": [
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open", "labels": "bug"}},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "payment"}},
        ],
    },

    # Gmail + Gmail patterns
    {
        "prompt": "Find emails about the security audit and read the full details",
        "ground_truth": "Dave's email: 3 findings - JWT expiry (HIGH), rate limiting (MEDIUM), CORS wildcard (LOW). Issue #41 filed",
        "expected_tools": ["gmail_search", "gmail_read_email"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "security audit"}},
            {"tool": "gmail_read_email", "args": {"message_id": "msg_002"}},
        ],
    },
    {
        "prompt": "Check if there are any emails about the payment issue and read the latest one",
        "ground_truth": "Alice's email: Stripe timeout resolved with exponential backoff, timeout 5s->15s, dead letter queue added. PR #14",
        "expected_tools": ["gmail_search", "gmail_read_email"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "payment"}},
            {"tool": "gmail_read_email", "args": {"message_id": "msg_001"}},
        ],
    },
    {
        "prompt": "Find emails from Carol and read the full message",
        "ground_truth": "Sprint planning at 2pm in Elm room. Update Linear tickets, flag blockers, review sprint board. Agenda: review velocity, triage, assign stories",
        "expected_tools": ["gmail_search", "gmail_read_email"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "from:carol"}},
            {"tool": "gmail_read_email", "args": {"message_id": "msg_003"}},
        ],
    },
    {
        "prompt": "Search for emails about the new hire and get the full announcement",
        "ground_truth": "Frank Torres joining as Senior Backend Engineer from Datadog, focusing on observability. Starts Monday March 24, Carol is onboarding buddy",
        "expected_tools": ["gmail_search", "gmail_read_email"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "new team member"}},
            {"tool": "gmail_read_email", "args": {"message_id": "msg_004"}},
        ],
    },
    {
        "prompt": "Look for any emails about the sprint and tell me the full agenda",
        "ground_truth": "Sprint planning at 2pm in Elm conference room. Agenda: review velocity, triage new issues, assign sprint stories",
        "expected_tools": ["gmail_search", "gmail_read_email"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "sprint planning"}},
            {"tool": "gmail_read_email", "args": {"message_id": "msg_003"}},
        ],
    },

    # Drive + Drive patterns
    {
        "prompt": "Find the security audit doc in Drive and read its contents",
        "ground_truth": "API Security Audit Report: HIGH JWT expiry, MEDIUM rate limiting, LOW CORS wildcard. PR #15 in progress for JWT fix",
        "expected_tools": ["drive_search", "drive_read_file"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "Security"}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_003"}},
        ],
    },
    {
        "prompt": "Search Drive for the roadmap and tell me what's in it",
        "ground_truth": "Q1 2025 priorities: billing portal (Feb), team collaboration (Mar), SOC2 cert, mobile app beta (Mar 30). MRR target $250K",
        "expected_tools": ["drive_search", "drive_read_file"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "Roadmap"}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_001"}},
        ],
    },
    {
        "prompt": "Find the onboarding guide and tell me the setup steps",
        "ground_truth": "Clone backend/frontend/infra repos, run make setup, get creds from 1Password Engineering vault. Stack: Python/FastAPI backend, React/TypeScript frontend, PostgreSQL+Redis, AWS ECS",
        "expected_tools": ["drive_search", "drive_read_file"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "Onboarding"}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_002"}},
        ],
    },
    {
        "prompt": "What recently modified files are in Drive? Read the most recent one",
        "ground_truth": "Sprint Planning Board is most recent (Mar 22). Other recent: Revenue Tracker, Security Audit, Q1 Roadmap",
        "expected_tools": ["drive_list_recent", "drive_read_file"],
        "steps": [
            {"tool": "drive_list_recent", "args": {}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_001"}},
        ],
    },
    {
        "prompt": "Get the file info for the roadmap doc and then read its content",
        "ground_truth": "Q1 2025 Product Roadmap by Alice Chen, shared with acmecorp.com domain. Priorities: billing, collaboration, SOC2, mobile",
        "expected_tools": ["drive_get_file_info", "drive_read_file"],
        "steps": [
            {"tool": "drive_get_file_info", "args": {"file_id": "doc_001"}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_001"}},
        ],
    },

    # Cross-service: Gmail + GitHub
    {
        "prompt": "Check if there are any urgent emails about the API, then find the related PR",
        "ground_truth": "Alice's email about payment outage references PR #14 for timeout fix. PR #14: payment processor timeout handling by Bob",
        "expected_tools": ["gmail_search", "github_list_prs"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "payment"}},
            {"tool": "github_list_prs", "args": {"repo": "acmecorp/backend", "state": "open"}},
        ],
    },
    {
        "prompt": "Read the security audit email and check if the rate limiting issue was filed on GitHub",
        "ground_truth": "Dave's audit email mentions Issue #41 for rate limiting. Issue #41: Add rate limiting to auth endpoints (open, enhancement)",
        "expected_tools": ["gmail_read_email", "github_list_issues"],
        "steps": [
            {"tool": "gmail_read_email", "args": {"message_id": "msg_002"}},
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open", "labels": "enhancement"}},
        ],
    },
    {
        "prompt": "Find the email about the Stripe fix and check the status of the related PR",
        "ground_truth": "Alice's email references PR #14. PR #14 fix: payment processor timeout handling, open, by Bob, not draft, mergeable",
        "expected_tools": ["gmail_search", "github_read_pr"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "payment stripe"}},
            {"tool": "github_read_pr", "args": {"repo": "acmecorp/backend", "pr_number": 14}},
        ],
    },
    {
        "prompt": "Check emails about the audit, then look at the auth code that needs fixing",
        "ground_truth": "Audit found JWT expiry issue. auth.py: jwt.decode with SECRET_KEY, raises AuthError if user not found",
        "expected_tools": ["gmail_search", "github_read_file"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "security audit"}},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "src/api/auth.py"}},
        ],
    },
    {
        "prompt": "What bugs are open in GitHub? Send a summary email to the engineering team",
        "ground_truth": "2 bugs: #42 Payment timeout (urgent), #39 CORS (closed). Summary email sent to engineering@acmecorp.com",
        "expected_tools": ["github_list_issues", "gmail_send_email"],
        "steps": [
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open", "labels": "bug"}},
            {"tool": "gmail_send_email", "args": {"to": "engineering@acmecorp.com", "subject": "Open Bug Summary", "body": "Current open bugs:\n- #42 Payment timeout on large orders (urgent)\n"}},
        ],
    },

    # Cross-service: Drive + GitHub
    {
        "prompt": "Find the design doc in Drive and check if the corresponding GitHub issue exists",
        "ground_truth": "No design doc found. Architecture doc available (doc_003 Security Audit). Related issues include #41 rate limiting",
        "expected_tools": ["drive_search", "github_list_issues"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "design"}},
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open"}},
        ],
    },
    {
        "prompt": "Read the security audit from Drive and find the related PRs in GitHub",
        "ground_truth": "Audit recommends JWT fix (PR #15 in progress) and rate limiting (Issue #41). PR #15: JWT refresh token rotation, open",
        "expected_tools": ["drive_read_file", "github_list_prs"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "doc_003"}},
            {"tool": "github_list_prs", "args": {"repo": "acmecorp/backend", "state": "open"}},
        ],
    },
    {
        "prompt": "What does the onboarding guide say about repos? List open PRs for the backend",
        "ground_truth": "Onboarding: clone backend/frontend/infra repos. Backend has 3 open PRs: JWT refresh, payment timeout, deps update",
        "expected_tools": ["drive_read_file", "github_list_prs"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "doc_002"}},
            {"tool": "github_list_prs", "args": {"repo": "acmecorp/backend", "state": "open"}},
        ],
    },
    {
        "prompt": "Check the roadmap priorities and see which ones have open GitHub issues",
        "ground_truth": "Roadmap: billing, collaboration, SOC2, mobile beta. Open issues: payment timeout, rate limiting, user model teams, webhook docs",
        "expected_tools": ["drive_read_file", "github_list_issues"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "doc_001"}},
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open"}},
        ],
    },
    {
        "prompt": "Check the revenue tracker and find any finance-related code in GitHub",
        "ground_truth": "Revenue: Jan $180K, Feb $210K, Mar $245K. Payment code in src/api/payments.py handles Stripe charges",
        "expected_tools": ["drive_read_file", "github_search_code"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "sheet_001"}},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "payment"}},
        ],
    },

    # Cross-service: Drive + Gmail
    {
        "prompt": "Check the roadmap and find any emails about the mobile app beta",
        "ground_truth": "Roadmap lists mobile app beta for Mar 30. No specific emails found about mobile app",
        "expected_tools": ["drive_read_file", "gmail_search"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "doc_001"}},
            {"tool": "gmail_search", "args": {"query": "mobile app"}},
        ],
    },
    {
        "prompt": "Read the security audit from Drive and find related emails",
        "ground_truth": "Audit has 3 findings. Dave's email about SOC2 audit covers same findings and mentions Issue #41 filed",
        "expected_tools": ["drive_read_file", "gmail_search"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "doc_003"}},
            {"tool": "gmail_search", "args": {"query": "security audit"}},
        ],
    },
    {
        "prompt": "Find the onboarding doc and check for emails about the new hire who'll need it",
        "ground_truth": "Onboarding guide covers setup steps. Frank Torres starting Monday as Senior Backend Engineer, Carol is buddy",
        "expected_tools": ["drive_search", "gmail_search"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "Onboarding"}},
            {"tool": "gmail_search", "args": {"query": "new team member"}},
        ],
    },

    # 3-step chains
    {
        "prompt": "Find the payment bug in GitHub, read the code, and email Bob about it",
        "ground_truth": "Issue #42 payment timeout. PaymentProcessor.charge in payments.py. Email sent to bob@acmecorp.com about the bug",
        "expected_tools": ["github_list_issues", "github_read_file", "gmail_send_email"],
        "steps": [
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open", "labels": "bug,urgent"}},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "src/api/payments.py"}},
            {"tool": "gmail_send_email", "args": {"to": "bob@acmecorp.com", "subject": "Payment timeout bug #42", "body": "The PaymentProcessor.charge method needs timeout handling. See issue #42."}},
        ],
    },
    {
        "prompt": "Read the security audit from Drive, check the related GitHub issues, and email Alice a status update",
        "ground_truth": "Audit: 3 findings. Issue #41 filed for rate limiting. Email sent to alice@acmecorp.com with status",
        "expected_tools": ["drive_read_file", "github_list_issues", "gmail_send_email"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "doc_003"}},
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open"}},
            {"tool": "gmail_send_email", "args": {"to": "alice@acmecorp.com", "subject": "Security audit status", "body": "Audit findings: JWT expiry (HIGH) - PR #15 in progress, Rate limiting (MEDIUM) - Issue #41 filed, CORS (LOW) - pending."}},
        ],
    },
    {
        "prompt": "Find the deployment runbook from Drive, read it, and check the latest deploy PR",
        "ground_truth": "No deployment runbook found. Engineering Onboarding Guide available. PRs: JWT refresh #15, payment timeout #14",
        "expected_tools": ["drive_search", "drive_read_file", "github_list_prs"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "deployment"}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_002"}},
            {"tool": "github_list_prs", "args": {"repo": "acmecorp/backend", "state": "open"}},
        ],
    },
    {
        "prompt": "Check recent Drive files, read the latest audit report, and find related emails about it",
        "ground_truth": "Most recent files include Security Audit (Mar 18). Audit has 3 findings. Dave's email covers same findings",
        "expected_tools": ["drive_list_recent", "drive_read_file", "gmail_search"],
        "steps": [
            {"tool": "drive_list_recent", "args": {}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_003"}},
            {"tool": "gmail_search", "args": {"query": "security audit"}},
        ],
    },
    {
        "prompt": "Search for the JWT auth code, read the PR that modifies it, and check for related emails",
        "ground_truth": "JWT code in src/api/auth.py. PR #15 adds refresh token rotation. Alice's payment email references related work",
        "expected_tools": ["github_search_code", "github_read_pr", "gmail_search"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "jwt"}},
            {"tool": "github_read_pr", "args": {"repo": "acmecorp/backend", "pr_number": 15}},
            {"tool": "gmail_search", "args": {"query": "JWT"}},
        ],
    },
    {
        "prompt": "Check the sprint planning email, see what issues are open, and read the roadmap for priorities",
        "ground_truth": "Sprint at 2pm, update Linear tickets. 4 open issues. Roadmap priorities: billing, collaboration, SOC2, mobile beta",
        "expected_tools": ["gmail_read_email", "github_list_issues", "drive_read_file"],
        "steps": [
            {"tool": "gmail_read_email", "args": {"message_id": "msg_003"}},
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open"}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_001"}},
        ],
    },
    {
        "prompt": "Find the revenue spreadsheet in Drive, read it, and search for any finance-related emails",
        "ground_truth": "Revenue Tracker: Jan $180K, Feb $210K, Mar $245K. No specific finance emails found",
        "expected_tools": ["drive_search", "drive_read_file", "gmail_search"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "Revenue"}},
            {"tool": "drive_read_file", "args": {"file_id": "sheet_001"}},
            {"tool": "gmail_search", "args": {"query": "revenue"}},
        ],
    },
    {
        "prompt": "Read the new hire email, check the onboarding guide, and list the backend PRs they should review",
        "ground_truth": "Frank Torres starts Monday from Datadog. Onboarding: clone repos, make setup, 1Password. 3 open PRs to review",
        "expected_tools": ["gmail_read_email", "drive_read_file", "github_list_prs"],
        "steps": [
            {"tool": "gmail_read_email", "args": {"message_id": "msg_004"}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_002"}},
            {"tool": "github_list_prs", "args": {"repo": "acmecorp/backend", "state": "open"}},
        ],
    },
    {
        "prompt": "What did Alice email about the payment fix? Read the actual PR she referenced",
        "ground_truth": "Alice's email: PR #14 fixes retry logic with exponential backoff. PR #14: 142 additions, 38 deletions, 4 changed files, mergeable",
        "expected_tools": ["gmail_search", "gmail_read_email", "github_read_pr"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "from:alice payment"}},
            {"tool": "gmail_read_email", "args": {"message_id": "msg_001"}},
            {"tool": "github_read_pr", "args": {"repo": "acmecorp/backend", "pr_number": 14}},
        ],
    },
    {
        "prompt": "Check what the security audit says about authentication, then read the auth code and the related PR",
        "ground_truth": "Audit: JWT tokens lack expiry validation (HIGH). auth.py: jwt.decode validates tokens. PR #15: JWT refresh token rotation",
        "expected_tools": ["drive_read_file", "github_read_file", "github_read_pr"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "doc_003"}},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "src/api/auth.py"}},
            {"tool": "github_read_pr", "args": {"repo": "acmecorp/backend", "pr_number": 15}},
        ],
    },
    {
        "prompt": "Search Gmail for sprint info, check what labels exist, and read the full sprint email",
        "ground_truth": "Sprint planning email found. Labels include Sprint (Label_3). Full email: 2pm in Elm room, update tickets, flag blockers",
        "expected_tools": ["gmail_search", "gmail_list_labels", "gmail_read_email"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "sprint"}},
            {"tool": "gmail_list_labels", "args": {}},
            {"tool": "gmail_read_email", "args": {"message_id": "msg_003"}},
        ],
    },
    {
        "prompt": "List recent Drive docs, check who owns the security audit doc, and read it",
        "ground_truth": "6 recent files. Security Audit owned by Dave Kim, shared with domain. Findings: JWT, rate limiting, CORS",
        "expected_tools": ["drive_list_recent", "drive_get_file_info", "drive_read_file"],
        "steps": [
            {"tool": "drive_list_recent", "args": {}},
            {"tool": "drive_get_file_info", "args": {"file_id": "doc_003"}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_003"}},
        ],
    },

    # Additional multi-step tasks to hit 50

    {
        "prompt": "Look at PR #15 details and check what the security audit says about JWT tokens",
        "ground_truth": "PR #15: JWT refresh token rotation, 142 additions, 4 files changed. Audit: JWT tokens lack expiry validation (HIGH)",
        "expected_tools": ["github_read_pr", "drive_read_file"],
        "steps": [
            {"tool": "github_read_pr", "args": {"repo": "acmecorp/backend", "pr_number": 15}},
            {"tool": "drive_read_file", "args": {"file_id": "doc_003"}},
        ],
    },
    {
        "prompt": "Find the SOC2 checklist in Drive and check if there are related emails",
        "ground_truth": "SOC2 Compliance Checklist.pdf (pdf_001) found. Dave's email about SOC2 audit covers 3 security findings",
        "expected_tools": ["drive_search", "gmail_search"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "SOC2"}},
            {"tool": "gmail_search", "args": {"query": "SOC2 audit"}},
        ],
    },
    {
        "prompt": "Check what documentation issues exist and read the webhook docs issue details",
        "ground_truth": "Issue #38: Document webhook integration (open, by Eve). No detailed webhook docs in codebase yet",
        "expected_tools": ["github_list_issues", "github_search_code"],
        "steps": [
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open", "labels": "documentation"}},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "webhook"}},
        ],
    },
    {
        "prompt": "Get the file info for the revenue tracker and read its contents",
        "ground_truth": "Revenue Tracker 2025 owned by Bob Martinez, shared. Jan $180K, Feb $210K, Mar $245K revenue",
        "expected_tools": ["drive_get_file_info", "drive_read_file"],
        "steps": [
            {"tool": "drive_get_file_info", "args": {"file_id": "sheet_001"}},
            {"tool": "drive_read_file", "args": {"file_id": "sheet_001"}},
        ],
    },
    {
        "prompt": "Find all emails from Alice, then check the PR she mentioned",
        "ground_truth": "Alice emailed about payment outage resolution. PR #14: payment timeout fix by Bob, 142 additions, mergeable",
        "expected_tools": ["gmail_search", "github_read_pr"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "from:alice"}},
            {"tool": "github_read_pr", "args": {"repo": "acmecorp/backend", "pr_number": 14}},
        ],
    },
    {
        "prompt": "Read the architecture doc and list what enhancement issues are planned",
        "ground_truth": "Architecture: layered (API, Service, Data, External). Enhancements: #41 rate limiting, #40 user model teams",
        "expected_tools": ["github_read_file", "github_list_issues"],
        "steps": [
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "docs/architecture.md"}},
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open", "labels": "enhancement"}},
        ],
    },
    {
        "prompt": "Search for auth-related code and check what test coverage exists",
        "ground_truth": "auth.py has authenticate function. test_auth.py tests valid token authentication for user_123",
        "expected_tools": ["github_search_code", "github_read_file"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "authenticate"}},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "tests/test_auth.py"}},
        ],
    },
    {
        "prompt": "Check what's in the sprint planning board and find the sprint planning email",
        "ground_truth": "Sprint Planning Board in Drive (sheet_002, Mar 22). Carol's email: sprint at 2pm, update Linear tickets",
        "expected_tools": ["drive_search", "gmail_search"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "Sprint"}},
            {"tool": "gmail_search", "args": {"query": "sprint planning"}},
        ],
    },
    {
        "prompt": "Get the closed PRs and check if there are related closed issues",
        "ground_truth": "Closed PR #12: dashboard chart components by Dave. Closed issue #39: CORS headers fix by Dave",
        "expected_tools": ["github_list_prs", "github_list_issues"],
        "steps": [
            {"tool": "github_list_prs", "args": {"repo": "acmecorp/backend", "state": "closed"}},
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "closed"}},
        ],
    },
    {
        "prompt": "Read the payment outage email in full and check the test file for payment tests",
        "ground_truth": "Alice: exponential backoff retry, timeout 5s->15s, dead letter queue. test_auth.py exists but no payment-specific tests found",
        "expected_tools": ["gmail_read_email", "github_search_code"],
        "steps": [
            {"tool": "gmail_read_email", "args": {"message_id": "msg_001"}},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "test_payment"}},
        ],
    },
]


def build_tier3(count: int = 50) -> list[TaskRecord]:
    """Build Tier 3 multi-step tasks. Target: 50."""
    rng = random.Random(42)
    tasks = []
    for i, spec in enumerate(_MULTI_STEP_TASKS[:count]):
        tasks.append(TaskRecord(
            id=f"v3-t3-multi-{i+1}",
            tier="tier3_multi_step",
            prompt=spec["prompt"],
            ground_truth=spec["ground_truth"],
            expected_tools=spec["expected_tools"],
            metadata={
                "category": "multi_step",
                "steps": spec["steps"],
                "num_steps": len(spec["steps"]),
            },
        ))
    rng.shuffle(tasks)
    return tasks[:count]


# ---------------------------------------------------------------------------
# Tier 4 — Error Recovery (20 tasks)
# ---------------------------------------------------------------------------

_ERROR_RECOVERY_TASKS: list[dict] = [
    {
        "prompt": "Search for the payments service code in the backend",
        "ground_truth": "No direct match for 'payments service', but PaymentProcessor found in src/api/payments.py",
        "expected_tools": ["github_search_code", "github_search_code"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "payments service"}, "expect_empty": True},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "payment"}},
        ],
        "recovery_hint": "First search returns empty — retry with broader query 'payment'",
    },
    {
        "prompt": "Read the README from acmecorp/api",
        "ground_truth": "No repo acmecorp/api found. The correct repo is acmecorp/backend with README about Production API service",
        "expected_tools": ["github_read_file", "github_read_file"],
        "steps": [
            {"tool": "github_read_file", "args": {"repo": "acmecorp/api", "path": "README.md"}, "expect_error": True},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "README.md"}},
        ],
        "recovery_hint": "File not found in acmecorp/api — try acmecorp/backend instead",
    },
    {
        "prompt": "Find the billing module in the backend codebase",
        "ground_truth": "No 'billing' module found. The closest match is PaymentProcessor in src/api/payments.py",
        "expected_tools": ["github_search_code", "github_search_code"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "billing"}, "expect_empty": True},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "payment"}},
        ],
        "recovery_hint": "No billing module — payments.py is the closest match",
    },
    {
        "prompt": "Read the config.yaml from the backend repo",
        "ground_truth": "No config.yaml found. Available files include src/api/auth.py, src/api/payments.py, etc.",
        "expected_tools": ["github_read_file", "github_search_code"],
        "steps": [
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "config.yaml"}, "expect_error": True},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "config"}},
        ],
        "recovery_hint": "config.yaml not found — search for config references instead",
    },
    {
        "prompt": "Find the database migration files in acmecorp/backend",
        "ground_truth": "No migration files found. The codebase has models in src/models/user.py but no separate migrations directory",
        "expected_tools": ["github_search_code", "github_search_code"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "migration"}, "expect_empty": True},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "model"}},
        ],
        "recovery_hint": "No migration files — check models directory instead",
    },
    {
        "prompt": "Search for the user registration endpoint",
        "ground_truth": "No registration endpoint found. Related auth code in src/api/auth.py handles authentication",
        "expected_tools": ["github_search_code", "github_search_code"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "registration"}, "expect_empty": True},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "authenticate"}},
        ],
        "recovery_hint": "No registration endpoint — check authentication code instead",
    },
    {
        "prompt": "Read the Dockerfile from acmecorp/backend",
        "ground_truth": "No Dockerfile found in mock data. Architecture doc mentions deployment on AWS ECS",
        "expected_tools": ["github_read_file", "github_read_file"],
        "steps": [
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "Dockerfile"}, "expect_error": True},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "docs/architecture.md"}},
        ],
        "recovery_hint": "No Dockerfile — check architecture docs for deployment info",
    },
    {
        "prompt": "Find the requirements.txt in the infra repo",
        "ground_truth": "File not found in mock. README mentions pip install -r requirements.txt for the backend",
        "expected_tools": ["github_read_file", "github_read_file"],
        "steps": [
            {"tool": "github_read_file", "args": {"repo": "acmecorp/infra", "path": "requirements.txt"}, "expect_error": True},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "README.md"}},
        ],
        "recovery_hint": "Not in infra repo — check backend repo README for dependency info",
    },
    {
        "prompt": "Search Drive for the quarterly business review deck",
        "ground_truth": "No QBR deck found. Closest match: Q1 2025 Product Roadmap with revenue targets",
        "expected_tools": ["drive_search", "drive_search"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "quarterly business review"}, "expect_empty": True},
            {"tool": "drive_search", "args": {"query": "Q1"}},
        ],
        "recovery_hint": "No QBR deck — try searching for Q1 roadmap",
    },
    {
        "prompt": "Find the project timeline document in Drive",
        "ground_truth": "No timeline document. Q1 2025 Product Roadmap has project priorities and dates",
        "expected_tools": ["drive_search", "drive_search"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "timeline"}, "expect_empty": True},
            {"tool": "drive_search", "args": {"query": "Roadmap"}},
        ],
        "recovery_hint": "No timeline doc — roadmap has project schedule info",
    },
    {
        "prompt": "Search for the incident postmortem in Drive",
        "ground_truth": "No postmortem found. API Security Audit Report is closest to incident documentation",
        "expected_tools": ["drive_search", "drive_search"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "postmortem"}, "expect_empty": True},
            {"tool": "drive_search", "args": {"query": "Audit"}},
        ],
        "recovery_hint": "No postmortem — security audit report covers incident findings",
    },
    {
        "prompt": "Read the design spec from Drive (file ID doc_005)",
        "ground_truth": "File doc_005 not found. Available design-related docs: API Security Audit Report (doc_003)",
        "expected_tools": ["drive_read_file", "drive_search"],
        "steps": [
            {"tool": "drive_read_file", "args": {"file_id": "doc_005"}, "expect_error": True},
            {"tool": "drive_search", "args": {"query": "design"}},
        ],
        "recovery_hint": "File ID does not exist — search for design docs instead",
    },
    {
        "prompt": "Find emails about the database migration",
        "ground_truth": "No emails about database migration. Closest: payment processor outage email mentions infrastructure changes",
        "expected_tools": ["gmail_search", "gmail_search"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "database migration"}, "expect_empty": True},
            {"tool": "gmail_search", "args": {"query": "infrastructure"}},
        ],
        "recovery_hint": "No migration emails — broaden search to infrastructure topics",
    },
    {
        "prompt": "Search for emails from frank@acmecorp.com",
        "ground_truth": "No emails from Frank (he hasn't started yet). Eve's email announces Frank Torres joining Monday",
        "expected_tools": ["gmail_search", "gmail_search"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "from:frank@acmecorp.com"}, "expect_empty": True},
            {"tool": "gmail_search", "args": {"query": "Frank"}},
        ],
        "recovery_hint": "Frank hasn't sent emails yet — search for mentions of Frank",
    },
    {
        "prompt": "Find emails about the CI/CD pipeline",
        "ground_truth": "No CI/CD emails. Closest: Alice's email about deployment (payment processor fix) and Dave's audit mentioning infrastructure",
        "expected_tools": ["gmail_search", "gmail_search"],
        "steps": [
            {"tool": "gmail_search", "args": {"query": "CI/CD pipeline"}, "expect_empty": True},
            {"tool": "gmail_search", "args": {"query": "deploy"}},
        ],
        "recovery_hint": "No CI/CD emails — try deployment-related search",
    },
    {
        "prompt": "Read the email with message ID msg_010",
        "ground_truth": "Message msg_010 not found. Available recent emails include payment outage, security audit, sprint planning, new hire",
        "expected_tools": ["gmail_read_email", "gmail_search"],
        "steps": [
            {"tool": "gmail_read_email", "args": {"message_id": "msg_010"}, "expect_error": True},
            {"tool": "gmail_search", "args": {"query": ""}},
        ],
        "recovery_hint": "Invalid message ID — search for recent emails to find correct one",
    },
    {
        "prompt": "Find the logging module in the backend",
        "ground_truth": "No logging module found. Architecture mentions FastAPI routes and external integrations",
        "expected_tools": ["github_search_code", "github_read_file"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "logging"}, "expect_empty": True},
            {"tool": "github_read_file", "args": {"repo": "acmecorp/backend", "path": "docs/architecture.md"}},
        ],
        "recovery_hint": "No logging module — check architecture docs for system overview",
    },
    {
        "prompt": "Look for the API rate limiter code in acmecorp/backend",
        "ground_truth": "No rate limiter code yet. Issue #41 filed to add rate limiting, and PR #15 includes rate_limit.py as new file",
        "expected_tools": ["github_search_code", "github_list_issues"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "rate limit"}, "expect_empty": True},
            {"tool": "github_list_issues", "args": {"repo": "acmecorp/backend", "state": "open", "labels": "enhancement"}},
        ],
        "recovery_hint": "Rate limiter not implemented yet — check if there's an issue for it",
    },
    {
        "prompt": "Find the employee handbook in Drive",
        "ground_truth": "No employee handbook. Engineering Onboarding Guide is the closest match for new employee documentation",
        "expected_tools": ["drive_search", "drive_search"],
        "steps": [
            {"tool": "drive_search", "args": {"query": "employee handbook"}, "expect_empty": True},
            {"tool": "drive_search", "args": {"query": "Onboarding"}},
        ],
        "recovery_hint": "No handbook — onboarding guide is closest employee documentation",
    },
    {
        "prompt": "Search for the error handling middleware in the backend",
        "ground_truth": "No error handling middleware found. Auth code in auth.py raises AuthError; payments.py raises ValueError",
        "expected_tools": ["github_search_code", "github_search_code"],
        "steps": [
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "error handling middleware"}, "expect_empty": True},
            {"tool": "github_search_code", "args": {"repo": "acmecorp/backend", "query": "Error"}},
        ],
        "recovery_hint": "No middleware found — search for Error references in codebase",
    },
]


def build_tier4(count: int = 20) -> list[TaskRecord]:
    """Build Tier 4 error recovery tasks. Target: 20."""
    rng = random.Random(42)
    tasks = []
    for i, spec in enumerate(_ERROR_RECOVERY_TASKS[:count]):
        tasks.append(TaskRecord(
            id=f"v3-t4-recovery-{i+1}",
            tier="tier4_error_recovery",
            prompt=spec["prompt"],
            ground_truth=spec["ground_truth"],
            expected_tools=spec["expected_tools"],
            metadata={
                "category": "error_recovery",
                "steps": spec["steps"],
                "recovery_hint": spec["recovery_hint"],
            },
            error_injection_policy={
                "enabled": False,
                "note": "Error comes from natural mock behavior, not injection",
            },
        ))
    rng.shuffle(tasks)
    return tasks[:count]


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def build_all() -> dict[str, list[TaskRecord]]:
    """Build all tiers and return as a dict."""
    return {
        "tier1": build_tier1(100),
        "tier2": build_tier2(80),
        "tier3": build_tier3(50),
        "tier4": build_tier4(20),
    }
