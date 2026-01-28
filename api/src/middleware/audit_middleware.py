"""
API Audit Middleware (Phase 1.4 - Audit Compliance)

Provides audit-grade request/response logging for compliance and reproducibility.
Integrates with the AuditLog model for immutable audit trails.

Features:
- Comprehensive request logging (method, path, headers, body)
- Response hashing for reproducibility
- Blockchain-style checksums for tamper detection
- Integration with AuditLog model for persistence
- Snapshot creation for point-in-time queries
"""

import time
import uuid
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from functools import wraps

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    from fastapi import FastAPI
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    Request = None
    Response = None
    BaseHTTPMiddleware = object

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for creating and managing audit log entries.
    
    Implements blockchain-style chaining with checksums for tamper detection.
    """
    
    def __init__(self):
        self._last_checksum: Optional[str] = None
        self._log_buffer: list = []
        self._buffer_size = 100  # Flush to database every N entries
    
    def compute_checksum(self, data: Dict[str, Any]) -> str:
        """Compute SHA-256 checksum of audit entry data."""
        # Include previous checksum for chain integrity
        data_with_chain = {
            **data,
            'previous_checksum': self._last_checksum
        }
        content = json.dumps(data_with_chain, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def compute_response_hash(self, response_body: bytes) -> str:
        """Compute SHA-256 hash of response body for reproducibility."""
        return hashlib.sha256(response_body).hexdigest()
    
    def create_audit_entry(
        self,
        event_type: str,
        action: str,
        request: Optional[Request] = None,
        response_hash: Optional[str] = None,
        actor_id: Optional[int] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an audit log entry.
        
        Returns the entry data (to be persisted to AuditLog table).
        """
        event_id = str(uuid.uuid4())
        event_timestamp = datetime.utcnow()
        
        # Extract actor info from request
        actor_ip = None
        actor_user_agent = None
        session_id = None
        
        if request:
            actor_ip = self._get_client_ip(request)
            actor_user_agent = request.headers.get('user-agent', '')[:500]
            session_id = request.cookies.get('session_id')
        
        # Build entry data
        entry_data = {
            'event_id': event_id,
            'event_type': event_type,
            'event_timestamp': event_timestamp.isoformat(),
            'actor_id': actor_id,
            'actor_type': 'user' if actor_id else 'system',
            'actor_ip': actor_ip,
            'actor_user_agent': actor_user_agent,
            'target_type': target_type,
            'target_id': target_id,
            'action': action,
            'action_data': action_data,
            'request_id': request_id or str(uuid.uuid4()),
            'session_id': session_id,
            'response_hash': response_hash,
            'success': success,
            'error_message': error_message,
        }
        
        # Compute checksum including chain reference
        checksum = self.compute_checksum(entry_data)
        entry_data['checksum'] = checksum
        entry_data['previous_checksum'] = self._last_checksum
        
        # Update chain
        self._last_checksum = checksum
        
        # Add to buffer
        self._log_buffer.append(entry_data)
        
        # Flush if buffer is full
        if len(self._log_buffer) >= self._buffer_size:
            self.flush()
        
        return entry_data
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request, handling proxies."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded = request.headers.get('x-forwarded-for')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Direct connection
        if request.client:
            return request.client.host
        
        return None
    
    def flush(self) -> int:
        """
        Flush buffered audit entries to database.
        
        Returns number of entries flushed.
        """
        if not self._log_buffer:
            return 0
        
        count = len(self._log_buffer)
        
        try:
            # Import here to avoid circular imports
            from datagod.models import AuditLog, db_session
            
            session = db_session()
            try:
                for entry in self._log_buffer:
                    audit_log = AuditLog(
                        event_id=entry['event_id'],
                        event_type=entry['event_type'],
                        event_timestamp=datetime.fromisoformat(entry['event_timestamp']),
                        actor_id=entry['actor_id'],
                        actor_type=entry['actor_type'],
                        actor_ip=entry['actor_ip'],
                        actor_user_agent=entry['actor_user_agent'],
                        target_type=entry['target_type'],
                        target_id=entry['target_id'],
                        action=entry['action'],
                        action_data=entry['action_data'],
                        request_id=entry['request_id'],
                        session_id=entry['session_id'],
                        response_hash=entry['response_hash'],
                        success=entry['success'],
                        error_message=entry['error_message'],
                        checksum=entry['checksum'],
                        previous_checksum=entry['previous_checksum']
                    )
                    session.add(audit_log)
                
                session.commit()
                logger.info(f"Flushed {count} audit entries to database")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to flush audit entries: {e}")
                raise
            finally:
                session.close()
                
        except ImportError:
            # Database not available, log to file as fallback
            logger.warning("Database not available, logging audit entries to file")
            for entry in self._log_buffer:
                logger.info(f"AUDIT: {json.dumps(entry, default=str)}")
        
        self._log_buffer.clear()
        return count


# Global audit service instance
audit_service = AuditService()


