"""GitHub connector tools using the REST API v3.

Each function hits the real GitHub API and returns structured dicts.
Pass a personal access token via the ``token`` parameter or set the
``GITHUB_TOKEN`` environment variable.
"""

from __future__ import annotations

import os
from typing import Any

import requests

_API = "https://api.github.com"
_MAX_FILE_CHARS = 2000
_MAX_LIST_ITEMS = 20
_TIMEOUT = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers(token: str | None) -> dict[str, str]:
    tok = token or os.environ.get("GITHUB_TOKEN", "")
    h: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _err(message: str) -> dict[str, Any]:
    return {"error": message}


def _get(url: str, token: str | None, params: dict[str, Any] | None = None) -> requests.Response:
    return requests.get(url, headers=_headers(token), params=params, timeout=_TIMEOUT)


def _post(url: str, token: str | None, json_body: dict[str, Any]) -> requests.Response:
    return requests.post(url, headers=_headers(token), json=json_body, timeout=_TIMEOUT)


def _put(url: str, token: str | None, json_body: dict[str, Any]) -> requests.Response:
    return requests.put(url, headers=_headers(token), json=json_body, timeout=_TIMEOUT)


def _check(resp: requests.Response) -> dict[str, Any] | None:
    """Return an error dict if the response is not 2xx, else None."""
    if resp.ok:
        return None
    try:
        detail = resp.json().get("message", resp.text[:200])
    except Exception:
        detail = resp.text[:200]
    return _err(f"GitHub API {resp.status_code}: {detail}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def github_search_code(
    repo: str,
    query: str,
    token: str | None = None,
) -> dict[str, Any]:
    """Search code in a repository.

    Args:
        repo: Owner/repo (e.g. ``"octocat/Hello-World"``).
        query: Search string.
        token: GitHub PAT. Falls back to ``GITHUB_TOKEN`` env var.

    Returns:
        Dict with ``matches`` list (path, repository, text_matches) or ``error``.
    """
    try:
        q = f"{query} repo:{repo}"
        resp = _get(f"{_API}/search/code", token, params={"q": q, "per_page": _MAX_LIST_ITEMS})
        if err := _check(resp):
            return err
        data = resp.json()
        matches = []
        for item in data.get("items", [])[:_MAX_LIST_ITEMS]:
            snippets = []
            for tm in item.get("text_matches", []):
                fragment = tm.get("fragment", "")
                if len(fragment) > 300:
                    fragment = fragment[:300] + "..."
                snippets.append(fragment)
            matches.append({
                "path": item.get("path", ""),
                "url": item.get("html_url", ""),
                "snippets": snippets,
            })
        return {"total_count": data.get("total_count", 0), "matches": matches}
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")


def github_read_file(
    repo: str,
    path: str,
    ref: str = "main",
    token: str | None = None,
) -> dict[str, Any]:
    """Read a file from a repository.

    Args:
        repo: Owner/repo.
        path: File path within the repo.
        ref: Branch or commit ref.
        token: GitHub PAT.

    Returns:
        Dict with ``path``, ``content`` (truncated to 2000 chars), ``size``, ``sha``.
    """
    try:
        resp = _get(f"{_API}/repos/{repo}/contents/{path}", token, params={"ref": ref})
        if err := _check(resp):
            return err
        data = resp.json()
        if data.get("type") != "file":
            return _err(f"Path is a {data.get('type', 'unknown')}, not a file")
        import base64
        content_raw = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        truncated = len(content_raw) > _MAX_FILE_CHARS
        content = content_raw[:_MAX_FILE_CHARS]
        if truncated:
            content += f"\n... [truncated, {len(content_raw)} chars total]"
        return {
            "path": data.get("path", path),
            "sha": data.get("sha", ""),
            "size": data.get("size", 0),
            "content": content,
            "truncated": truncated,
        }
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")


