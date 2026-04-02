"""GitHub API connector — real API calls using personal access token."""

import base64
import httpx
from config import GITHUB_TOKEN

API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _auth_headers() -> dict:
    h = dict(HEADERS)
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


async def call_github(method: str, args: dict) -> dict:
    """Dispatch to the correct GitHub API method."""
    handlers = {
        "search_repos": _search_repos,
        "read_file": _read_file,
        "list_pull_requests": _list_pull_requests,
        "get_commit_history": _get_commit_history,
        "create_issue": _create_issue,
    }
    handler = handlers.get(method)
    if not handler:
        return {"error": f"Unknown GitHub method: {method}"}
    return await handler(args)


async def _search_repos(args: dict) -> dict:
    query = args.get("query", "")
    language = args.get("language", "")
    sort = args.get("sort", "stars")

    q = query
    if language:
        q += f" language:{language}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/search/repositories",
            params={"q": q, "sort": sort, "per_page": 5},
            headers=_auth_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "results": [
            {
                "name": r["full_name"],
                "description": r.get("description", ""),
                "stars": r["stargazers_count"],
                "language": r.get("language", ""),
                "updated": r["updated_at"],
            }
            for r in data.get("items", [])[:5]
        ],
        "total_count": data.get("total_count", 0),
    }


async def _read_file(args: dict) -> dict:
    repo = args.get("repo", "")
    path = args.get("path", "")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/repos/{repo}/contents/{path}",
            headers=_auth_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("encoding") == "base64":
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    else:
        content = data.get("content", "")

    return {"path": path, "content": content, "size": data.get("size", 0)}


async def _list_pull_requests(args: dict) -> dict:
    repo = args.get("repo", "")
    state = args.get("state", "open")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/repos/{repo}/pulls",
            params={"state": state, "per_page": 10},
            headers=_auth_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "pull_requests": [
            {
                "number": pr["number"],
                "title": pr["title"],
                "author": pr["user"]["login"],
                "status": pr["state"],
                "created": pr["created_at"],
            }
            for pr in data[:10]
        ],
    }


async def _get_commit_history(args: dict) -> dict:
    repo = args.get("repo", "")
    branch = args.get("branch", "main")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/repos/{repo}/commits",
            params={"sha": branch, "per_page": 5},
            headers=_auth_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "commits": [
            {
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
            }
            for c in data[:5]
        ],
    }


async def _create_issue(args: dict) -> dict:
    repo = args.get("repo", "")
    title = args.get("title", "")
    body = args.get("body", "")

    # Safety: in demo context, simulate instead of creating real issues
    if not GITHUB_TOKEN:
        return {"simulated": True, "title": title, "note": "No GitHub token configured"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API}/repos/{repo}/issues",
            json={"title": title, "body": body},
            headers=_auth_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {"number": data["number"], "url": data["html_url"], "title": data["title"]}
