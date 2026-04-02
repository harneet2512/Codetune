"""OAuth routes for Google (Gmail + Drive)."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from auth.google_oauth import get_auth_url, exchange_code, disconnect, get_credentials
from config import FRONTEND_URL

router = APIRouter(tags=["auth"])


@router.get("/google/start")
async def google_auth_start():
    """Start the Google OAuth flow. Returns the consent URL."""
    try:
        url = get_auth_url()
        return {"auth_url": url}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/google/callback")
async def google_auth_callback(code: str = "", error: str = ""):
    """Handle the OAuth callback from Google."""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}?auth_error={error}")

    if not code:
        raise HTTPException(400, "Missing authorization code")

    try:
        exchange_code(code)
        # Redirect back to frontend with success
        return RedirectResponse(f"{FRONTEND_URL}?auth=success")
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}?auth_error={str(e)}")


@router.get("/google/status")
async def google_auth_status():
    """Check if Google OAuth tokens are available."""
    creds = get_credentials()
    return {
        "connected": creds is not None,
        "scopes": ["gmail.readonly", "drive.readonly"] if creds else [],
    }


@router.post("/google/disconnect")
async def google_disconnect():
    """Clear stored Google credentials."""
    disconnect()
    return {"status": "disconnected"}
