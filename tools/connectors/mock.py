"""Mock implementations of connector tools for testing and training data generation.

All mocks return realistic but fake data seeded with a consistent "AcmeCorp"
company. Used during SFT data generation when you don't want to hit real APIs.

Usage::

    from tools.connectors.mock import MockConnectorRegistry

    registry = MockConnectorRegistry()
    result = registry.execute("github_list_issues", {"repo": "acmecorp/backend"})
"""

from __future__ import annotations

import json
import hashlib
from typing import Any

from tooltune.contracts import ToolCall, ToolObservation

from tools.connectors.schemas import CONNECTOR_TOOL_SCHEMAS


# ---------------------------------------------------------------------------
# Seed data — AcmeCorp fake company
# ---------------------------------------------------------------------------

_TEAM = ["alice", "bob", "carol", "dave", "eve"]
_REPOS = ["acmecorp/backend", "acmecorp/frontend", "acmecorp/infra", "acmecorp/ml-pipeline", "acmecorp/docs"]
_LABELS = ["bug", "enhancement", "good first issue", "urgent", "documentation", "backend", "frontend"]
_BRANCHES = ["main", "develop", "feature/auth-v2", "fix/payment-timeout", "feature/dashboard-charts"]

_FILES = {
    "src/api/auth.py": 'def authenticate(token: str) -> User:\n    """Validate JWT token and return user."""\n    decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])\n    user = db.users.get(decoded["sub"])\n    if not user:\n        raise AuthError("User not found")\n    return user\n',
    "src/api/payments.py": 'class PaymentProcessor:\n    def charge(self, amount: Decimal, currency: str, card_token: str) -> PaymentResult:\n        """Process a payment via Stripe."""\n        if amount <= 0:\n            raise ValueError("Amount must be positive")\n        return self.stripe.charges.create(\n            amount=int(amount * 100), currency=currency, source=card_token\n        )\n',
    "src/models/user.py": '@dataclass\nclass User:\n    id: str\n    email: str\n    name: str\n    role: str = "member"\n    created_at: datetime = field(default_factory=datetime.utcnow)\n    is_active: bool = True\n',
    "tests/test_auth.py": 'def test_authenticate_valid_token():\n    token = create_test_token(user_id="user_123")\n    user = authenticate(token)\n    assert user.id == "user_123"\n    assert user.is_active\n',
    "README.md": "# AcmeCorp Backend\n\nProduction API service for AcmeCorp platform.\n\n## Setup\n\n```bash\npip install -r requirements.txt\npython -m uvicorn src.main:app\n```\n",
    "docs/architecture.md": "# Architecture\n\nThe backend follows a layered architecture:\n- API layer (FastAPI routes)\n- Service layer (business logic)\n- Data layer (SQLAlchemy models)\n- External integrations (Stripe, SendGrid)\n",
}

_ISSUES = [
    {"number": 42, "title": "Payment timeout on large orders", "state": "open", "labels": ["bug", "urgent"], "author": "alice", "comments": 5},
    {"number": 41, "title": "Add rate limiting to auth endpoints", "state": "open", "labels": ["enhancement", "backend"], "author": "bob", "comments": 2},
    {"number": 40, "title": "Update user model to support teams", "state": "open", "labels": ["enhancement"], "author": "carol", "comments": 8},
    {"number": 39, "title": "Fix CORS headers for staging env", "state": "closed", "labels": ["bug"], "author": "dave", "comments": 1},
    {"number": 38, "title": "Document webhook integration", "state": "open", "labels": ["documentation"], "author": "eve", "comments": 0},
]

_PRS = [
    {"number": 15, "title": "feat: add JWT refresh token rotation", "state": "open", "author": "alice", "head": "feature/auth-v2", "base": "main", "draft": False},
    {"number": 14, "title": "fix: payment processor timeout handling", "state": "open", "author": "bob", "head": "fix/payment-timeout", "base": "main", "draft": False},
    {"number": 13, "title": "chore: update dependencies", "state": "open", "author": "carol", "head": "chore/deps-update", "base": "main", "draft": True},
    {"number": 12, "title": "feat: dashboard chart components", "state": "closed", "author": "dave", "head": "feature/dashboard-charts", "base": "main", "draft": False},
]

