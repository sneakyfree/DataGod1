"""
User model for DataGod authentication and user management
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Optional


class User:
    """
    Represents a user in the DataGod system.

    This model handles authentication, authorization, and user profile data.
    Supports:
    - Username/email authentication
    - Role-based access control (RBAC)
    - Password reset flow with tokens
    - Email verification
    - Subscription tracking
    """
    __tablename__ = 'users'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Authentication fields
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Profile information
    full_name = Column(String(255), nullable=True)

    # Account status
    disabled = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Roles and permissions (stored as JSON array)
    roles = Column(JSON, default=lambda: ["user"], nullable=False)

    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires = Column(DateTime, nullable=True)

    # Login tracking
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    failed_login_count = Column(Integer, default=0, nullable=False)
    last_failed_login = Column(DateTime, nullable=True)

    # Account lockout
    locked_until = Column(DateTime, nullable=True)

    # Subscription (basic tracking - full subscription model separate)
    subscription_tier = Column(String(50), default='free', nullable=False)  # free, basic, pro, enterprise
    subscription_expires = Column(DateTime, nullable=True)

    # Stripe integration
    stripe_customer_id = Column(String(255), nullable=True, unique=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True, index=True)

    # API usage tracking
    api_calls_today = Column(Integer, default=0, nullable=False)
    api_calls_reset_at = Column(DateTime, nullable=True)
    exports_this_month = Column(Integer, default=0, nullable=False)
    exports_reset_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Additional profile data
    profile_data = Column(JSON, nullable=True)  # Avatar URL, preferences, etc.

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_username', 'username'),
        Index('idx_user_reset_token', 'password_reset_token'),
        Index('idx_user_subscription', 'subscription_tier'),
        Index('idx_user_disabled', 'disabled'),
        Index('idx_user_stripe_customer', 'stripe_customer_id'),
        Index('idx_user_stripe_subscription', 'stripe_subscription_id'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in (self.roles or [])

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        user_roles = self.roles or []
        return any(role in user_roles for role in roles)

    def is_admin(self) -> bool:
        """Check if user is an admin"""
        return self.has_role("admin")

    def is_active(self) -> bool:
        """Check if user account is active (not disabled and not locked)"""
        if self.disabled:
            return False
        if self.locked_until and self.locked_until > datetime.utcnow():
            return False
        return True

    def can_access_feature(self, feature: str) -> bool:
        """
        Check if user's subscription tier allows access to a feature.
        Override this with actual feature gating logic.
        """
        tier_features = {
            'free': ['basic_search', 'view_records'],
            'basic': ['basic_search', 'view_records', 'export_csv', 'advanced_search'],
            'pro': ['basic_search', 'view_records', 'export_csv', 'advanced_search',
                    'export_excel', 'bulk_operations', 'api_access'],
            'enterprise': ['basic_search', 'view_records', 'export_csv', 'advanced_search',
                          'export_excel', 'bulk_operations', 'api_access', 'unlimited_exports',
                          'priority_support', 'custom_integrations']
        }
        tier = self.subscription_tier or 'free'
        allowed_features = tier_features.get(tier, tier_features['free'])
        return feature in allowed_features

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary representation.

        Args:
            include_sensitive: If True, include sensitive fields like tokens

        Returns:
            Dictionary representation of user
        """
        result = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'disabled': self.disabled,
            'email_verified': self.email_verified,
            'roles': self.roles,
            'subscription_tier': self.subscription_tier,
            'subscription_expires': self.subscription_expires.isoformat() if self.subscription_expires else None,
            'stripe_customer_id': self.stripe_customer_id,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_sensitive:
            result.update({
                'email_verification_token': self.email_verification_token,
                'password_reset_token': self.password_reset_token,
                'login_count': self.login_count,
                'failed_login_count': self.failed_login_count,
                'api_calls_today': self.api_calls_today,
                'exports_this_month': self.exports_this_month,
                'stripe_subscription_id': self.stripe_subscription_id,
            })

        return result
