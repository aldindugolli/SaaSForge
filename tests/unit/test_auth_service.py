"""Unit tests for AuthService."""
import pytest
from app.services.auth_service import AuthService
from app.services.base import ValidationError, PermissionError


class TestAuthService:
    def test_validate_password_valid(self):
        is_valid, error = AuthService.validate_password("TestPass123!")
        assert is_valid
        assert error == ""

    def test_validate_password_too_short(self):
        is_valid, error = AuthService.validate_password("Ab1!")
        assert not is_valid
        assert "8 characters" in error

    def test_validate_password_no_uppercase(self):
        is_valid, error = AuthService.validate_password("testpass123!")
        assert not is_valid
        assert "uppercase" in error

    def test_validate_password_no_lowercase(self):
        is_valid, error = AuthService.validate_password("TESTPASS123!")
        assert not is_valid
        assert "lowercase" in error

    def test_validate_password_no_number(self):
        is_valid, error = AuthService.validate_password("TestPassTest!")
        assert not is_valid
        assert "number" in error

    def test_validate_password_no_special(self):
        is_valid, error = AuthService.validate_password("TestPass1234")
        assert not is_valid
        assert "special" in error

    def test_validate_email_valid(self):
        is_valid, error = AuthService.validate_email("test@example.com")
        assert is_valid

    def test_validate_email_invalid(self):
        is_valid, error = AuthService.validate_email("not-an-email")
        assert not is_valid

    def test_register_success(self, db):
        user = AuthService.register("new@example.com", "TestPass123!", "New User")
        assert user.email == "new@example.com"
        assert user.name == "New User"
        assert user.email_verified is False
        assert user.check_password("TestPass123!")

    def test_register_duplicate_email(self, db, registered_user):
        with pytest.raises(ValidationError, match="already exists"):
            AuthService.register("test@example.com", "TestPass123!", "Duplicate")

    def test_register_weak_password(self, db):
        with pytest.raises(ValidationError, match="Password"):
            AuthService.register("weak@example.com", "short", "Weak")

    def test_register_invalid_email(self, db):
        with pytest.raises(ValidationError, match="email"):
            AuthService.register("invalid", "TestPass123!", "Invalid")

    def test_login_success(self, db, registered_user):
        user = AuthService.login("test@example.com", "TestPass123!")
        assert user.email == "test@example.com"

    def test_login_wrong_password(self, db, registered_user):
        with pytest.raises(ValidationError, match="Invalid"):
            AuthService.login("test@example.com", "WrongPass123!")

    def test_login_nonexistent_user(self, db):
        with pytest.raises(ValidationError, match="Invalid"):
            AuthService.login("nonexistent@example.com", "TestPass123!")

    def test_login_disabled_user(self, db, registered_user):
        registered_user.is_active = False
        db.session.commit()
        with pytest.raises(PermissionError, match="deactivated"):
            AuthService.login("test@example.com", "TestPass123!")

    def test_change_password(self, db, registered_user):
        result = AuthService.change_password(registered_user, "TestPass123!", "NewPass123!")
        assert result
        assert registered_user.check_password("NewPass123!")

    def test_change_password_wrong_current(self, db, registered_user):
        with pytest.raises(ValidationError, match="incorrect"):
            AuthService.change_password(registered_user, "WrongPass123!", "NewPass123!")