_DRIVE_FILES = [
    {"id": "doc_001", "name": "Q1 2025 Product Roadmap", "mime_type": "application/vnd.google-apps.document", "modified_time": "2025-03-15T10:30:00Z", "owners": ["Alice Chen"]},
    {"id": "sheet_001", "name": "Revenue Tracker 2025", "mime_type": "application/vnd.google-apps.spreadsheet", "modified_time": "2025-03-20T14:00:00Z", "owners": ["Bob Martinez"]},
    {"id": "doc_002", "name": "Engineering Onboarding Guide", "mime_type": "application/vnd.google-apps.document", "modified_time": "2025-02-28T09:15:00Z", "owners": ["Carol Davis"]},
    {"id": "doc_003", "name": "API Security Audit Report", "mime_type": "application/vnd.google-apps.document", "modified_time": "2025-03-18T16:45:00Z", "owners": ["Dave Kim"]},
    {"id": "sheet_002", "name": "Sprint Planning Board", "mime_type": "application/vnd.google-apps.spreadsheet", "modified_time": "2025-03-22T11:00:00Z", "owners": ["Eve Johnson"]},
    {"id": "pdf_001", "name": "SOC2 Compliance Checklist.pdf", "mime_type": "application/pdf", "modified_time": "2025-01-10T08:00:00Z", "owners": ["Alice Chen"]},
]

_DRIVE_CONTENTS = {
    "doc_001": "Q1 2025 Product Roadmap\n\nPriorities:\n1. Launch self-serve billing portal (Feb)\n2. Ship team collaboration features (Mar)\n3. SOC2 Type II certification (ongoing)\n4. Mobile app beta (Mar 30)\n\nKey Metrics:\n- MRR target: $250K\n- DAU target: 5,000\n- Churn target: <3%\n",
    "sheet_001": "Month,Revenue,Customers,Churn\nJan 2025,$180K,320,2.1%\nFeb 2025,$210K,355,1.8%\nMar 2025,$245K,390,2.4%\n",
    "doc_002": "Engineering Onboarding Guide\n\nWelcome to AcmeCorp Engineering!\n\n1. Dev Environment Setup\n   - Clone repos: backend, frontend, infra\n   - Run `make setup` in each repo\n   - Get credentials from 1Password vault 'Engineering'\n\n2. Architecture Overview\n   - Monorepo backend (Python/FastAPI)\n   - React frontend with TypeScript\n   - PostgreSQL + Redis\n   - Deployed on AWS ECS\n",
    "doc_003": "API Security Audit Report\n\nDate: March 18, 2025\nAuditor: External Security Team\n\nFindings:\n- HIGH: JWT tokens lack expiry validation in 2 endpoints\n- MEDIUM: Rate limiting not enforced on /api/auth/login\n- LOW: CORS allows wildcard in staging\n\nRecommendations:\n1. Implement token refresh rotation (PR #15 in progress)\n2. Add rate limiting middleware (Issue #41 filed)\n3. Restrict CORS to known origins\n",
}

