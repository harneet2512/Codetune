"""Gmail API connector — requires OAuth2 tokens from Google."""

from auth.google_oauth import get_credentials

API = "https://gmail.googleapis.com/gmail/v1"


async def call_gmail(method: str, args: dict) -> dict:
    """Dispatch to Gmail API. Requires authenticated credentials."""
    creds = get_credentials()
    if not creds:
        return {"error": "Gmail not connected. Complete OAuth flow first."}

    handlers = {
        "search_emails": _search_emails,
        "read_email": _read_email,
        "send_email": _send_email,
        "list_threads": _list_threads,
    }
    handler = handlers.get(method)
    if not handler:
        return {"error": f"Unknown Gmail method: {method}"}
    return await handler(args, creds)


async def _search_emails(args: dict, creds) -> dict:
    import httpx

    query = args.get("query", "")
    from_addr = args.get("from", "")
    q = query
    if from_addr:
        q += f" from:{from_addr}"

    headers = {"Authorization": f"Bearer {creds.token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/users/me/messages",
            params={"q": q, "maxResults": 5},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    messages = []
    for msg_ref in data.get("messages", [])[:5]:
        detail = await _fetch_message_metadata(client, msg_ref["id"], headers)
        messages.append(detail)

    return {"emails": messages, "total": data.get("resultSizeEstimate", 0)}


async def _fetch_message_metadata(client, msg_id: str, headers: dict) -> dict:
    import httpx

    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{API}/users/me/messages/{msg_id}",
            params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    headers_list = data.get("payload", {}).get("headers", [])
    header_map = {h["name"]: h["value"] for h in headers_list}

    return {
        "id": msg_id,
        "from": header_map.get("From", ""),
        "subject": header_map.get("Subject", ""),
        "date": header_map.get("Date", ""),
        "snippet": data.get("snippet", ""),
    }


async def _read_email(args: dict, creds) -> dict:
    import httpx

    msg_id = args.get("id", "")
    headers = {"Authorization": f"Bearer {creds.token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/users/me/messages/{msg_id}",
            params={"format": "full"},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    # Extract plain text body
    body = _extract_body(data.get("payload", {}))
    headers_list = data.get("payload", {}).get("headers", [])
    header_map = {h["name"]: h["value"] for h in headers_list}

    return {
        "id": msg_id,
        "from": header_map.get("From", ""),
        "subject": header_map.get("Subject", ""),
        "body": body,
    }


def _extract_body(payload: dict) -> str:
    """Extract plain text body from MIME payload."""
    import base64

    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""


async def _send_email(args: dict, creds) -> dict:
    # Safety: create draft instead of sending
    return {
        "status": "draft_created",
        "note": "In demo mode, emails are drafted but not sent.",
        "to": args.get("to", ""),
        "subject": args.get("subject", ""),
    }


async def _list_threads(args: dict, creds) -> dict:
    import httpx

    query = args.get("query", "")
    headers = {"Authorization": f"Bearer {creds.token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/users/me/threads",
            params={"q": query, "maxResults": 5},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "threads": [
            {"id": t["id"], "snippet": t.get("snippet", "")}
            for t in data.get("threads", [])[:5]
        ],
    }
