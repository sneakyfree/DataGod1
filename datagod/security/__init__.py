"""
Security Utilities (Phase 5: Launch Readiness)

Provides security hardening for production:
- Rate limiting middleware
- Input sanitization
- PII detection and redaction
"""

import logging
import re
import time
import hashlib
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# RATE LIMITING
# =============================================================================

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10  # Max requests in 1 second
    whitelist_ips: Set[str] = field(default_factory=set)
    blacklist_ips: Set[str] = field(default_factory=set)


class RateLimiter:
    """
    Token bucket rate limiter with multiple time windows.
    
    Features:
    - Per-user and per-IP rate limiting
    - Multiple time windows (minute, hour, day)
    - Burst protection
    - Whitelist/blacklist support
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'minute': {'count': 0, 'reset_at': time.time() + 60},
            'hour': {'count': 0, 'reset_at': time.time() + 3600},
            'day': {'count': 0, 'reset_at': time.time() + 86400},
            'burst': {'count': 0, 'reset_at': time.time() + 1}
        })
    
    def check(self, key: str, ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if a request is allowed.
        
        Args:
            key: Unique identifier (user_id, api_key, etc.)
            ip: IP address for additional checks
        
        Returns:
            Dict with 'allowed', 'remaining', 'reset_at', 'retry_after'
        """
        # Check blacklist
        if ip and ip in self.config.blacklist_ips:
            return {
                'allowed': False,
                'reason': 'IP blacklisted',
                'remaining': 0,
                'reset_at': None,
                'retry_after': None
            }
        
        # Check whitelist (bypass rate limiting)
        if ip and ip in self.config.whitelist_ips:
            return {
                'allowed': True,
                'remaining': float('inf'),
                'reset_at': None,
                'retry_after': None
            }
        
        now = time.time()
        bucket = self._buckets[key]
        
        # Reset expired buckets
        for window in ['minute', 'hour', 'day', 'burst']:
            if now >= bucket[window]['reset_at']:
                bucket[window]['count'] = 0
                reset_seconds = {'minute': 60, 'hour': 3600, 'day': 86400, 'burst': 1}
                bucket[window]['reset_at'] = now + reset_seconds[window]
        
        # Check limits
        limits = {
            'minute': self.config.requests_per_minute,
            'hour': self.config.requests_per_hour,
            'day': self.config.requests_per_day,
            'burst': self.config.burst_limit
        }
        
        for window, limit in limits.items():
            if bucket[window]['count'] >= limit:
                return {
                    'allowed': False,
                    'reason': f'{window} limit exceeded',
                    'remaining': 0,
                    'reset_at': bucket[window]['reset_at'],
                    'retry_after': bucket[window]['reset_at'] - now
                }
        
        # Increment counters
        for window in ['minute', 'hour', 'day', 'burst']:
            bucket[window]['count'] += 1
        
        # Return remaining (use minute as primary)
        remaining = limits['minute'] - bucket['minute']['count']
        
        return {
            'allowed': True,
            'remaining': remaining,
            'reset_at': bucket['minute']['reset_at'],
            'retry_after': None
        }
    
    def get_headers(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Get rate limit headers for HTTP response."""
        headers = {
            'X-RateLimit-Remaining': str(result.get('remaining', 0))
        }
        if result.get('reset_at'):
            headers['X-RateLimit-Reset'] = str(int(result['reset_at']))
        if result.get('retry_after'):
            headers['Retry-After'] = str(int(result['retry_after']))
        return headers


def rate_limit(
    limiter: RateLimiter,
    key_func: Callable = None
):
    """
    Decorator for rate limiting functions.
    
    Args:
        limiter: RateLimiter instance
        key_func: Function to extract rate limit key from args
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs) if key_func else 'default'
            result = limiter.check(key)
            
            if not result['allowed']:
                raise Exception(f"Rate limit exceeded: {result['reason']}")
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs) if key_func else 'default'
            result = limiter.check(key)
            
            if not result['allowed']:
                raise Exception(f"Rate limit exceeded: {result['reason']}")
            
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# =============================================================================
# INPUT SANITIZATION
# =============================================================================

