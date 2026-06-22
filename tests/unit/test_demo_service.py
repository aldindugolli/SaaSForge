"""Unit tests for the demo environment service."""


class TestDemoService:
    def test_demo_accounts_defined(self):
        from app.services.demo_service import DEMO_ACCOUNTS
        assert len(DEMO_ACCOUNTS) >= 2
        emails = [a["email"] for a in DEMO_ACCOUNTS]
        assert "admin@saasforge.com" in emails
        assert "demo@saasforge.com" in emails

    def test_is_demo_mode_false_by_default(self, app):
        from app.services.demo_service import is_demo_mode
        assert is_demo_mode() is False

    def test_is_demo_mode_true(self, app):
        from app.services.demo_service import is_demo_mode
        app.config["DEMO_MODE"] = True
        assert is_demo_mode() is True
        app.config["DEMO_MODE"] = False

    def test_is_demo_user(self, app, db):
        from app.core.models import User
        user = User(email="nondemo@example.com", name="Non Demo")
        db.session.add(user)
        db.session.flush()
        from app.services.demo_service import is_demo_user
        assert is_demo_user(user) is False

    def test_create_seed_data(self, app, db):
        from app.services.demo_service import create_seed_data
        result = create_seed_data()
        assert len(result) > 0

    def test_get_allowed_actions(self):
        from app.services.demo_service import get_allowed_actions
        actions = get_allowed_actions()
        assert len(actions) > 0
        assert all(isinstance(a, str) for a in actions)
