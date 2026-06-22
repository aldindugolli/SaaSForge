import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, session
from flask_login import login_user

from app.services.impersonation_service import ImpersonationService
from app.core.models import User


class TestImpersonationService:
    def test_start_impersonation(self, app, db):
        admin = User(id="admin-1", email="admin@test.com", name="Admin", is_admin=True)
        target = User(id="user-1", email="user@test.com", name="User")
        db.session.add_all([admin, target])
        db.session.commit()

        with app.test_request_context():
            login_user(admin)
            result = ImpersonationService.start_impersonation(admin, target, "Testing")
            assert result is True
            assert ImpersonationService.is_impersonating()
            assert ImpersonationService.get_impersonator_id() == "admin-1"
            assert ImpersonationService.get_impersonation_reason() == "Testing"

    def test_non_admin_cannot_impersonate(self, app, db):
        non_admin = User(id="imp-na-1", email="imp-na-1@test.com", name="NonAdmin", is_admin=False)
        target = User(id="imp-na-2", email="imp-na-2@test.com", name="Target")
        db.session.add_all([non_admin, target])
        db.session.commit()

        with app.test_request_context():
            login_user(non_admin)
            result = ImpersonationService.start_impersonation(non_admin, target, "hack")
            assert result is False

    def test_stop_impersonation(self, app, db):
        admin = User(id="imp-stop-1", email="imp-stop-1@test.com", name="Admin", is_admin=True)
        target = User(id="imp-stop-2", email="imp-stop-2@test.com", name="User")
        db.session.add_all([admin, target])
        db.session.commit()

        with app.test_request_context():
            login_user(admin)
            ImpersonationService.start_impersonation(admin, target, "Testing")
            assert ImpersonationService.is_impersonating()

            ImpersonationService.stop_impersonation()
            assert not ImpersonationService.is_impersonating()

    def test_cannot_impersonate_admin(self, app, db):
        admin = User(id="imp-cia-1", email="imp-cia-1@test.com", name="Admin", is_admin=True)
        other_admin = User(id="imp-cia-2", email="imp-cia-2@test.com", name="Admin2", is_admin=True)
        db.session.add_all([admin, other_admin])
        db.session.commit()

        with app.test_request_context():
            login_user(admin)
            result = ImpersonationService.start_impersonation(admin, other_admin, "test")
            assert result is False
