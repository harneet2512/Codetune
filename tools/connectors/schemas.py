"""Tool definitions for the model's system prompt.

These schemas define the tools that the fine-tuned model sees during training
and inference. Each schema specifies the tool name, description, and typed
parameters. Export as JSON-serializable list via ``CONNECTOR_TOOL_SCHEMAS``.
"""

from __future__ import annotations

from typing import Any

CONNECTOR_TOOL_SCHEMAS: list[dict[str, Any]] = [
    # -----------------------------------------------------------------------
    # GitHub tools
    # -----------------------------------------------------------------------
    {
        "name": "github_search_code",
        "description": "Search code in a GitHub repository. Returns file matches with code snippets.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format (e.g. 'octocat/Hello-World')"},
            "query": {"type": "string", "description": "Code search query string"},
        },
    },
    {
        "name": "github_read_file",
        "description": "Read the contents of a file from a GitHub repository.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format"},
            "path": {"type": "string", "description": "File path within the repository"},
            "ref": {"type": "string", "description": "Branch, tag, or commit SHA (default: 'main')", "default": "main"},
        },
    },
    {
        "name": "github_list_issues",
        "description": "List issues in a GitHub repository. Can filter by state and labels.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format"},
            "state": {"type": "string", "description": "Filter by state: 'open', 'closed', or 'all' (default: 'open')", "default": "open"},
            "labels": {"type": "string", "description": "Comma-separated label names to filter by (optional)"},
        },
    },
    {
        "name": "github_list_prs",
        "description": "List pull requests in a GitHub repository.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format"},
            "state": {"type": "string", "description": "Filter by state: 'open', 'closed', or 'all' (default: 'open')", "default": "open"},
        },
    },
    {
        "name": "github_read_pr",
        "description": "Read pull request details including title, description, and changed files summary.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format"},
            "pr_number": {"type": "integer", "description": "Pull request number"},
        },
    },
    {
        "name": "github_create_branch",
        "description": "Create a new branch in a GitHub repository.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format"},
            "branch_name": {"type": "string", "description": "Name for the new branch"},
            "from_ref": {"type": "string", "description": "Source branch to create from (default: 'main')", "default": "main"},
        },
    },
    {
        "name": "github_commit_file",
        "description": "Create or update a file in a GitHub repository via a commit.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format"},
            "path": {"type": "string", "description": "File path in the repository"},
            "content": {"type": "string", "description": "New file content"},
            "message": {"type": "string", "description": "Commit message"},
            "branch": {"type": "string", "description": "Target branch for the commit"},
        },
    },
    {
        "name": "github_create_pr",
        "description": "Create a pull request in a GitHub repository.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format"},
            "title": {"type": "string", "description": "Pull request title"},
            "body": {"type": "string", "description": "Pull request description"},
            "head_branch": {"type": "string", "description": "Source branch with changes"},
            "base": {"type": "string", "description": "Target branch to merge into (default: 'main')", "default": "main"},
        },
    },
    {
        "name": "github_create_issue",
        "description": "Create an issue in a GitHub repository.",
        "parameters": {
            "repo": {"type": "string", "description": "Repository in owner/repo format"},
            "title": {"type": "string", "description": "Issue title"},
            "body": {"type": "string", "description": "Issue description"},
            "labels": {"type": "array", "description": "List of label names to apply (optional)"},
        },
    },
    # -----------------------------------------------------------------------
    # Google Drive tools
    # -----------------------------------------------------------------------
    {
        "name": "drive_search",
        "description": "Search files in Google Drive by name or content.",
        "parameters": {
            "query": {"type": "string", "description": "Search query to match against file names"},
            "max_results": {"type": "integer", "description": "Maximum number of results (default: 10, max: 20)", "default": 10},
        },
    },
    {
        "name": "drive_read_file",
        "description": "Read the contents of a Google Drive file. Supports Docs, Sheets, and plain text files.",
        "parameters": {
            "file_id": {"type": "string", "description": "Google Drive file ID"},
        },
    },
    {
        "name": "drive_list_recent",
        "description": "List recently modified files in Google Drive.",
        "parameters": {
            "max_results": {"type": "integer", "description": "Maximum number of results (default: 10, max: 20)", "default": 10},
        },
    },
    {
        "name": "drive_get_file_info",
        "description": "Get metadata for a Google Drive file including owner, modification date, and sharing info.",
        "parameters": {
            "file_id": {"type": "string", "description": "Google Drive file ID"},
        },
    },
    # -----------------------------------------------------------------------
    # Gmail tools
    # -----------------------------------------------------------------------
    {
        "name": "gmail_search",
        "description": "Search emails using Gmail query syntax (e.g. 'from:alice subject:meeting').",
        "parameters": {
            "query": {"type": "string", "description": "Gmail search query"},
            "max_results": {"type": "integer", "description": "Maximum number of results (default: 10, max: 20)", "default": 10},
        },
    },
    {
        "name": "gmail_read_email",
        "description": "Read the full content of an email including from, to, subject, and body.",
        "parameters": {
            "message_id": {"type": "string", "description": "Gmail message ID"},
        },
    },
    {
        "name": "gmail_send_email",
        "description": "Send an email via Gmail.",
        "parameters": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Plain text email body"},
        },
    },
    {
        "name": "gmail_list_labels",
        "description": "List all available Gmail labels for the authenticated user.",
        "parameters": {},
    },
]


def get_schemas() -> list[dict[str, Any]]:
    """Return a copy of all connector tool schemas."""
    return list(CONNECTOR_TOOL_SCHEMAS)


def get_schema_by_name(name: str) -> dict[str, Any] | None:
    """Look up a single tool schema by name."""
    for schema in CONNECTOR_TOOL_SCHEMAS:
        if schema["name"] == name:
            return schema
    return None