class InputSanitizer:
    """
    Sanitizes user input to prevent injection attacks.
    
    Features:
    - SQL injection prevention
    - XSS prevention
    - Path traversal prevention
    - Command injection prevention
    """
    
    # Patterns for dangerous content
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
        r"('|\"|`)\s*(OR|AND)\s*('|\"|`)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e/",
        r"\.%2e/",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",
        r"\$\(",
        r"\$\{",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, context: str = "general") -> str:
        """
        Sanitize a string value.
        
        Args:
            value: The string to sanitize
            context: Context for sanitization (general, sql, html, path, command)
        
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return value
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Context-specific sanitization
        if context in ["sql", "general"]:
            value = cls._escape_sql(value)
        
        if context in ["html", "general"]:
            value = cls._escape_html(value)
        
        if context in ["path", "general"]:
            value = cls._sanitize_path(value)
        
        if context == "command":
            value = cls._escape_command(value)
        
        return value
    
    @classmethod
    def validate_input(cls, value: str, context: str = "general") -> Dict[str, Any]:
        """
        Validate input and return any detected threats.
        
        Returns:
            Dict with 'valid', 'threats', 'sanitized'
        """
        threats = []
        
        if context in ["sql", "general"]:
            for pattern in cls.SQL_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    threats.append("SQL injection attempt detected")
                    break
        
        if context in ["html", "general"]:
            for pattern in cls.XSS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    threats.append("XSS attempt detected")
                    break
        
        if context in ["path", "general"]:
            for pattern in cls.PATH_TRAVERSAL_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    threats.append("Path traversal attempt detected")
                    break
        
        if context == "command":
            for pattern in cls.COMMAND_INJECTION_PATTERNS:
                if re.search(pattern, value):
                    threats.append("Command injection attempt detected")
                    break
        
        return {
            'valid': len(threats) == 0,
            'threats': threats,
            'sanitized': cls.sanitize_string(value, context)
        }
    
    @staticmethod
    def _escape_sql(value: str) -> str:
        """Escape SQL special characters."""
        return value.replace("'", "''").replace("\\", "\\\\")
    
    @staticmethod
    def _escape_html(value: str) -> str:
        """Escape HTML special characters."""
        escapes = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
        }
        for char, escape in escapes.items():
            value = value.replace(char, escape)
        return value
    
    @staticmethod
    def _sanitize_path(value: str) -> str:
        """Remove path traversal sequences."""
        # Remove ../ and ..\
        value = re.sub(r'\.\.[\\/]', '', value)
        # Remove leading slashes
        value = value.lstrip('/')
        return value
    
    @staticmethod
    def _escape_command(value: str) -> str:
        """Escape shell command characters."""
        # Remove dangerous characters
        return re.sub(r'[;&|`$()]', '', value)


# =============================================================================
# PII DETECTION AND REDACTION
# =============================================================================

class PIIRedactor:
    """
    Detects and redacts Personally Identifiable Information.
    
    Supported PII types:
    - SSN
    - Credit card numbers
    - Phone numbers
    - Email addresses
    - Bank account numbers
    """
    
    # PII patterns with named groups
    PII_PATTERNS = {
        'ssn': {
            'pattern': r'\b(\d{3})[-.\s]?(\d{2})[-.\s]?(\d{4})\b',
            'redaction': '***-**-****',
            'description': 'Social Security Number'
        },
        'credit_card': {
            'pattern': r'\b(\d{4})[-.\s]?(\d{4})[-.\s]?(\d{4})[-.\s]?(\d{4})\b',
            'redaction': '****-****-****-****',
            'description': 'Credit Card Number'
        },
        'phone': {
            'pattern': r'\b(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})\b',
            'redaction': '(***) ***-****',
            'description': 'Phone Number'
        },
        'email': {
            'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'redaction': '[EMAIL REDACTED]',
            'description': 'Email Address'
        },
        'bank_account': {
            'pattern': r'\b\d{8,17}\b',  # Generic bank account pattern
            'redaction': '[ACCOUNT REDACTED]',
            'description': 'Bank Account Number',
            'context_required': True  # Only redact in certain contexts
        }
    }
    
    def __init__(self, redact_types: Optional[List[str]] = None):
        """
        Initialize redactor.
        
        Args:
            redact_types: List of PII types to redact (None = all)
        """
        self.redact_types = redact_types or list(self.PII_PATTERNS.keys())
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text.
        
        Returns:
            List of detected PII with type, location, and snippet
        """
        detections = []
        
        for pii_type in self.redact_types:
            config = self.PII_PATTERNS.get(pii_type)
            if not config:
                continue
            
            # Skip context-required patterns for now
            if config.get('context_required'):
                continue
            
            for match in re.finditer(config['pattern'], text, re.IGNORECASE):
                detections.append({
                    'type': pii_type,
                    'description': config['description'],
                    'start': match.start(),
                    'end': match.end(),
                    'snippet': text[max(0, match.start()-10):match.end()+10]
                })
        
        return detections
    
    def redact(self, text: str, replacement_style: str = "mask") -> str:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            replacement_style: "mask" (****), "type" ([SSN]), or "remove"
        
        Returns:
            Redacted text
        """
        result = text
        
        # Sort by position (reverse) to maintain offsets
        detections = sorted(self.detect(text), key=lambda d: d['start'], reverse=True)
        
        for detection in detections:
            pii_type = detection['type']
            config = self.PII_PATTERNS.get(pii_type, {})
            
            if replacement_style == "mask":
                replacement = config.get('redaction', '[REDACTED]')
            elif replacement_style == "type":
                replacement = f"[{pii_type.upper()}]"
            else:  # remove
                replacement = ""
            
            result = result[:detection['start']] + replacement + result[detection['end']:]
        
        return result
    
    def redact_dict(self, data: Dict[str, Any], recursive: bool = True) -> Dict[str, Any]:
        """
        Redact PII from a dictionary.
        
        Args:
            data: Dictionary to redact
            recursive: Process nested dicts/lists
        
        Returns:
            Redacted dictionary
        """
        result = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact(value)
            elif isinstance(value, dict) and recursive:
                result[key] = self.redact_dict(value, recursive)
            elif isinstance(value, list) and recursive:
                result[key] = [
                    self.redact_dict(item, recursive) if isinstance(item, dict)
                    else self.redact(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result


# =============================================================================
# SECURITY AUDIT LOGGING
# =============================================================================

class SecurityAuditLogger:
    """
    Specialized logger for security events.
    """
    
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
    
    def log_authentication(
        self,
        user_id: Optional[int],
        success: bool,
        method: str,
        ip: str,
        details: Optional[Dict] = None
    ):
        """Log authentication attempt."""
        event = {
            'event_type': 'authentication',
            'user_id': user_id,
            'success': success,
            'method': method,
            'ip': ip,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details or {}
        }
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, f"Auth: {event}")
    
    def log_authorization(
        self,
        user_id: int,
        resource: str,
        action: str,
        allowed: bool,
        reason: Optional[str] = None
    ):
        """Log authorization decision."""
        event = {
            'event_type': 'authorization',
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'allowed': allowed,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        level = logging.INFO if allowed else logging.WARNING
        self.logger.log(level, f"Authz: {event}")
    
    def log_threat(
        self,
        threat_type: str,
        source_ip: str,
        details: Dict[str, Any],
        severity: str = "medium"
    ):
        """Log detected security threat."""
        event = {
            'event_type': 'threat',
            'threat_type': threat_type,
            'source_ip': source_ip,
            'severity': severity,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        level = logging.CRITICAL if severity == "high" else logging.WARNING
        self.logger.log(level, f"THREAT: {event}")


# Module-level instances
rate_limiter = RateLimiter()
input_sanitizer = InputSanitizer()
pii_redactor = PIIRedactor()
security_logger = SecurityAuditLogger()
