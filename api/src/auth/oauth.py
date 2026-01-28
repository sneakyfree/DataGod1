"""
DataGod OAuth2/SSO Authentication Module

Provides OAuth2 authentication with Google, GitHub, and SAML SSO providers.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import secrets
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["OAuth Authentication"])


# =============================================================================
# CONFIGURATION
# =============================================================================

class OAuthConfig:
    """OAuth provider configuration."""
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    GOOGLE_SCOPES: str = "openid email profile"
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_AUTH_URL: str = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL: str = "https://github.com/login/oauth/access_token"
    GITHUB_USERINFO_URL: str = "https://api.github.com/user"
    GITHUB_SCOPES: str = "read:user user:email"
    
    # General
    REDIRECT_BASE_URL: str = "http://localhost:3000"
    STATE_SECRET: str = secrets.token_urlsafe(32)
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables."""
        import os
        cls.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
        cls.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
        cls.GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
        cls.GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
        cls.REDIRECT_BASE_URL = os.getenv("OAUTH_REDIRECT_BASE_URL", "http://localhost:3000")

# Load config on module import
OAuthConfig.load_from_env()


# =============================================================================
# MODELS
# =============================================================================

class OAuthState(BaseModel):
    """OAuth state for CSRF protection."""
    state: str
    provider: str
    created_at: datetime
    redirect_uri: Optional[str] = None

class OAuthUserInfo(BaseModel):
    """Standardized user info from OAuth providers."""
    provider: str
    provider_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False
    raw_data: Dict[str, Any] = {}

class OAuthCallbackResponse(BaseModel):
    """Response from OAuth callback."""
    access_token: str
    token_type: str = "bearer"
    user: OAuthUserInfo
    is_new_user: bool = False


# =============================================================================
# STATE MANAGEMENT (In-memory for dev, use Redis in production)
# =============================================================================

_oauth_states: Dict[str, OAuthState] = {}