_EMAILS = [
    {"id": "msg_001", "thread_id": "thread_001", "subject": "Re: Payment processor outage", "from": "alice@acmecorp.com", "to": "engineering@acmecorp.com", "date": "Mon, 24 Mar 2025 09:15:00 -0700", "snippet": "The Stripe webhook timeout issue has been resolved. Bob's PR #14 fixes the retry logic.", "body": "Team,\n\nThe Stripe webhook timeout issue has been resolved. Bob's PR #14 fixes the retry logic by adding exponential backoff.\n\nKey changes:\n- Added 3-retry with exponential backoff for webhook delivery\n- Increased timeout from 5s to 15s for payment confirmation\n- Added dead letter queue for failed webhooks\n\nPlease review the PR when you get a chance.\n\nBest,\nAlice"},
    {"id": "msg_002", "thread_id": "thread_002", "subject": "SOC2 audit - action items", "from": "dave@acmecorp.com", "to": "alice@acmecorp.com", "date": "Tue, 18 Mar 2025 16:45:00 -0700", "snippet": "Attached the security audit report. Three findings need immediate attention.", "body": "Hi Alice,\n\nAttached the security audit report from the external team. Three findings need immediate attention:\n\n1. JWT token expiry validation (HIGH) - 2 endpoints skip validation\n2. Rate limiting on login (MEDIUM) - no protection against brute force\n3. CORS wildcard in staging (LOW) - should restrict to known origins\n\nI've filed Issue #41 for the rate limiting work. Can you prioritize the JWT fix?\n\nThanks,\nDave"},
    {"id": "msg_003", "thread_id": "thread_003", "subject": "Sprint planning - March 24", "from": "carol@acmecorp.com", "to": "engineering@acmecorp.com", "date": "Mon, 24 Mar 2025 08:00:00 -0700", "snippet": "Sprint planning at 2pm today. Please update your tickets in Linear.", "body": "Hi team,\n\nSprint planning at 2pm today in the Elm conference room.\n\nPlease:\n1. Update your Linear tickets with current status\n2. Flag any blockers\n3. Review the sprint board before the meeting\n\nAgenda:\n- Review previous sprint velocity\n- Triage new issues\n- Assign sprint stories\n\nSee you there!\nCarol"},
    {"id": "msg_004", "thread_id": "thread_004", "subject": "New team member starting Monday", "from": "eve@acmecorp.com", "to": "engineering@acmecorp.com", "date": "Fri, 21 Mar 2025 14:00:00 -0700", "snippet": "Frank Torres joins as Senior Backend Engineer on Monday.", "body": "Team,\n\nExcited to announce that Frank Torres will be joining us as Senior Backend Engineer starting Monday, March 24!\n\nFrank comes from Datadog where he worked on their metrics pipeline. He'll be focusing on our observability and monitoring stack.\n\nCarol will be his onboarding buddy. Please make him feel welcome!\n\nBest,\nEve"},
]

_GMAIL_LABELS = [
    {"id": "INBOX", "name": "INBOX", "type": "system"},
    {"id": "SENT", "name": "SENT", "type": "system"},
    {"id": "DRAFT", "name": "DRAFT", "type": "system"},
    {"id": "TRASH", "name": "TRASH", "type": "system"},
    {"id": "SPAM", "name": "SPAM", "type": "system"},
    {"id": "Label_1", "name": "Engineering", "type": "user"},
    {"id": "Label_2", "name": "Security", "type": "user"},
    {"id": "Label_3", "name": "Sprint", "type": "user"},
    {"id": "Label_4", "name": "Hiring", "type": "user"},
]


# ---------------------------------------------------------------------------
# Deterministic seeding helper
# ---------------------------------------------------------------------------

def _seed_hash(seed: str) -> int:
    """Produce a deterministic integer from a seed string."""
    return int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)


# ---------------------------------------------------------------------------
# Mock tool implementations
# ---------------------------------------------------------------------------

def _mock_github_search_code(repo: str, query: str, **_: Any) -> dict[str, Any]:
    matches = []
    for path, content in _FILES.items():
        if query.lower() in content.lower() or query.lower() in path.lower():
            # Find snippet around the match
            lines = content.split("\n")
            snippet_lines = [l for l in lines if query.lower() in l.lower()][:2]
            snippet = "\n".join(snippet_lines) if snippet_lines else lines[0]
            matches.append({
                "path": path,
                "url": f"https://github.com/{repo}/blob/main/{path}",
                "snippets": [snippet[:300]],
            })
    return {"total_count": len(matches), "matches": matches[:20]}


def _mock_github_read_file(repo: str, path: str, ref: str = "main", **_: Any) -> dict[str, Any]:
    if path in _FILES:
        content = _FILES[path]
        return {
            "path": path,
            "sha": hashlib.sha1(content.encode()).hexdigest(),
            "size": len(content),
            "content": content[:2000],
            "truncated": len(content) > 2000,
        }
    return {"error": f"File not found: {path}"}


def _mock_github_list_issues(repo: str, state: str = "open", labels: str | None = None, **_: Any) -> dict[str, Any]:
    issues = _ISSUES
    if state != "all":
        issues = [i for i in issues if i["state"] == state]
    if labels:
        label_set = {l.strip() for l in labels.split(",")}
        issues = [i for i in issues if label_set & set(i["labels"])]
    result = []
    for i in issues:
        result.append({
            **i,
            "created_at": "2025-03-15T10:00:00Z",
        })
    return {"count": len(result), "issues": result}


def _mock_github_list_prs(repo: str, state: str = "open", **_: Any) -> dict[str, Any]:
    prs = _PRS
    if state != "all":
        prs = [p for p in prs if p["state"] == state]
    result = []
    for p in prs:
        result.append({
            **p,
            "created_at": "2025-03-10T09:00:00Z",
        })
    return {"count": len(result), "pull_requests": result}


