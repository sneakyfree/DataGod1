"""
Tests for User model.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest


class TestUserModelImport:
    """Tests for User model import."""

    def test_user_import(self):
        """Test User can be imported."""
        from datagod.models.user import User

        assert User is not None

    def test_user_tablename(self):
        """Test User table name."""
        from datagod.models.user import User

        assert User.__tablename__ == "users"


class TestUserModelAttributes:
    """Tests for User model attributes."""

    def test_user_has_id_column(self):
        """Test User has id column."""
        from datagod.models.user import User

        assert hasattr(User, "id")

    def test_user_has_username_column(self):
        """Test User has username column."""
        from datagod.models.user import User

        assert hasattr(User, "username")

    def test_user_has_email_column(self):
        """Test User has email column."""
        from datagod.models.user import User

        assert hasattr(User, "email")

    def test_user_has_password_column(self):
        """Test User has hashed_password column."""
        from datagod.models.user import User

        assert hasattr(User, "hashed_password")

    def test_user_has_full_name_column(self):
        """Test User has full_name column."""
        from datagod.models.user import User

        assert hasattr(User, "full_name")

    def test_user_has_disabled_column(self):
        """Test User has disabled column."""
        from datagod.models.user import User

        assert hasattr(User, "disabled")

    def test_user_has_roles_column(self):
        """Test User has roles column."""
        from datagod.models.user import User

        assert hasattr(User, "roles")

    def test_user_has_subscription_tier_column(self):
        """Test User has subscription_tier column."""
        from datagod.models.user import User

        assert hasattr(User, "subscription_tier")

    def test_user_has_timestamps(self):
        """Test User has timestamp columns."""
        from datagod.models.user import User

        assert hasattr(User, "created_at")
        assert hasattr(User, "updated_at")

    def test_user_has_login_tracking(self):
        """Test User has login tracking columns."""
        from datagod.models.user import User

        assert hasattr(User, "last_login")
        assert hasattr(User, "login_count")
        assert hasattr(User, "failed_login_count")

    def test_user_has_password_reset_fields(self):
        """Test User has password reset fields."""
        from datagod.models.user import User

        assert hasattr(User, "password_reset_token")
        assert hasattr(User, "password_reset_expires")

    def test_user_has_email_verification_fields(self):
        """Test User has email verification fields."""
        from datagod.models.user import User

        assert hasattr(User, "email_verification_token")
        assert hasattr(User, "email_verification_expires")


class TestUserModelMethods:
    """Tests for User model methods."""

    def test_user_has_role_method(self):
        """Test User has has_role method."""
        from datagod.models.user import User

        user = User()
        user.roles = ["user", "admin"]

        assert user.has_role("admin") is True
        assert user.has_role("user") is True
        assert user.has_role("superadmin") is False

    def test_user_has_role_empty_roles(self):
        """Test has_role with empty/None roles."""
        from datagod.models.user import User

        user = User()
        user.roles = None

        assert user.has_role("admin") is False

    def test_user_has_any_role_method(self):
        """Test User has has_any_role method."""
        from datagod.models.user import User

        user = User()
        user.roles = ["user"]

        assert user.has_any_role(["admin", "user"]) is True
        assert user.has_any_role(["admin", "superadmin"]) is False

    def test_user_has_any_role_empty_roles(self):
        """Test has_any_role with empty/None roles."""
        from datagod.models.user import User

        user = User()
        user.roles = None

        assert user.has_any_role(["admin"]) is False

    def test_user_is_admin_method(self):
        """Test User is_admin method."""
        from datagod.models.user import User

        admin_user = User()
        admin_user.roles = ["admin"]
        assert admin_user.is_admin() is True

        regular_user = User()
        regular_user.roles = ["user"]
        assert regular_user.is_admin() is False

    def test_user_is_active_method(self):
        """Test User is_active method."""
        from datagod.models.user import User

        active_user = User()
        active_user.disabled = False
        active_user.locked_until = None
        assert active_user.is_active() is True

    def test_user_is_active_disabled(self):
        """Test is_active returns False when disabled."""
        from datagod.models.user import User

        user = User()
        user.disabled = True
        user.locked_until = None
        assert user.is_active() is False

    def test_user_is_active_locked(self):
        """Test is_active returns False when locked."""
        from datagod.models.user import User

        user = User()
        user.disabled = False
        user.locked_until = datetime.utcnow() + timedelta(hours=1)
        assert user.is_active() is False

    def test_user_is_active_lock_expired(self):
        """Test is_active returns True when lock expired."""
        from datagod.models.user import User

        user = User()
        user.disabled = False
        user.locked_until = datetime.utcnow() - timedelta(hours=1)
        assert user.is_active() is True


class TestUserFeatureAccess:
    """Tests for User feature access."""

    def test_can_access_feature_free_tier(self):
        """Test free tier feature access."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = "free"

        assert user.can_access_feature("basic_search") is True
        assert user.can_access_feature("view_records") is True
        assert user.can_access_feature("export_csv") is False
        assert user.can_access_feature("api_access") is False

    def test_can_access_feature_basic_tier(self):
        """Test basic tier feature access."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = "basic"

        assert user.can_access_feature("basic_search") is True
        assert user.can_access_feature("export_csv") is True
        assert user.can_access_feature("advanced_search") is True
        assert user.can_access_feature("api_access") is False

    def test_can_access_feature_pro_tier(self):
        """Test pro tier feature access."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = "pro"

        assert user.can_access_feature("basic_search") is True
        assert user.can_access_feature("export_excel") is True
        assert user.can_access_feature("api_access") is True
        assert user.can_access_feature("unlimited_exports") is False

    def test_can_access_feature_enterprise_tier(self):
        """Test enterprise tier feature access."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = "enterprise"

        assert user.can_access_feature("basic_search") is True
        assert user.can_access_feature("unlimited_exports") is True
        assert user.can_access_feature("priority_support") is True
        assert user.can_access_feature("custom_integrations") is True

    def test_can_access_feature_unknown_tier(self):
        """Test unknown tier defaults to free."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = "unknown_tier"

        # Should default to free tier features
        assert user.can_access_feature("basic_search") is True
        assert user.can_access_feature("export_csv") is False

    def test_can_access_feature_none_tier(self):
        """Test None tier defaults to free."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = None

        # Should default to free tier features
        assert user.can_access_feature("basic_search") is True


class TestUserToDict:
    """Tests for User to_dict method."""

    def test_to_dict_basic(self):
        """Test to_dict with basic fields."""
        from datagod.models.user import User

        user = User()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.full_name = "Test User"
        user.disabled = False
        user.email_verified = True
        user.roles = ["user"]
        user.subscription_tier = "free"
        user.subscription_expires = None
        user.last_login = None
        user.created_at = datetime(2023, 1, 1, 12, 0, 0)
        user.updated_at = datetime(2023, 1, 1, 12, 0, 0)

        result = user.to_dict()

        assert result["id"] == 1
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert result["full_name"] == "Test User"
        assert result["disabled"] is False
        assert "password_reset_token" not in result  # Sensitive field excluded

    def test_to_dict_with_sensitive(self):
        """Test to_dict with sensitive fields included."""
        from datagod.models.user import User

        user = User()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.full_name = "Test User"
        user.disabled = False
        user.email_verified = True
        user.roles = ["user"]
        user.subscription_tier = "free"
        user.subscription_expires = None
        user.last_login = None
        user.created_at = datetime(2023, 1, 1, 12, 0, 0)
        user.updated_at = datetime(2023, 1, 1, 12, 0, 0)
        user.email_verification_token = "token123"
        user.password_reset_token = "reset456"
        user.login_count = 5
        user.failed_login_count = 2
        user.api_calls_today = 100
        user.exports_this_month = 10

        result = user.to_dict(include_sensitive=True)

        assert "password_reset_token" in result
        assert result["password_reset_token"] == "reset456"
        assert result["login_count"] == 5
        assert result["api_calls_today"] == 100

    def test_to_dict_with_dates(self):
        """Test to_dict with date fields."""
        from datagod.models.user import User

        user = User()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.full_name = None
        user.disabled = False
        user.email_verified = False
        user.roles = []
        user.subscription_tier = "free"
        user.subscription_expires = datetime(2024, 1, 1)
        user.last_login = datetime(2023, 12, 15, 10, 30, 0)
        user.created_at = datetime(2023, 1, 1)
        user.updated_at = datetime(2023, 6, 1)

        result = user.to_dict()

        assert result["subscription_expires"] == "2024-01-01T00:00:00"
        assert result["last_login"] == "2023-12-15T10:30:00"


class TestUserRepr:
    """Tests for User __repr__ method."""

    def test_repr(self):
        """Test __repr__ method."""
        from datagod.models.user import User

        user = User()
        user.id = 42
        user.username = "johndoe"
        user.email = "john@example.com"

        repr_str = repr(user)
        assert "42" in repr_str
        assert "johndoe" in repr_str
        assert "john@example.com" in repr_str
