"""Google Drive API connector — requires OAuth2 tokens from Google."""

from auth.google_oauth import get_credentials

API = "https://www.googleapis.com/drive/v3"
DOCS_API = "https://docs.googleapis.com/v1"


async def call_drive(method: str, args: dict) -> dict:
    """Dispatch to Google Drive API."""
    creds = get_credentials()
    if not creds:
        return {"error": "Google Drive not connected. Complete OAuth flow first."}

    handlers = {
        "search_files": _search_files,
        "read_document": _read_document,
        "list_folder": _list_folder,
        "get_file_metadata": _get_file_metadata,
    }
    handler = handlers.get(method)
    if not handler:
        return {"error": f"Unknown Drive method: {method}"}
    return await handler(args, creds)


async def _search_files(args: dict, creds) -> dict:
    import httpx

    query = args.get("query", "")
    file_type = args.get("type", "")

    q_parts = [f"name contains '{query}'"]
    if file_type:
        mime_map = {
            "document": "application/vnd.google-apps.document",
            "spreadsheet": "application/vnd.google-apps.spreadsheet",
            "folder": "application/vnd.google-apps.folder",
        }
        mime = mime_map.get(file_type, "")
        if mime:
            q_parts.append(f"mimeType='{mime}'")

    headers = {"Authorization": f"Bearer {creds.token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/files",
            params={"q": " and ".join(q_parts), "fields": "files(id,name,mimeType,modifiedTime,owners)", "pageSize": 10},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "files": [
            {
                "id": f["id"],
                "name": f["name"],
                "type": f.get("mimeType", ""),
                "modified": f.get("modifiedTime", ""),
                "owner": f.get("owners", [{}])[0].get("emailAddress", "") if f.get("owners") else "",
            }
            for f in data.get("files", [])
        ],
    }


async def _read_document(args: dict, creds) -> dict:
    import httpx

    file_id = args.get("file_id", "")
    headers = {"Authorization": f"Bearer {creds.token}"}

    # Try Google Docs API first (for native Google Docs)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{DOCS_API}/documents/{file_id}",
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            doc = resp.json()

            # Extract text from document body
            text = _extract_doc_text(doc.get("body", {}).get("content", []))
            return {"file_id": file_id, "title": doc.get("title", ""), "content": text}
        except httpx.HTTPStatusError:
            # Fall back to raw download for non-Google-Doc files
            resp = await client.get(
                f"{API}/files/{file_id}",
                params={"alt": "media"},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            return {"file_id": file_id, "content": resp.text[:10000]}


def _extract_doc_text(content: list) -> str:
    """Extract plain text from Google Docs body content."""
    text_parts = []
    for element in content:
        if "paragraph" in element:
            for elem in element["paragraph"].get("elements", []):
                if "textRun" in elem:
                    text_parts.append(elem["textRun"].get("content", ""))
    return "".join(text_parts)


async def _list_folder(args: dict, creds) -> dict:
    import httpx

    folder_id = args.get("folder_id", "root")
    headers = {"Authorization": f"Bearer {creds.token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/files",
            params={"q": f"'{folder_id}' in parents", "fields": "files(id,name,mimeType)", "pageSize": 20},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "items": [
            {"id": f["id"], "name": f["name"], "type": f.get("mimeType", "")}
            for f in data.get("files", [])
        ],
    }


async def _get_file_metadata(args: dict, creds) -> dict:
    import httpx

    file_id = args.get("file_id", "")
    headers = {"Authorization": f"Bearer {creds.token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API}/files/{file_id}",
            params={"fields": "*"},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "id": data["id"],
        "name": data["name"],
        "mimeType": data.get("mimeType", ""),
        "size": data.get("size", ""),
        "modifiedTime": data.get("modifiedTime", ""),
        "owners": [o.get("emailAddress", "") for o in data.get("owners", [])],
        "shared": data.get("shared", False),
    }
