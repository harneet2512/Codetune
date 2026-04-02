"""Gmail connector tools using the Gmail API v1.

Authentication uses the same approach as Google Drive:
- Service account JSON path via ``GOOGLE_SERVICE_ACCOUNT_PATH`` env var, OR
- OAuth access token via ``GOOGLE_ACCESS_TOKEN`` env var, OR
- Pass ``credentials`` directly to each function.
"""

from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText
from typing import Any

_MAX_BODY_CHARS = 2000
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _err(message: str) -> dict[str, Any]:
    return {"error": message}


def _build_service(credentials: Any | None = None) -> Any:
    """Build a Gmail API service object.

    Args:
        credentials: A google.oauth2 credentials object. If None, resolves
            from environment variables.

    Returns:
        A googleapiclient Resource for Gmail v1.
    """
    try:
        from googleapiclient.discovery import build as build_discovery
    except ImportError:
        raise RuntimeError(
            "google-api-python-client is not installed. "
            "Install with: pip install google-api-python-client google-auth"
        )

    if credentials is None:
        credentials = _resolve_credentials()

    return build_discovery("gmail", "v1", credentials=credentials, cache_discovery=False)


def _resolve_credentials() -> Any:
    """Resolve credentials from environment variables."""
    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH")
    if sa_path:
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_file(sa_path, scopes=_SCOPES)

    access_token = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if access_token:
        from google.oauth2.credentials import Credentials
        return Credentials(token=access_token)

    raise RuntimeError(
        "No Google credentials found. Set GOOGLE_SERVICE_ACCOUNT_PATH or GOOGLE_ACCESS_TOKEN."
    )


def _extract_header(headers: list[dict[str, str]], name: str) -> str:
    """Extract a header value from a Gmail message headers list."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_body(payload: dict[str, Any]) -> str:
    """Recursively extract plain text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    # Direct body
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Multipart: recurse into parts
    parts = payload.get("parts", [])
    for part in parts:
        result = _decode_body(part)
        if result:
            return result

    # Fallback: try the body data directly
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return ""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def gmail_search(
    query: str,
    max_results: int = 10,
    credentials: Any | None = None,
) -> dict[str, Any]:
    """Search emails using Gmail query syntax.

    Args:
        query: Gmail search query (e.g. ``"from:alice subject:meeting"``).
        max_results: Maximum number of results (capped at 20).
        credentials: Google credentials object.

    Returns:
        Dict with ``emails`` list containing id, subject, from, date, snippet.
    """
    try:
        service = _build_service(credentials)
        max_results = min(max_results, 20)
        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        message_ids = result.get("messages", [])
        emails = []
        for msg_ref in message_ids:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="metadata",
                     metadataHeaders=["Subject", "From", "Date"])
                .execute()
            )
            headers = msg.get("payload", {}).get("headers", [])
            emails.append({
                "id": msg["id"],
                "thread_id": msg.get("threadId", ""),
                "subject": _extract_header(headers, "Subject"),
                "from": _extract_header(headers, "From"),
                "date": _extract_header(headers, "Date"),
                "snippet": msg.get("snippet", "")[:200],
            })
        return {"count": len(emails), "emails": emails}
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"Gmail API error: {exc}")


def gmail_read_email(
    message_id: str,
    credentials: Any | None = None,
) -> dict[str, Any]:
    """Read the full content of an email.

    Args:
        message_id: The Gmail message ID.
        credentials: Google credentials object.

    Returns:
        Dict with ``from``, ``to``, ``subject``, ``date``, ``body``.
    """
    try:
        service = _build_service(credentials)
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        body = _decode_body(msg.get("payload", {}))
        truncated = len(body) > _MAX_BODY_CHARS
        if truncated:
            body = body[:_MAX_BODY_CHARS] + f"\n... [truncated, {len(body)} chars total]"

        return {
            "id": message_id,
            "thread_id": msg.get("threadId", ""),
            "from": _extract_header(headers, "From"),
            "to": _extract_header(headers, "To"),
            "cc": _extract_header(headers, "Cc"),
            "subject": _extract_header(headers, "Subject"),
            "date": _extract_header(headers, "Date"),
            "body": body,
            "truncated": truncated,
            "labels": msg.get("labelIds", []),
        }
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"Gmail API error: {exc}")


def gmail_send_email(
    to: str,
    subject: str,
    body: str,
    credentials: Any | None = None,
) -> dict[str, Any]:
    """Send an email via Gmail.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain text email body.
        credentials: Google credentials object.

    Returns:
        Dict with ``id``, ``thread_id``, ``label_ids`` of the sent message.
    """
    try:
        service = _build_service(credentials)
        message = MIMEText(body)
        message["To"] = to
        message["Subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        result = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
        return {
            "id": result.get("id", ""),
            "thread_id": result.get("threadId", ""),
            "label_ids": result.get("labelIds", []),
        }
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"Gmail API error: {exc}")


def gmail_list_labels(
    credentials: Any | None = None,
) -> dict[str, Any]:
    """List all Gmail labels for the authenticated user.

    Args:
        credentials: Google credentials object.

    Returns:
        Dict with ``labels`` list containing id, name, type.
    """
    try:
        service = _build_service(credentials)
        result = service.users().labels().list(userId="me").execute()
        labels = []
        for label in result.get("labels", []):
            labels.append({
                "id": label["id"],
                "name": label["name"],
                "type": label.get("type", "user"),
            })
        return {"count": len(labels), "labels": labels}
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"Gmail API error: {exc}")