if FASTAPI_AVAILABLE:
    class AuditMiddleware(BaseHTTPMiddleware):
        """
        Middleware for comprehensive API audit logging.
        
        Captures:
        - All API requests (method, path, query params)
        - Request headers (sanitized)
        - Response status and timing
        - Response hash for reproducibility
        - User context when authenticated
        """
        
        # Paths to exclude from audit logging
        EXCLUDED_PATHS = {
            '/health',
            '/healthz',
            '/liveness',
            '/readiness',
            '/metrics',
            '/favicon.ico',
            '/docs',
            '/redoc',
            '/openapi.json',
        }
        
        # Headers to exclude from logging (sensitive data)
        EXCLUDED_HEADERS = {
            'authorization',
            'cookie',
            'x-api-key',
            'x-auth-token',
        }
        
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            """Process request and create audit entry."""
            
            # Skip excluded paths
            if request.url.path in self.EXCLUDED_PATHS:
                return await call_next(request)
            
            # Generate request ID if not present
            request_id = request.headers.get('x-request-id', str(uuid.uuid4()))
            
            # Record start time
            start_time = time.time()
            
            # Extract request info
            request_info = self._extract_request_info(request)
            
            # Process request
            response = None
            error_message = None
            success = True
            
            try:
                response = await call_next(request)
                
                # Capture response body for hashing
                response_body = b''
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Compute response hash
                response_hash = audit_service.compute_response_hash(response_body)
                
                # Create new response with captured body
                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
                # Add audit headers
                response.headers['x-request-id'] = request_id
                response.headers['x-response-hash'] = response_hash[:16]  # First 16 chars
                
                success = response.status_code < 400
                
            except Exception as e:
                error_message = str(e)
                success = False
                response_hash = None
                raise
            
            finally:
                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000
                
                # Extract user ID if authenticated
                actor_id = None
                if hasattr(request.state, 'user'):
                    actor_id = getattr(request.state.user, 'id', None)
                
                # Create audit entry
                action_data = {
                    'method': request.method,
                    'path': request.url.path,
                    'query_params': dict(request.query_params),
                    'headers': request_info['headers'],
                    'latency_ms': round(latency_ms, 2),
                    'status_code': response.status_code if response else None,
                }
                
                # Determine action from HTTP method
                action = self._method_to_action(request.method)
                
                # Determine target from path
                target_type, target_id = self._extract_target(request.url.path)
                
                audit_service.create_audit_entry(
                    event_type='api_request',
                    action=action,
                    request=request,
                    response_hash=response_hash if 'response_hash' in dir() else None,
                    actor_id=actor_id,
                    target_type=target_type,
                    target_id=target_id,
                    action_data=action_data,
                    success=success,
                    error_message=error_message,
                    request_id=request_id
                )
            
            return response
        
        def _extract_request_info(self, request: Request) -> Dict[str, Any]:
            """Extract sanitized request information."""
            # Sanitize headers
            headers = {}
            for key, value in request.headers.items():
                if key.lower() not in self.EXCLUDED_HEADERS:
                    headers[key] = value
                else:
                    headers[key] = '[REDACTED]'
            
            return {
                'method': request.method,
                'path': request.url.path,
                'query_params': dict(request.query_params),
                'headers': headers,
            }
        
        def _method_to_action(self, method: str) -> str:
            """Map HTTP method to action name."""
            mapping = {
                'GET': 'read',
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'partial_update',
                'DELETE': 'delete',
                'HEAD': 'head',
                'OPTIONS': 'options',
            }
            return mapping.get(method.upper(), 'unknown')
        
        def _extract_target(self, path: str) -> tuple:
            """Extract target type and ID from API path."""
            parts = [p for p in path.split('/') if p and p != 'api' and p != 'v2']
            
            if not parts:
                return None, None
            
            target_type = parts[0]
            target_id = parts[1] if len(parts) > 1 and parts[1].isdigit() else None
            
            return target_type, target_id


def audit_action(event_type: str, action: str, target_type: Optional[str] = None):
    """
    Decorator for auditing specific function calls.
    
    Usage:
        @audit_action('record_access', 'export', 'record')
        async def export_records(record_ids: list):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            result = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                
                audit_service.create_audit_entry(
                    event_type=event_type,
                    action=action,
                    target_type=target_type,
                    action_data={
                        'function': func.__name__,
                        'latency_ms': round(latency_ms, 2),
                    },
                    success=success,
                    error_message=error_message
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                
                audit_service.create_audit_entry(
                    event_type=event_type,
                    action=action,
                    target_type=target_type,
                    action_data={
                        'function': func.__name__,
                        'latency_ms': round(latency_ms, 2),
                    },
                    success=success,
                    error_message=error_message
                )
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def setup_audit_middleware(app: 'FastAPI') -> None:
    """Add audit middleware to FastAPI application."""
    if FASTAPI_AVAILABLE:
        app.add_middleware(AuditMiddleware)
        logger.info("Audit middleware enabled")
    else:
        logger.warning("FastAPI not available, audit middleware not enabled")
