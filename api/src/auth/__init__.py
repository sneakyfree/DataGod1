"""
DataGod Auth Module

Provides OAuth2, SSO, and authentication utilities.
"""

from .oauth import router as oauth_router

__all__ = ["oauth_router"]
