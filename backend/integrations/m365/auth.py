"""M365 OAuth2 token management via MSAL confidential client."""
import msal
from backend.config import get_settings

GRAPH_SCOPES = [
    "User.Read", "Mail.Read", "Mail.Send",
    "Calendars.Read", "Contacts.Read", "Files.Read.All",
]

_app_cache: msal.ConfidentialClientApplication | None = None


def _get_msal_app() -> msal.ConfidentialClientApplication:
    global _app_cache
    if _app_cache is None:
        s = get_settings()
        _app_cache = msal.ConfidentialClientApplication(
            client_id=s.m365_client_id,
            client_credential=s.m365_client_secret,
            authority=f"https://login.microsoftonline.com/{s.m365_tenant_id}",
        )
    return _app_cache


def get_access_token() -> str:
    """Exchange the stored refresh token for a fresh access token.

    Returns the access_token string ready for Authorization header.
    Raises RuntimeError if the refresh fails.
    """
    s = get_settings()
    app = _get_msal_app()
    result = app.acquire_token_by_refresh_token(
        s.m365_refresh_token,
        scopes=GRAPH_SCOPES,
    )
    if "access_token" not in result:
        raise RuntimeError(f"M365 token refresh failed: {result.get('error_description', result)}")
    return result["access_token"]
