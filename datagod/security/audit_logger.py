"""
DataGod Audit Logging System

Comprehensive audit logging for compliance, security, and debugging.
Tracks all significant actions with full context.
"""

import logging
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Types of auditable actions."""
    # Authentication
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGE = "auth.password_change"
    MFA_ENABLED = "auth.mfa_enabled"
    MFA_DISABLED = "auth.mfa_disabled"
    
    # User Management
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    ROLE_CHANGE = "user.role_change"
    
    # Data Access
    DATA_VIEW = "data.view"
    DATA_EXPORT = "data.export"
    DATA_SEARCH = "data.search"
    
    # Record CRUD
    RECORD_CREATE = "record.create"
    RECORD_UPDATE = "record.update"
    RECORD_DELETE = "record.delete"
    RECORD_BULK_CREATE = "record.bulk_create"
    RECORD_BULK_UPDATE = "record.bulk_update"
    RECORD_BULK_DELETE = "record.bulk_delete"
    
    # Subscription/Billing
    SUBSCRIPTION_CREATE = "billing.subscription_create"
    SUBSCRIPTION_UPDATE = "billing.subscription_update"
    SUBSCRIPTION_CANCEL = "billing.subscription_cancel"
    PAYMENT_SUCCESS = "billing.payment_success"
    PAYMENT_FAILED = "billing.payment_failed"
    
    # Sharing
    SHARE_LINK_CREATE = "share.link_create"
    SHARE_LINK_ACCESS = "share.link_access"
    SHARE_LINK_DELETE = "share.link_delete"
    
    # API
    API_KEY_CREATE = "api.key_create"
    API_KEY_REVOKE = "api.key_revoke"
    API_CALL = "api.call"
    
    # System
    SYSTEM_CONFIG_CHANGE = "system.config_change"
    SCRAPER_RUN = "system.scraper_run"
    ML_MODEL_TRAIN = "system.ml_train"
    

class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents an audit log entry."""
    id: str
    action: AuditAction
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    user_email: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    description: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['action'] = self.action.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Centralized audit logging system.
    
    Features:
    - Structured audit trail for all significant actions
    - User, IP, and session tracking
    - Before/after value capture for changes
    - Configurable severity levels
    - Multiple output backends (file, database, external service)
    """
    
    def __init__(
        self,
        storage_backend: str = "file",
        log_file: str = "/var/log/datagod/audit.log",
        database_url: Optional[str] = None,
        retention_days: int = 90
    ):
        """
        Initialize audit logger.
        
        Args:
            storage_backend: 'file', 'database', or 'both'
            log_file: Path to audit log file
            database_url: SQLAlchemy database URL
            retention_days: Days to retain audit logs
        """
        self.storage_backend = storage_backend
        self.log_file = log_file
        self.database_url = database_url
        self.retention_days = retention_days
        
        self._event_count = 0
        self._file_handler = None
        
        if storage_backend in ('file', 'both'):
            self._setup_file_logging()
        
        logger.info("AuditLogger initialized with backend: %s", storage_backend)
    
    def log(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: str = "",
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            action: The action being audited
            user_id: ID of user performing action
            user_email: Email of user
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            description: Human-readable description
            old_value: Previous value (for updates)
            new_value: New value (for creates/updates)
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional context
            success: Whether action succeeded
            error_message: Error message if failed
            request_id: Unique request identifier
            session_id: User session identifier
            severity: Override default severity
            
        Returns:
            The created AuditEvent
        """
        # Determine severity if not provided
        if severity is None:
            severity = self._get_default_severity(action, success)
        
        # Generate event ID
        event_id = self._generate_event_id()
        
        # Sanitize sensitive data
        if old_value:
            old_value = self._sanitize_sensitive(old_value)
        if new_value:
            new_value = self._sanitize_sensitive(new_value)
        
        event = AuditEvent(
            id=event_id,
            action=action,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description or self._get_default_description(action),
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
            success=success,
            error_message=error_message,
            request_id=request_id,
            session_id=session_id,
        )
        
        # Store event
        self._store_event(event)
        
        # Log critical events to application logger
        if severity == AuditSeverity.CRITICAL:
            logger.warning("AUDIT CRITICAL: %s - %s", action.value, description)
        
        self._event_count += 1
        
        return event
    
    def log_request(
        self,
        request,  # FastAPI/Flask request object
        action: AuditAction,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: str = "",
        **kwargs
    ) -> AuditEvent:
        """
        Log audit event from HTTP request context.
        
        Automatically extracts user, IP, and user agent from request.
        """
        # Extract from request (FastAPI-style)
        user_id = getattr(request.state, 'user_id', None) if hasattr(request, 'state') else None
        user_email = getattr(request.state, 'user_email', None) if hasattr(request, 'state') else None
        
        # Get IP address (handle proxies)
        ip_address = request.headers.get('x-forwarded-for', '').split(',')[0].strip()
        if not ip_address:
            ip_address = getattr(request.client, 'host', None) if hasattr(request, 'client') else None
        
        user_agent = request.headers.get('user-agent', '')
        request_id = request.headers.get('x-request-id', '')
        
        return self.log(
            action=action,
            user_id=user_id,
            user_email=user_email,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            **kwargs
        )
    
    def query(
        self,
        action: Optional[AuditAction] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """
        Query audit logs with filters.
        
        Returns list of matching AuditEvents.
        """
        # This would query database in production
        # For now, return empty list (implementation depends on storage)
        logger.debug("Audit query: action=%s, user=%s, resource=%s/%s",
                    action, user_id, resource_type, resource_id)
        return []
    
    def export(
        self,
        format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **filters
    ) -> str:
        """
        Export audit logs to file.
        
        Args:
            format: 'json' or 'csv'
            start_date: Filter start
            end_date: Filter end
            **filters: Additional filters
            
        Returns:
            Path to exported file
        """
        events = self.query(start_date=start_date, end_date=end_date, **filters)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"/tmp/audit_export_{timestamp}.{format}"
        
        if format == "json":
            with open(filename, 'w') as f:
                json.dump([e.to_dict() for e in events], f, indent=2, default=str)
        elif format == "csv":
            import csv
            with open(filename, 'w', newline='') as f:
                if events:
                    writer = csv.DictWriter(f, fieldnames=events[0].to_dict().keys())
                    writer.writeheader()
                    for event in events:
                        writer.writerow(event.to_dict())
        
        return filename
    
    def get_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get summary statistics for audit logs."""
        return {
            "total_events": self._event_count,
            "storage_backend": self.storage_backend,
            "retention_days": self.retention_days,
        }
    
    def _setup_file_logging(self):
        """Setup file-based audit logging."""
        import os
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except PermissionError:
                # Fall back to temp directory
                self.log_file = f"/tmp/datagod_audit_{datetime.utcnow().strftime('%Y%m%d')}.log"
    
    def _store_event(self, event: AuditEvent):
        """Store audit event to configured backend."""
        if self.storage_backend in ('file', 'both'):
            try:
                with open(self.log_file, 'a') as f:
                    f.write(event.to_json() + '\n')
            except Exception as e:
                logger.error("Failed to write audit log: %s", e)
        
        if self.storage_backend in ('database', 'both') and self.database_url:
            # Would write to database here
            pass
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        timestamp = datetime.utcnow().isoformat()
        unique = f"{timestamp}_{self._event_count}"
        return hashlib.md5(unique.encode()).hexdigest()[:16]
    
    def _sanitize_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive fields."""
        sensitive_fields = {'password', 'token', 'secret', 'api_key', 'credit_card', 'ssn'}
        
        result = {}
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_fields):
                result[key] = '[REDACTED]'
            elif isinstance(value, dict):
                result[key] = self._sanitize_sensitive(value)
            else:
                result[key] = value
        
        return result
    
    def _get_default_severity(self, action: AuditAction, success: bool) -> AuditSeverity:
        """Get default severity for action type."""
        if not success:
            return AuditSeverity.WARNING
        
        critical_actions = {
            AuditAction.USER_DELETE,
            AuditAction.ROLE_CHANGE,
            AuditAction.API_KEY_REVOKE,
            AuditAction.SYSTEM_CONFIG_CHANGE,
            AuditAction.RECORD_BULK_DELETE,
        }
        
        warning_actions = {
            AuditAction.LOGIN_FAILED,
            AuditAction.PAYMENT_FAILED,
            AuditAction.SUBSCRIPTION_CANCEL,
        }
        
        if action in critical_actions:
            return AuditSeverity.CRITICAL
        if action in warning_actions:
            return AuditSeverity.WARNING
        
        return AuditSeverity.INFO
    
    def _get_default_description(self, action: AuditAction) -> str:
        """Get default description for action."""
        descriptions = {
            AuditAction.LOGIN: "User logged in",
            AuditAction.LOGOUT: "User logged out",
            AuditAction.LOGIN_FAILED: "Failed login attempt",
            AuditAction.USER_CREATE: "New user created",
            AuditAction.USER_UPDATE: "User profile updated",
            AuditAction.USER_DELETE: "User account deleted",
            AuditAction.DATA_EXPORT: "Data exported",
        }
        return descriptions.get(action, action.value)


# Decorator for automatic audit logging
def audited(action: AuditAction, resource_type: Optional[str] = None):
    """
    Decorator to automatically audit function calls.
    
    Usage:
        @audited(AuditAction.RECORD_CREATE, "property")
        async def create_property(request, data):
            ...
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            audit_logger = get_audit_logger()
            
            try:
                result = await func(*args, **kwargs)
                
                # Try to extract request from args
                request = args[0] if args else None
                
                audit_logger.log(
                    action=action,
                    resource_type=resource_type,
                    success=True,
                )
                
                return result
            except Exception as e:
                audit_logger.log(
                    action=action,
                    resource_type=resource_type,
                    success=False,
                    error_message=str(e),
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            audit_logger = get_audit_logger()
            
            try:
                result = func(*args, **kwargs)
                audit_logger.log(action=action, resource_type=resource_type, success=True)
                return result
            except Exception as e:
                audit_logger.log(action=action, resource_type=resource_type, success=False, error_message=str(e))
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Default logger instance
_default_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the default audit logger instance."""
    global _default_audit_logger
    if _default_audit_logger is None:
        _default_audit_logger = AuditLogger()
    return _default_audit_logger
