"""Google OAuth 2.0 flow for Gmail + Drive access."""

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

# In-memory credential store (session-scoped, not persisted)
_credentials: Credentials | None = None

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_credentials() -> Credentials | None:
    """Return current OAuth credentials, or None if not authenticated."""
    global _credentials
    if _credentials and _credentials.valid:
        return _credentials
    if _credentials and _credentials.expired and _credentials.refresh_token:
        from google.auth.transport.requests import Request
        _credentials.refresh(Request())
        return _credentials
    return None


def get_auth_url() -> str:
    """Generate the Google OAuth consent URL."""
    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID not configured")

    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code(code: str) -> Credentials:
    """Exchange the authorization code for tokens."""
    global _credentials
    flow = _build_flow()
    flow.fetch_token(code=code)
    _credentials = flow.credentials
    return _credentials


def disconnect():
    """Clear stored credentials."""
    global _credentials
    _credentials = None


def _build_flow() -> Flow:
    """Build a Google OAuth Flow from config."""
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
