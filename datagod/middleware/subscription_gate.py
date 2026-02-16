"""
DataGod Subscription Gate Middleware
Enforces feature access based on user subscription tier
"""

import logging
from typing import Optional, List
from functools import wraps

from fastapi import Depends, HTTPException, status, Request

logger = logging.getLogger("datagod.middleware.subscription")


# Tier hierarchy (higher number = more access)
TIER_LEVELS = {
    "free": 0,
    "basic": 1,
    "pro": 2,
    "enterprise": 3,
}

# Daily usage limits per tier
TIER_LIMITS = {
    "free": {
        "searches_per_day": 10,
        "exports_per_day": 2,
        "records_per_export": 100,
        "api_requests_per_day": 50,
        "saved_searches": 3,
    },
    "basic": {
        "searches_per_day": 100,
        "exports_per_day": 20,
        "records_per_export": 1000,
        "api_requests_per_day": 500,
        "saved_searches": 25,
    },
    "pro": {
        "searches_per_day": -1,  # Unlimited
        "exports_per_day": -1,
        "records_per_export": 10000,
        "api_requests_per_day": -1,
        "saved_searches": -1,
    },
    "enterprise": {
        "searches_per_day": -1,
        "exports_per_day": -1,
        "records_per_export": 100000,
        "api_requests_per_day": -1,
        "saved_searches": -1,
    },
}


class SubscriptionGate:
    """
    FastAPI dependency that checks if a user's subscription tier
    meets the minimum required level for an endpoint.
    
    Usage:
        @app.get("/premium-endpoint", dependencies=[Depends(SubscriptionGate(min_tier="basic"))])
        async def premium_endpoint(): ...
    """

    def __init__(self, min_tier: str = "free"):
        self.min_tier = min_tier
        self.min_level = TIER_LEVELS.get(min_tier, 0)

    async def __call__(self, request: Request):
        # Get user tier from request state (set by auth middleware)
        user_tier = getattr(request.state, "subscription_tier", "free")
        user_level = TIER_LEVELS.get(user_tier, 0)

        if user_level < self.min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "subscription_required",
                    "message": f"This feature requires a {self.min_tier} subscription or higher",
                    "current_tier": user_tier,
                    "required_tier": self.min_tier,
                    "upgrade_url": "/pricing",
                },
            )

        return user_tier


def get_tier_limit(tier: str, limit_name: str) -> int:
    """
    Get the usage limit for a specific tier and limit type.
    Returns -1 for unlimited.
    """
    tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    return tier_limits.get(limit_name, 0)


def check_usage_limit(
    tier: str,
    limit_name: str,
    current_usage: int,
) -> bool:
    """
    Check if the current usage is within the tier limit.
    Returns True if within limit, False if exceeded.
    """
    limit = get_tier_limit(tier, limit_name)
    if limit == -1:  # Unlimited
        return True
    return current_usage < limit
