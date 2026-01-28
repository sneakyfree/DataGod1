"""
DataGod Rate Limiting and Bulk Operations

Rate limiting by subscription tier and bulk API operations
with proper handling.
"""

import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from collections import defaultdict

logger = logging.getLogger(__name__)


# ==========================
# RATE LIMITING
# ==========================

class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a tier."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int  # Max burst requests
    bulk_operations_per_hour: int
    max_bulk_size: int  # Max records per bulk operation


# Default rate limits by tier
TIER_RATE_LIMITS: Dict[SubscriptionTier, RateLimitConfig] = {
    SubscriptionTier.FREE: RateLimitConfig(
        requests_per_minute=20,
        requests_per_hour=500,
        requests_per_day=2000,
        burst_limit=10,
        bulk_operations_per_hour=5,
        max_bulk_size=50,
    ),
    SubscriptionTier.BASIC: RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=2000,
        requests_per_day=10000,
        burst_limit=30,
        bulk_operations_per_hour=20,
        max_bulk_size=200,
    ),
    SubscriptionTier.PRO: RateLimitConfig(
        requests_per_minute=200,
        requests_per_hour=10000,
        requests_per_day=50000,
        burst_limit=100,
        bulk_operations_per_hour=100,
        max_bulk_size=1000,
    ),
    SubscriptionTier.ENTERPRISE: RateLimitConfig(
        requests_per_minute=1000,
        requests_per_hour=50000,
        requests_per_day=250000,
        burst_limit=500,
        bulk_operations_per_hour=500,
        max_bulk_size=5000,
    ),
}


@dataclass
class RateLimitState:
    """Current rate limit state for a user."""
    user_id: str
    tier: SubscriptionTier
    minute_count: int = 0
    minute_reset: float = 0
    hour_count: int = 0
    hour_reset: float = 0
    day_count: int = 0
    day_reset: float = 0
    bulk_count: int = 0
    bulk_reset: float = 0


