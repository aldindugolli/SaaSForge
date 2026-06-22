"""Unit tests for OrganizationService."""
import pytest
from app.services.org_service import OrganizationService
from app.services.base import ValidationError, PermissionError, NotFoundError
from app.core.models import Role, Membership


class TestOrganizationService:
    def test_create_organization(self, db, registered_user):
        org = OrganizationService.create("My Company", registered_user)
        assert org.name == "My Company"
        assert org.owner_id == registered_user.id
        assert org.subscription_tier == "free"
        assert org.max_members == 1

        membership = Membership.query.filter_by(
            user_id=registered_user.id, organization_id=org.id
        ).first()
        assert membership is not None
        assert membership.role == Role.OWNER.value

    def test_switch_organization(self, db, registered_user):
        org1 = OrganizationService.create("Org 1", registered_user)
        org2 = OrganizationService.create("Org 2", registered_user, "org-2")

        result = OrganizationService.switch_organization(registered_user, org2.id)
        assert result

        current = registered_user.current_organization
        assert current.id == org2.id

    def test_switch_non_member_raises_error(self, db, registered_user):
        from app.core.models import User
        other_user = User(email="other@example.com", name="Other")
        other_user.set_password("TestPass123!")
        db.session.add(other_user)
        db.session.commit()

        with pytest.raises(PermissionError):
            OrganizationService.switch_organization(other_user, "nonexistent-id")

    def test_get_members(self, db, registered_user, organization):
        Membership(
            user_id=registered_user.id,
            organization_id=organization.id,
            role=Role.OWNER.value,
        )
        db.session.commit()

        members = OrganizationService.get_members(organization.id)
        assert len(members) >= 1

    def test_update_member_role(self, db, registered_user, organization):
        from app.core.models import User
        other = User(email="member@example.com", name="Member")
        other.set_password("TestPass123!")
        db.session.add(other)
        db.session.commit()

        Membership(
            user_id=other.id,
            organization_id=organization.id,
            role=Role.MEMBER.value,
        )
        db.session.commit()

        result = OrganizationService.update_member_role(
            organization.id, other.id, Role.ADMIN.value, registered_user
        )
        assert result

        membership = Membership.query.filter_by(
            user_id=other.id, organization_id=organization.id
        ).first()
        assert membership.role == Role.ADMIN.value

    def test_remove_member(self, db, registered_user, organization):
        from app.core.models import User
        other = User(email="remove@example.com", name="Remove")
        other.set_password("TestPass123!")
        db.session.add(other)
        db.session.commit()

        Membership(
            user_id=other.id,
            organization_id=organization.id,
            role=Role.MEMBER.value,
        )
        db.session.commit()

        result = OrganizationService.remove_member(organization.id, other.id, registered_user)
        assert result

        membership = Membership.query.filter_by(
            user_id=other.id, organization_id=organization.id
        ).first()
        assert membership is None