def github_list_issues(
    repo: str,
    state: str = "open",
    labels: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """List issues in a repository.

    Args:
        repo: Owner/repo.
        state: ``"open"``, ``"closed"``, or ``"all"``.
        labels: Comma-separated label names to filter by.
        token: GitHub PAT.

    Returns:
        Dict with ``issues`` list.
    """
    try:
        params: dict[str, Any] = {"state": state, "per_page": _MAX_LIST_ITEMS}
        if labels:
            params["labels"] = labels
        resp = _get(f"{_API}/repos/{repo}/issues", token, params=params)
        if err := _check(resp):
            return err
        issues = []
        for item in resp.json()[:_MAX_LIST_ITEMS]:
            if "pull_request" in item:
                continue  # skip PRs from issues endpoint
            issues.append({
                "number": item["number"],
                "title": item["title"],
                "state": item["state"],
                "labels": [l["name"] for l in item.get("labels", [])],
                "author": item.get("user", {}).get("login", ""),
                "created_at": item.get("created_at", ""),
                "comments": item.get("comments", 0),
            })
        return {"count": len(issues), "issues": issues}
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")


def github_list_prs(
    repo: str,
    state: str = "open",
    token: str | None = None,
) -> dict[str, Any]:
    """List pull requests in a repository.

    Args:
        repo: Owner/repo.
        state: ``"open"``, ``"closed"``, or ``"all"``.
        token: GitHub PAT.

    Returns:
        Dict with ``pull_requests`` list.
    """
    try:
        params: dict[str, Any] = {"state": state, "per_page": _MAX_LIST_ITEMS}
        resp = _get(f"{_API}/repos/{repo}/pulls", token, params=params)
        if err := _check(resp):
            return err
        prs = []
        for item in resp.json()[:_MAX_LIST_ITEMS]:
            prs.append({
                "number": item["number"],
                "title": item["title"],
                "state": item["state"],
                "author": item.get("user", {}).get("login", ""),
                "head": item.get("head", {}).get("ref", ""),
                "base": item.get("base", {}).get("ref", ""),
                "created_at": item.get("created_at", ""),
                "draft": item.get("draft", False),
            })
        return {"count": len(prs), "pull_requests": prs}
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")


def github_read_pr(
    repo: str,
    pr_number: int,
    token: str | None = None,
) -> dict[str, Any]:
    """Read pull request details including a diff summary.

    Args:
        repo: Owner/repo.
        pr_number: PR number.
        token: GitHub PAT.

    Returns:
        Dict with PR metadata and a list of changed files.
    """
    try:
        resp = _get(f"{_API}/repos/{repo}/pulls/{pr_number}", token)
        if err := _check(resp):
            return err
        pr = resp.json()

        # Fetch changed files
        files_resp = _get(f"{_API}/repos/{repo}/pulls/{pr_number}/files", token, params={"per_page": _MAX_LIST_ITEMS})
        changed_files = []
        if files_resp.ok:
            for f in files_resp.json()[:_MAX_LIST_ITEMS]:
                changed_files.append({
                    "filename": f.get("filename", ""),
                    "status": f.get("status", ""),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                })

        return {
            "number": pr["number"],
            "title": pr["title"],
            "body": (pr.get("body") or "")[:_MAX_FILE_CHARS],
            "state": pr["state"],
            "author": pr.get("user", {}).get("login", ""),
            "head": pr.get("head", {}).get("ref", ""),
            "base": pr.get("base", {}).get("ref", ""),
            "mergeable": pr.get("mergeable"),
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "changed_files_count": pr.get("changed_files", 0),
            "changed_files": changed_files,
        }
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")


def github_create_branch(
    repo: str,
    branch_name: str,
    from_ref: str = "main",
    token: str | None = None,
) -> dict[str, Any]:
    """Create a new branch in a repository.

    Args:
        repo: Owner/repo.
        branch_name: Name for the new branch.
        from_ref: Source branch or commit SHA to branch from.
        token: GitHub PAT.

    Returns:
        Dict with ``ref`` and ``sha`` of the new branch.
    """
    try:
        # Get the SHA of the source ref
        ref_resp = _get(f"{_API}/repos/{repo}/git/ref/heads/{from_ref}", token)
        if err := _check(ref_resp):
            return _err(f"Could not resolve ref '{from_ref}': {err['error']}")
        sha = ref_resp.json()["object"]["sha"]

        # Create the new branch
        resp = _post(
            f"{_API}/repos/{repo}/git/refs",
            token,
            {"ref": f"refs/heads/{branch_name}", "sha": sha},
        )
        if err := _check(resp):
            return err
        data = resp.json()
        return {"ref": data["ref"], "sha": data["object"]["sha"]}
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")


def github_commit_file(
    repo: str,
    path: str,
    content: str,
    message: str,
    branch: str,
    token: str | None = None,
) -> dict[str, Any]:
    """Create or update a file in a repository.

    Args:
        repo: Owner/repo.
        path: File path in the repo.
        content: New file content (plain text, will be base64-encoded).
        message: Commit message.
        branch: Target branch.
        token: GitHub PAT.

    Returns:
        Dict with ``path``, ``sha``, and ``commit_sha``.
    """
    try:
        import base64
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

        # Check if file already exists to get its SHA (required for updates)
        existing_resp = _get(f"{_API}/repos/{repo}/contents/{path}", token, params={"ref": branch})
        body: dict[str, Any] = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        if existing_resp.ok:
            body["sha"] = existing_resp.json().get("sha", "")

        resp = _put(f"{_API}/repos/{repo}/contents/{path}", token, body)
        if err := _check(resp):
            return err
        data = resp.json()
        return {
            "path": data.get("content", {}).get("path", path),
            "sha": data.get("content", {}).get("sha", ""),
            "commit_sha": data.get("commit", {}).get("sha", ""),
        }
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")


def github_create_pr(
    repo: str,
    title: str,
    body: str,
    head_branch: str,
    base: str = "main",
    token: str | None = None,
) -> dict[str, Any]:
    """Create a pull request.

    Args:
        repo: Owner/repo.
        title: PR title.
        body: PR description.
        head_branch: Source branch.
        base: Target branch.
        token: GitHub PAT.

    Returns:
        Dict with ``number``, ``url``, ``title``.
    """
    try:
        resp = _post(
            f"{_API}/repos/{repo}/pulls",
            token,
            {"title": title, "body": body, "head": head_branch, "base": base},
        )
        if err := _check(resp):
            return err
        data = resp.json()
        return {
            "number": data["number"],
            "url": data.get("html_url", ""),
            "title": data["title"],
            "state": data["state"],
        }
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")


def github_create_issue(
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Create an issue in a repository.

    Args:
        repo: Owner/repo.
        title: Issue title.
        body: Issue body.
        labels: Optional list of label names.
        token: GitHub PAT.

    Returns:
        Dict with ``number``, ``url``, ``title``.
    """
    try:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        resp = _post(f"{_API}/repos/{repo}/issues", token, payload)
        if err := _check(resp):
            return err
        data = resp.json()
        return {
            "number": data["number"],
            "url": data.get("html_url", ""),
            "title": data["title"],
        }
    except requests.RequestException as exc:
        return _err(f"Request failed: {exc}")