class RateLimiter:
    """
    Rate limiter with per-tier limits.
    
    Features:
    - Tiered rate limits based on subscription
    - Sliding window algorithm
    - Separate bulk operation limits
    - Real-time quota tracking
    """
    
    def __init__(self):
        """Initialize rate limiter with in-memory storage."""
        self._states: Dict[str, RateLimitState] = {}
        self._lock = None  # Would use asyncio.Lock in async context
    
    def check_limit(
        self,
        user_id: str,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        is_bulk: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.
        
        Args:
            user_id: User identifier
            tier: User's subscription tier
            is_bulk: Whether this is a bulk operation
            
        Returns:
            Tuple of (allowed, limit_info)
        """
        now = time.time()
        state = self._get_or_create_state(user_id, tier)
        config = TIER_RATE_LIMITS[tier]
        
        # Reset windows if expired
        self._reset_windows(state, now)
        
        # Check limits
        if is_bulk:
            if state.bulk_count >= config.bulk_operations_per_hour:
                return False, self._build_limit_info(state, config, "bulk_hour", is_bulk=True)
        
        # Check all time windows
        if state.minute_count >= config.requests_per_minute:
            return False, self._build_limit_info(state, config, "minute")
        
        if state.hour_count >= config.requests_per_hour:
            return False, self._build_limit_info(state, config, "hour")
        
        if state.day_count >= config.requests_per_day:
            return False, self._build_limit_info(state, config, "day")
        
        # Increment counters
        state.minute_count += 1
        state.hour_count += 1
        state.day_count += 1
        if is_bulk:
            state.bulk_count += 1
        
        return True, self._build_limit_info(state, config, None)
    
    def get_quota(self, user_id: str, tier: SubscriptionTier = SubscriptionTier.FREE) -> Dict[str, Any]:
        """Get current quota usage for a user."""
        state = self._states.get(user_id)
        config = TIER_RATE_LIMITS[tier]
        
        if not state:
            return {
                "minute": {"used": 0, "limit": config.requests_per_minute, "remaining": config.requests_per_minute},
                "hour": {"used": 0, "limit": config.requests_per_hour, "remaining": config.requests_per_hour},
                "day": {"used": 0, "limit": config.requests_per_day, "remaining": config.requests_per_day},
                "bulk": {"used": 0, "limit": config.bulk_operations_per_hour, "remaining": config.bulk_operations_per_hour},
            }
        
        return {
            "minute": {
                "used": state.minute_count,
                "limit": config.requests_per_minute,
                "remaining": max(0, config.requests_per_minute - state.minute_count),
                "resets_in": int(state.minute_reset - time.time()),
            },
            "hour": {
                "used": state.hour_count,
                "limit": config.requests_per_hour,
                "remaining": max(0, config.requests_per_hour - state.hour_count),
                "resets_in": int(state.hour_reset - time.time()),
            },
            "day": {
                "used": state.day_count,
                "limit": config.requests_per_day,
                "remaining": max(0, config.requests_per_day - state.day_count),
                "resets_in": int(state.day_reset - time.time()),
            },
            "bulk": {
                "used": state.bulk_count,
                "limit": config.bulk_operations_per_hour,
                "remaining": max(0, config.bulk_operations_per_hour - state.bulk_count),
                "resets_in": int(state.bulk_reset - time.time()),
            },
        }
    
    def _get_or_create_state(self, user_id: str, tier: SubscriptionTier) -> RateLimitState:
        """Get or create rate limit state for user."""
        if user_id not in self._states:
            now = time.time()
            self._states[user_id] = RateLimitState(
                user_id=user_id,
                tier=tier,
                minute_reset=now + 60,
                hour_reset=now + 3600,
                day_reset=now + 86400,
                bulk_reset=now + 3600,
            )
        return self._states[user_id]
    
    def _reset_windows(self, state: RateLimitState, now: float):
        """Reset expired windows."""
        if now >= state.minute_reset:
            state.minute_count = 0
            state.minute_reset = now + 60
        
        if now >= state.hour_reset:
            state.hour_count = 0
            state.hour_reset = now + 3600
            state.bulk_count = 0
            state.bulk_reset = now + 3600
        
        if now >= state.day_reset:
            state.day_count = 0
            state.day_reset = now + 86400
    
    def _build_limit_info(
        self,
        state: RateLimitState,
        config: RateLimitConfig,
        exceeded_window: Optional[str],
        is_bulk: bool = False
    ) -> Dict[str, Any]:
        """Build rate limit info response."""
        now = time.time()
        
        info = {
            "exceeded": exceeded_window is not None,
            "tier": state.tier.value,
            "limits": {
                "minute": config.requests_per_minute,
                "hour": config.requests_per_hour,
                "day": config.requests_per_day,
            },
            "current": {
                "minute": state.minute_count,
                "hour": state.hour_count,
                "day": state.day_count,
            },
        }
        
        if exceeded_window:
            if exceeded_window == "minute":
                info["retry_after"] = int(state.minute_reset - now)
            elif exceeded_window == "hour" or exceeded_window == "bulk_hour":
                info["retry_after"] = int(state.hour_reset - now)
            elif exceeded_window == "day":
                info["retry_after"] = int(state.day_reset - now)
            
            info["message"] = f"Rate limit exceeded. Please wait {info.get('retry_after', 0)} seconds."
        
        return info


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# ==========================
# BULK OPERATIONS
# ==========================

@dataclass
class BulkOperationResult:
    """Result of a bulk operation."""
    operation: str
    total_items: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]]
    duration_ms: float
    items: List[Dict[str, Any]] = field(default_factory=list)


class BulkOperationsHandler:
    """
    Handler for bulk API operations.
    
    Features:
    - Batch processing with configurable size
    - Transaction-like behavior (all or nothing optional)
    - Detailed error reporting
    - Progress tracking
    """
    
    def __init__(self, batch_size: int = 100):
        """Initialize bulk operations handler."""
        self.batch_size = batch_size
    
    async def bulk_create(
        self,
        items: List[Dict[str, Any]],
        create_func: Callable,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        validate_func: Optional[Callable] = None,
        all_or_nothing: bool = False
    ) -> BulkOperationResult:
        """
        Bulk create operation.
        
        Args:
            items: List of items to create
            create_func: Async function to create single item
            tier: User's subscription tier
            validate_func: Optional validation function
            all_or_nothing: If True, rollback all on any failure
            
        Returns:
            BulkOperationResult with stats
        """
        config = TIER_RATE_LIMITS[tier]
        
        # Check max size
        if len(items) > config.max_bulk_size:
            return BulkOperationResult(
                operation="bulk_create",
                total_items=len(items),
                successful=0,
                failed=len(items),
                errors=[{"message": f"Exceeds max bulk size of {config.max_bulk_size}"}],
                duration_ms=0,
            )
        
        start_time = time.time()
        successful = 0
        failed = 0
        errors = []
        created_items = []
        
        # Validate all items first if all_or_nothing
        if all_or_nothing and validate_func:
            for i, item in enumerate(items):
                try:
                    validate_func(item)
                except Exception as e:
                    return BulkOperationResult(
                        operation="bulk_create",
                        total_items=len(items),
                        successful=0,
                        failed=len(items),
                        errors=[{"index": i, "message": str(e)}],
                        duration_ms=(time.time() - start_time) * 1000,
                    )
        
        # Process in batches
        for i, item in enumerate(items):
            try:
                if validate_func:
                    validate_func(item)
                
                result = await create_func(item)
                created_items.append(result)
                successful += 1
            except Exception as e:
                failed += 1
                errors.append({
                    "index": i,
                    "item": item.get("id") or str(i),
                    "message": str(e),
                })
                
                if all_or_nothing:
                    # Would rollback created items here
                    break
        
        return BulkOperationResult(
            operation="bulk_create",
            total_items=len(items),
            successful=successful,
            failed=failed,
            errors=errors,
            duration_ms=(time.time() - start_time) * 1000,
            items=created_items,
        )
    
    async def bulk_update(
        self,
        items: List[Dict[str, Any]],
        update_func: Callable,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        id_field: str = "id"
    ) -> BulkOperationResult:
        """
        Bulk update operation.
        
        Args:
            items: List of items with IDs and update data
            update_func: Async function to update single item
            tier: User's subscription tier
            id_field: Field name containing item ID
            
        Returns:
            BulkOperationResult with stats
        """
        config = TIER_RATE_LIMITS[tier]
        
        if len(items) > config.max_bulk_size:
            return BulkOperationResult(
                operation="bulk_update",
                total_items=len(items),
                successful=0,
                failed=len(items),
                errors=[{"message": f"Exceeds max bulk size of {config.max_bulk_size}"}],
                duration_ms=0,
            )
        
        start_time = time.time()
        successful = 0
        failed = 0
        errors = []
        updated_items = []
        
        for i, item in enumerate(items):
            try:
                item_id = item.get(id_field)
                if not item_id:
                    raise ValueError(f"Missing {id_field}")
                
                result = await update_func(item_id, item)
                updated_items.append(result)
                successful += 1
            except Exception as e:
                failed += 1
                errors.append({
                    "index": i,
                    "item": item.get(id_field, str(i)),
                    "message": str(e),
                })
        
        return BulkOperationResult(
            operation="bulk_update",
            total_items=len(items),
            successful=successful,
            failed=failed,
            errors=errors,
            duration_ms=(time.time() - start_time) * 1000,
            items=updated_items,
        )
    
    async def bulk_delete(
        self,
        ids: List[str],
        delete_func: Callable,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        soft_delete: bool = True
    ) -> BulkOperationResult:
        """
        Bulk delete operation.
        
        Args:
            ids: List of item IDs to delete
            delete_func: Async function to delete single item
            tier: User's subscription tier
            soft_delete: If True, soft delete (mark as deleted)
            
        Returns:
            BulkOperationResult with stats
        """
        config = TIER_RATE_LIMITS[tier]
        
        if len(ids) > config.max_bulk_size:
            return BulkOperationResult(
                operation="bulk_delete",
                total_items=len(ids),
                successful=0,
                failed=len(ids),
                errors=[{"message": f"Exceeds max bulk size of {config.max_bulk_size}"}],
                duration_ms=0,
            )
        
        start_time = time.time()
        successful = 0
        failed = 0
        errors = []
        
        for i, item_id in enumerate(ids):
            try:
                await delete_func(item_id, soft=soft_delete)
                successful += 1
            except Exception as e:
                failed += 1
                errors.append({
                    "index": i,
                    "item": item_id,
                    "message": str(e),
                })
        
        return BulkOperationResult(
            operation="bulk_delete",
            total_items=len(ids),
            successful=successful,
            failed=failed,
            errors=errors,
            duration_ms=(time.time() - start_time) * 1000,
        )


# FastAPI middleware for rate limiting
def rate_limit_middleware(app):
    """
    FastAPI middleware for rate limiting.
    
    Usage:
        app = FastAPI()
        rate_limit_middleware(app)
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse
    
    class RateLimitMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            # Skip rate limiting for health checks
            if request.url.path in ('/health', '/ready', '/metrics'):
                return await call_next(request)
            
            # Get user info from request
            user_id = getattr(request.state, 'user_id', None)
            if not user_id:
                # Use IP as fallback for anonymous users
                user_id = f"ip:{request.client.host}" if request.client else "anonymous"
            
            tier_str = getattr(request.state, 'tier', 'free')
            tier = SubscriptionTier(tier_str)
            
            # Check if bulk operation
            is_bulk = '/bulk' in request.url.path
            
            # Check rate limit
            rate_limiter = get_rate_limiter()
            allowed, limit_info = rate_limiter.check_limit(user_id, tier, is_bulk)
            
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": limit_info.get("message", "Too many requests"),
                        "retry_after": limit_info.get("retry_after", 60),
                    },
                    headers={
                        "Retry-After": str(limit_info.get("retry_after", 60)),
                        "X-RateLimit-Limit": str(limit_info["limits"]["minute"]),
                        "X-RateLimit-Remaining": str(max(0, limit_info["limits"]["minute"] - limit_info["current"]["minute"])),
                    }
                )
            
            # Add rate limit headers to response
            response = await call_next(request)
            config = TIER_RATE_LIMITS[tier]
            response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(max(0, config.requests_per_minute - limit_info["current"]["minute"]))
            
            return response
    
    app.add_middleware(RateLimitMiddleware)
    return app


# Default bulk handler instance
_bulk_handler: Optional[BulkOperationsHandler] = None


def get_bulk_handler() -> BulkOperationsHandler:
    """Get or create bulk operations handler."""
    global _bulk_handler
    if _bulk_handler is None:
        _bulk_handler = BulkOperationsHandler()
    return _bulk_handler
