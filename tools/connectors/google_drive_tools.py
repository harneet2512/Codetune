"""Google Drive connector tools using the Drive API v3.

Authentication:
- Service account JSON path via ``GOOGLE_SERVICE_ACCOUNT_PATH`` env var, OR
- OAuth access token via ``GOOGLE_ACCESS_TOKEN`` env var, OR
- Pass ``credentials`` directly to each function.
"""

from __future__ import annotations

import io
import os
from typing import Any

_MAX_FILE_CHARS = 2000
_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _err(message: str) -> dict[str, Any]:
    return {"error": message}


def _build_service(credentials: Any | None = None) -> Any:
    """Build a Google Drive API service object.

    Args:
        credentials: A google.oauth2 credentials object. If None, resolves
            from environment variables.

    Returns:
        A googleapiclient Resource for Drive v3.

    Raises:
        RuntimeError: If no credentials can be resolved.
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

    return build_discovery("drive", "v3", credentials=credentials, cache_discovery=False)


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


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def drive_search(
    query: str,
    max_results: int = 10,
    credentials: Any | None = None,
) -> dict[str, Any]:
    """Search files in Google Drive by name or content.

    Args:
        query: Search string (applied to file name via ``name contains``).
        max_results: Maximum number of results (capped at 20).
        credentials: Google credentials object.

    Returns:
        Dict with ``files`` list, each containing id, name, mimeType, modifiedTime.
    """
    try:
        service = _build_service(credentials)
        max_results = min(max_results, 20)
        # Escape single quotes in query
        safe_query = query.replace("'", "\\'")
        result = (
            service.files()
            .list(
                q=f"name contains '{safe_query}' and trashed = false",
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, owners, size)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )
        files = []
        for f in result.get("files", []):
            owners = [o.get("displayName", o.get("emailAddress", "")) for o in f.get("owners", [])]
            files.append({
                "id": f["id"],
                "name": f["name"],
                "mime_type": f.get("mimeType", ""),
                "modified_time": f.get("modifiedTime", ""),
                "owners": owners,
                "size": f.get("size"),
            })
        return {"count": len(files), "files": files}
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"Drive API error: {exc}")


def drive_read_file(
    file_id: str,
    credentials: Any | None = None,
) -> dict[str, Any]:
    """Read file contents from Google Drive.

    Supports Google Docs (exported as plain text), Google Sheets (exported as
    CSV), and binary/plain text files (downloaded directly).

    Args:
        file_id: The Drive file ID.
        credentials: Google credentials object.

    Returns:
        Dict with ``name``, ``content`` (truncated to 2000 chars), ``mime_type``.
    """
    try:
        service = _build_service(credentials)

        # Get file metadata first
        meta = service.files().get(fileId=file_id, fields="id, name, mimeType, size").execute()
        mime = meta.get("mimeType", "")
        name = meta.get("name", "")

        # Google Workspace files need export
        export_map = {
            "application/vnd.google-apps.document": ("text/plain", "txt"),
            "application/vnd.google-apps.spreadsheet": ("text/csv", "csv"),
            "application/vnd.google-apps.presentation": ("text/plain", "txt"),
        }

        if mime in export_map:
            export_mime, _ = export_map[mime]
            content_bytes = service.files().export(fileId=file_id, mimeType=export_mime).execute()
        else:
            content_bytes = service.files().get_media(fileId=file_id).execute()

        if isinstance(content_bytes, bytes):
            content = content_bytes.decode("utf-8", errors="replace")
        else:
            content = str(content_bytes)

        truncated = len(content) > _MAX_FILE_CHARS
        if truncated:
            content = content[:_MAX_FILE_CHARS] + f"\n... [truncated, {len(content)} chars total]"

        return {
            "id": file_id,
            "name": name,
            "mime_type": mime,
            "content": content,
            "truncated": truncated,
        }
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"Drive API error: {exc}")


def drive_list_recent(
    max_results: int = 10,
    credentials: Any | None = None,
) -> dict[str, Any]:
    """List recently modified files in Google Drive.

    Args:
        max_results: Maximum number of results (capped at 20).
        credentials: Google credentials object.

    Returns:
        Dict with ``files`` list ordered by most recently modified.
    """
    try:
        service = _build_service(credentials)
        max_results = min(max_results, 20)
        result = (
            service.files()
            .list(
                q="trashed = false",
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, owners)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )
        files = []
        for f in result.get("files", []):
            owners = [o.get("displayName", o.get("emailAddress", "")) for o in f.get("owners", [])]
            files.append({
                "id": f["id"],
                "name": f["name"],
                "mime_type": f.get("mimeType", ""),
                "modified_time": f.get("modifiedTime", ""),
                "owners": owners,
            })
        return {"count": len(files), "files": files}
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"Drive API error: {exc}")


def drive_get_file_info(
    file_id: str,
    credentials: Any | None = None,
) -> dict[str, Any]:
    """Get metadata for a Google Drive file.

    Args:
        file_id: The Drive file ID.
        credentials: Google credentials object.

    Returns:
        Dict with file metadata including owner, modified date, sharing info.
    """
    try:
        service = _build_service(credentials)
        meta = (
            service.files()
            .get(
                fileId=file_id,
                fields="id, name, mimeType, modifiedTime, createdTime, owners, "
                       "shared, sharingUser, size, webViewLink, permissions",
            )
            .execute()
        )
        owners = [o.get("displayName", o.get("emailAddress", "")) for o in meta.get("owners", [])]
        permissions = []
        for p in meta.get("permissions", []):
            permissions.append({
                "role": p.get("role", ""),
                "type": p.get("type", ""),
                "email": p.get("emailAddress", ""),
                "display_name": p.get("displayName", ""),
            })

        return {
            "id": meta["id"],
            "name": meta["name"],
            "mime_type": meta.get("mimeType", ""),
            "created_time": meta.get("createdTime", ""),
            "modified_time": meta.get("modifiedTime", ""),
            "owners": owners,
            "shared": meta.get("shared", False),
            "size": meta.get("size"),
            "web_link": meta.get("webViewLink", ""),
            "permissions": permissions,
        }
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"Drive API error: {exc}")
