"""Unit tests for SQLAlchemy models."""
import pytest
from app.core.models import User, Organization, Membership, Role, PlanType
from app.core.extensions import db


class TestUserModel:
    def test_create_user(self, db):
        user = User(
            email="test@example.com",
            name="Test User",
        )
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.check_password("SecurePass123!")
        assert not user.check_password("wrong")

    def test_user_str(self, db):
        user = User(email="test@example.com", name="Test")
        assert "test@example.com" in repr(user)

    def test_user_defaults(self, db):
        user = User(email="test@example.com", name="Test")
        db.session.add(user)
        db.session.commit()

        assert user.is_active is True
        assert user.is_admin is False
        assert user.is_banned is False
        assert user.email_verified is False
        assert user.login_count == 0


class TestOrganizationModel:
    def test_create_organization(self, db, registered_user):
        org = Organization(
            name="Test Corp",
            slug="test-corp",
            owner_id=registered_user.id,
            subscription_tier=PlanType.FREE.value,
        )
        db.session.add(org)
        db.session.commit()

        assert org.id is not None
        assert org.name == "Test Corp"
        assert org.member_count == 0

    def test_organization_plan_property(self, db, registered_user):
        org = Organization(
            name="Test Corp",
            slug="test-corp-2",
            owner_id=registered_user.id,
            subscription_tier=PlanType.PRO.value,
        )
        db.session.add(org)
        db.session.commit()

        plan = org.plan
        assert plan["name"] == "Pro"
        assert plan["price"] == 29


class TestMembershipModel:
    def test_create_membership(self, db, registered_user, organization):
        membership = Membership(
            user_id=registered_user.id,
            organization_id=organization.id,
            role=Role.OWNER.value,
            is_current=True,
        )
        db.session.add(membership)
        db.session.commit()

        assert membership.id is not None
        assert membership.role == Role.OWNER.value

    def test_duplicate_membership_fails(self, db, registered_user, organization):
        Membership(
            user_id=registered_user.id,
            organization_id=organization.id,
            role=Role.MEMBER.value,
        )
        with pytest.raises(Exception):
            db.session.commit()