def _mock_github_read_pr(repo: str, pr_number: int, **_: Any) -> dict[str, Any]:
    for p in _PRS:
        if p["number"] == pr_number:
            return {
                **p,
                "body": f"This PR implements changes for {p['title'].split(': ', 1)[-1]}.\n\n## Changes\n- Updated core logic\n- Added tests\n- Updated documentation",
                "mergeable": True,
                "additions": 142,
                "deletions": 38,
                "changed_files_count": 4,
                "changed_files": [
                    {"filename": "src/api/auth.py", "status": "modified", "additions": 65, "deletions": 12},
                    {"filename": "src/middleware/rate_limit.py", "status": "added", "additions": 45, "deletions": 0},
                    {"filename": "tests/test_auth.py", "status": "modified", "additions": 28, "deletions": 22},
                    {"filename": "docs/auth.md", "status": "modified", "additions": 4, "deletions": 4},
                ],
            }
    return {"error": f"PR #{pr_number} not found"}


def _mock_github_create_branch(repo: str, branch_name: str, from_ref: str = "main", **_: Any) -> dict[str, Any]:
    sha = hashlib.sha1(f"{repo}/{branch_name}/{from_ref}".encode()).hexdigest()
    return {"ref": f"refs/heads/{branch_name}", "sha": sha}


def _mock_github_commit_file(repo: str, path: str, content: str, message: str, branch: str, **_: Any) -> dict[str, Any]:
    sha = hashlib.sha1(content.encode()).hexdigest()
    commit_sha = hashlib.sha1(f"{message}/{sha}".encode()).hexdigest()
    return {"path": path, "sha": sha, "commit_sha": commit_sha}


def _mock_github_create_pr(repo: str, title: str, body: str, head_branch: str, base: str = "main", **_: Any) -> dict[str, Any]:
    number = _seed_hash(f"{repo}/{head_branch}") % 100 + 20
    return {
        "number": number,
        "url": f"https://github.com/{repo}/pull/{number}",
        "title": title,
        "state": "open",
    }


def _mock_github_create_issue(repo: str, title: str, body: str, labels: list[str] | None = None, **_: Any) -> dict[str, Any]:
    number = _seed_hash(f"{repo}/{title}") % 100 + 50
    return {
        "number": number,
        "url": f"https://github.com/{repo}/issues/{number}",
        "title": title,
    }


def _mock_drive_search(query: str, max_results: int = 10, **_: Any) -> dict[str, Any]:
    matches = [f for f in _DRIVE_FILES if query.lower() in f["name"].lower()][:max_results]
    return {"count": len(matches), "files": matches}


def _mock_drive_read_file(file_id: str, **_: Any) -> dict[str, Any]:
    if file_id in _DRIVE_CONTENTS:
        content = _DRIVE_CONTENTS[file_id]
        meta = next((f for f in _DRIVE_FILES if f["id"] == file_id), None)
        return {
            "id": file_id,
            "name": meta["name"] if meta else file_id,
            "mime_type": meta["mime_type"] if meta else "text/plain",
            "content": content[:2000],
            "truncated": len(content) > 2000,
        }
    return {"error": f"File not found: {file_id}"}


def _mock_drive_list_recent(max_results: int = 10, **_: Any) -> dict[str, Any]:
    files = sorted(_DRIVE_FILES, key=lambda f: f["modified_time"], reverse=True)[:max_results]
    return {"count": len(files), "files": files}


def _mock_drive_get_file_info(file_id: str, **_: Any) -> dict[str, Any]:
    meta = next((f for f in _DRIVE_FILES if f["id"] == file_id), None)
    if meta is None:
        return {"error": f"File not found: {file_id}"}
    return {
        **meta,
        "created_time": "2025-01-15T08:00:00Z",
        "shared": True,
        "size": str(_seed_hash(file_id) % 50000 + 1000),
        "web_link": f"https://docs.google.com/document/d/{file_id}/edit",
        "permissions": [
            {"role": "owner", "type": "user", "email": "alice@acmecorp.com", "display_name": "Alice Chen"},
            {"role": "reader", "type": "domain", "email": "", "display_name": "acmecorp.com"},
        ],
    }


