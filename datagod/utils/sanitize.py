"""
DataGod Input Sanitization Utilities
Prevents XSS, SQL injection patterns, and other malicious input
"""

import re
import html
from typing import Optional


# Known XSS patterns to strip
_XSS_PATTERNS = [
    re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),
    re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<embed[^>]*>', re.IGNORECASE),
    re.compile(r'<link[^>]*>', re.IGNORECASE),
    re.compile(r'expression\s*\(', re.IGNORECASE),
    re.compile(r'url\s*\(', re.IGNORECASE),
    re.compile(r'data:', re.IGNORECASE),
]

# SQL injection patterns to detect
_SQL_PATTERNS = [
    re.compile(r"('|\")\s*(OR|AND)\s+\d+\s*=\s*\d+", re.IGNORECASE),
    re.compile(r";\s*DROP\s+", re.IGNORECASE),
    re.compile(r";\s*DELETE\s+", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT", re.IGNORECASE),
    re.compile(r"--\s*$", re.IGNORECASE),
]


def sanitize_input(text: Optional[str], max_length: int = 10000) -> Optional[str]:
    """
    Sanitize user input text to prevent XSS and other injection attacks.
    
    Args:
        text: Raw user input string
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string safe for storage and display
    """
    if text is None:
        return None

    if not isinstance(text, str):
        text = str(text)

    # Truncate to max length
    text = text[:max_length]

    # HTML-escape special characters
    text = html.escape(text, quote=True)

    # Strip known XSS patterns
    for pattern in _XSS_PATTERNS:
        text = pattern.sub('', text)

    # Strip null bytes
    text = text.replace('\x00', '')

    # Normalize whitespace (collapse multiple spaces, strip leading/trailing)
    text = ' '.join(text.split())

    return text


def sanitize_search_query(query: Optional[str]) -> Optional[str]:
    """
    Sanitize search query input — less aggressive than general sanitization
    to preserve search-specific characters like quotes for phrase search.
    
    Args:
        query: Raw search query
    
    Returns:
        Sanitized search query
    """
    if query is None:
        return None

    if not isinstance(query, str):
        query = str(query)

    # Truncate
    query = query[:500]

    # Strip script tags and event handlers
    for pattern in _XSS_PATTERNS:
        query = pattern.sub('', query)

    # Strip null bytes
    query = query.replace('\x00', '')

    # Normalize whitespace
    query = ' '.join(query.split())

    return query


def is_suspicious_input(text: str) -> bool:
    """
    Check if input contains suspicious patterns that may indicate
    an injection attempt (SQL injection, XSS, etc.).
    
    Args:
        text: Input text to check
    
    Returns:
        True if suspicious patterns detected
    """
    if not text:
        return False

    # Check SQL injection patterns
    for pattern in _SQL_PATTERNS:
        if pattern.search(text):
            return True

    # Check for excessive special characters (potential attack payload)
    special_count = sum(1 for c in text if c in '<>{}[]|\\^~`')
    if special_count > len(text) * 0.3:
        return True

    return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.
    
    Args:
        filename: Raw filename
    
    Returns:
        Safe filename
    """
    # Remove path separators
    filename = filename.replace('/', '').replace('\\', '')
    # Remove null bytes
    filename = filename.replace('\x00', '')
    # Remove leading dots (hidden files / traversal)
    filename = filename.lstrip('.')
    # Only allow alphanumeric, dash, underscore, dot
    filename = re.sub(r'[^\w\-.]', '_', filename)
    # Truncate
    return filename[:255] if filename else 'unnamed'