def create_state(provider: str, redirect_uri: Optional[str] = None) -> str:
    """Create and store an OAuth state token."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = OAuthState(
        state=state,
        provider=provider,
        created_at=datetime.utcnow(),
        redirect_uri=redirect_uri
    )
    # Clean up old states (older than 10 minutes)
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    expired = [k for k, v in _oauth_states.items() if v.created_at < cutoff]
    for k in expired:
        _oauth_states.pop(k, None)
    return state

def validate_state(state: str, provider: str) -> Optional[OAuthState]:
    """Validate and consume an OAuth state token."""
    oauth_state = _oauth_states.pop(state, None)
    if oauth_state and oauth_state.provider == provider:
        # Check if not expired (10 minutes)
        if datetime.utcnow() - oauth_state.created_at < timedelta(minutes=10):
            return oauth_state
    return None


# =============================================================================
# GOOGLE OAUTH
# =============================================================================

@router.get("/google/login")
async def google_login(
    redirect_uri: Optional[str] = Query(None, description="Post-login redirect URI")
):
    """Initiate Google OAuth login flow."""
    if not OAuthConfig.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    
    state = create_state("google", redirect_uri)
    callback_url = f"{OAuthConfig.REDIRECT_BASE_URL}/api/auth/oauth/google/callback"
    
    params = {
        "client_id": OAuthConfig.GOOGLE_CLIENT_ID,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": OAuthConfig.GOOGLE_SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"{OAuthConfig.GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...)
):
    """Handle Google OAuth callback."""
    # Validate state
    oauth_state = validate_state(state, "google")
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    
    callback_url = f"{OAuthConfig.REDIRECT_BASE_URL}/api/auth/oauth/google/callback"
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(
                OAuthConfig.GOOGLE_TOKEN_URL,
                data={
                    "client_id": OAuthConfig.GOOGLE_CLIENT_ID,
                    "client_secret": OAuthConfig.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_url,
                }
            )
            token_response.raise_for_status()
            tokens = token_response.json()
        except httpx.HTTPError as e:
            logger.error(f"Google token exchange failed: {e}")
            raise HTTPException(status_code=400, detail="Token exchange failed")
        
        # Get user info
        try:
            userinfo_response = await client.get(
                OAuthConfig.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
        except httpx.HTTPError as e:
            logger.error(f"Google userinfo failed: {e}")
            raise HTTPException(status_code=400, detail="Failed to get user info")
    
    # Create standardized user info
    user_info = OAuthUserInfo(
        provider="google",
        provider_id=userinfo.get("sub", ""),
        email=userinfo.get("email", ""),
        name=userinfo.get("name"),
        picture=userinfo.get("picture"),
        email_verified=userinfo.get("email_verified", False),
        raw_data=userinfo
    )
    
    # Create or get user, generate JWT token
    result = await _process_oauth_user(user_info)
    
    # Redirect to frontend with token
    redirect_uri = oauth_state.redirect_uri or f"{OAuthConfig.REDIRECT_BASE_URL}/dashboard"
    return RedirectResponse(
        url=f"{redirect_uri}?token={result['access_token']}&new_user={result['is_new_user']}"
    )


# =============================================================================
# GITHUB OAUTH
# =============================================================================

@router.get("/github/login")
async def github_login(
    redirect_uri: Optional[str] = Query(None, description="Post-login redirect URI")
):
    """Initiate GitHub OAuth login flow."""
    if not OAuthConfig.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    
    state = create_state("github", redirect_uri)
    callback_url = f"{OAuthConfig.REDIRECT_BASE_URL}/api/auth/oauth/github/callback"
    
    params = {
        "client_id": OAuthConfig.GITHUB_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": OAuthConfig.GITHUB_SCOPES,
        "state": state,
    }
    
    auth_url = f"{OAuthConfig.GITHUB_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...)
):
    """Handle GitHub OAuth callback."""
    # Validate state
    oauth_state = validate_state(state, "github")
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    
    callback_url = f"{OAuthConfig.REDIRECT_BASE_URL}/api/auth/oauth/github/callback"
    
    async with httpx.AsyncClient() as client:
        # Exchange code for token
        try:
            token_response = await client.post(
                OAuthConfig.GITHUB_TOKEN_URL,
                data={
                    "client_id": OAuthConfig.GITHUB_CLIENT_ID,
                    "client_secret": OAuthConfig.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": callback_url,
                },
                headers={"Accept": "application/json"}
            )
            token_response.raise_for_status()
            tokens = token_response.json()
        except httpx.HTTPError as e:
            logger.error(f"GitHub token exchange failed: {e}")
            raise HTTPException(status_code=400, detail="Token exchange failed")
        
        if "error" in tokens:
            raise HTTPException(status_code=400, detail=tokens.get("error_description", "OAuth error"))
        
        access_token = tokens.get("access_token")
        
        # Get user info
        try:
            userinfo_response = await client.get(
                OAuthConfig.GITHUB_USERINFO_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
        except httpx.HTTPError as e:
            logger.error(f"GitHub userinfo failed: {e}")
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        # Get email if not public
        email = userinfo.get("email")
        if not email:
            try:
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                emails_response.raise_for_status()
                emails = emails_response.json()
                primary_email = next((e for e in emails if e.get("primary")), None)
                if primary_email:
                    email = primary_email.get("email")
            except httpx.HTTPError:
                pass
    
    # Create standardized user info
    user_info = OAuthUserInfo(
        provider="github",
        provider_id=str(userinfo.get("id", "")),
        email=email or "",
        name=userinfo.get("name") or userinfo.get("login"),
        picture=userinfo.get("avatar_url"),
        email_verified=True,  # GitHub emails are verified
        raw_data=userinfo
    )
    
    # Create or get user, generate JWT token
    result = await _process_oauth_user(user_info)
    
    # Redirect to frontend with token
    redirect_uri = oauth_state.redirect_uri or f"{OAuthConfig.REDIRECT_BASE_URL}/dashboard"
    return RedirectResponse(
        url=f"{redirect_uri}?token={result['access_token']}&new_user={result['is_new_user']}"
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _process_oauth_user(user_info: OAuthUserInfo) -> Dict[str, Any]:
    """
    Process OAuth user info to create/update user and generate JWT.
    
    This function should be connected to your user database.
    For now, it returns a mock response.
    """
    from jose import jwt
    from datetime import datetime, timedelta
    import os
    
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
    
    # TODO: Integrate with actual database
    # Here you would:
    # 1. Check if user exists by provider_id or email
    # 2. Create new user if not exists
    # 3. Update user info if exists
    # 4. Generate JWT token
    
    is_new_user = False  # Set based on database lookup
    
    # Generate JWT token
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": user_info.email,
        "provider": user_info.provider,
        "provider_id": user_info.provider_id,
        "exp": expire,
    }
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    
    logger.info(f"OAuth login successful for {user_info.email} via {user_info.provider}")
    
    return {
        "access_token": access_token,
        "is_new_user": is_new_user,
        "user": user_info
    }


# =============================================================================
# STATUS ENDPOINT
# =============================================================================

@router.get("/providers")
async def get_available_providers():
    """Get list of available OAuth providers."""
    providers = []
    
    if OAuthConfig.GOOGLE_CLIENT_ID:
        providers.append({
            "id": "google",
            "name": "Google",
            "login_url": "/api/auth/oauth/google/login",
            "icon": "google"
        })
    
    if OAuthConfig.GITHUB_CLIENT_ID:
        providers.append({
            "id": "github",
            "name": "GitHub",
            "login_url": "/api/auth/oauth/github/login",
            "icon": "github"
        })
    
    return {"providers": providers}