def _mock_gmail_search(query: str, max_results: int = 10, **_: Any) -> dict[str, Any]:
    matches = []
    q_lower = query.lower()
    for email in _EMAILS:
        searchable = f"{email['subject']} {email['from']} {email['body']}".lower()
        if q_lower in searchable or not query.strip():
            matches.append({
                "id": email["id"],
                "thread_id": email["thread_id"],
                "subject": email["subject"],
                "from": email["from"],
                "date": email["date"],
                "snippet": email["snippet"],
            })
    return {"count": len(matches[:max_results]), "emails": matches[:max_results]}


def _mock_gmail_read_email(message_id: str, **_: Any) -> dict[str, Any]:
    email = next((e for e in _EMAILS if e["id"] == message_id), None)
    if email is None:
        return {"error": f"Message not found: {message_id}"}
    return {
        "id": email["id"],
        "thread_id": email["thread_id"],
        "from": email["from"],
        "to": email["to"],
        "cc": "",
        "subject": email["subject"],
        "date": email["date"],
        "body": email["body"],
        "truncated": False,
        "labels": ["INBOX", "Label_1"],
    }


def _mock_gmail_send_email(to: str, subject: str, body: str, **_: Any) -> dict[str, Any]:
    msg_id = f"msg_{hashlib.md5(f'{to}/{subject}'.encode()).hexdigest()[:8]}"
    return {
        "id": msg_id,
        "thread_id": f"thread_{msg_id}",
        "label_ids": ["SENT"],
    }


def _mock_gmail_list_labels(**_: Any) -> dict[str, Any]:
    return {"count": len(_GMAIL_LABELS), "labels": _GMAIL_LABELS}


# ---------------------------------------------------------------------------
# MockConnectorRegistry
# ---------------------------------------------------------------------------

class MockConnectorRegistry:
    """Drop-in replacement for ConnectorRegistry that returns fake AcmeCorp data.

    No network calls are made. Results are deterministic for a given input.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {
            "github_search_code": _mock_github_search_code,
            "github_read_file": _mock_github_read_file,
            "github_list_issues": _mock_github_list_issues,
            "github_list_prs": _mock_github_list_prs,
            "github_read_pr": _mock_github_read_pr,
            "github_create_branch": _mock_github_create_branch,
            "github_commit_file": _mock_github_commit_file,
            "github_create_pr": _mock_github_create_pr,
            "github_create_issue": _mock_github_create_issue,
            "drive_search": _mock_drive_search,
            "drive_read_file": _mock_drive_read_file,
            "drive_list_recent": _mock_drive_list_recent,
            "drive_get_file_info": _mock_drive_get_file_info,
            "gmail_search": _mock_gmail_search,
            "gmail_read_email": _mock_gmail_read_email,
            "gmail_send_email": _mock_gmail_send_email,
            "gmail_list_labels": _mock_gmail_list_labels,
        }
        self._schemas = {s["name"]: s for s in CONNECTOR_TOOL_SCHEMAS}

    def get_tool(self, name: str) -> Any | None:
        """Return the mock callable for a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return tool schemas (same as real registry — model sees identical definitions)."""
        return [self._schemas[name] for name in self._tools if name in self._schemas]

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        credentials: dict[str, Any] | None = None,
    ) -> ToolObservation:
        """Execute a mock tool. Credentials are ignored."""
        if tool_name not in self._tools:
            return ToolObservation(
                tool_name=tool_name,
                content=json.dumps({"error": f"Unknown tool: {tool_name}"}),
                is_error=True,
            )
        try:
            result = self._tools[tool_name](**arguments)
            is_error = "error" in result
            return ToolObservation(
                tool_name=tool_name,
                content=json.dumps(result, default=str),
                is_error=is_error,
            )
        except Exception as exc:
            return ToolObservation(
                tool_name=tool_name,
                content=json.dumps({"error": f"Mock execution failed: {exc}"}),
                is_error=True,
            )

    def execute_tool_call(
        self,
        tool_call: ToolCall,
        credentials: dict[str, Any] | None = None,
    ) -> ToolObservation:
        """Execute from a ToolCall contract object."""
        if not tool_call.valid:
            return ToolObservation(
                tool_name=tool_call.name,
                content=json.dumps({"error": tool_call.error or "Invalid tool call"}),
                is_error=True,
            )
        return self.execute(tool_call.name, tool_call.arguments, credentials)
