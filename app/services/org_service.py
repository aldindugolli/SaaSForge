from datetime import UTC, datetime, timedelta

from app.core.extensions import cache, cache_service, db
from app.core.models import (
    AuditLog,
    Invitation,
    Membership,
    Organization,
    PlanType,
    Role,
    User,
)
from app.services.base import NotFoundError, PermissionError, ValidationError


class OrganizationService:
    @staticmethod
    def create(name: str, owner: User, slug: str = None) -> Organization:
        if not slug:
            slug = OrganizationService._generate_slug(name)
        else:
            if Organization.query.filter_by(slug=slug).first():
                raise ValidationError("Organization slug already exists.")

        org = Organization(
            name=name,
            slug=slug,
            owner_id=owner.id,
            subscription_tier=PlanType.FREE.value,
            max_members=1,
        )
        db.session.add(org)
        db.session.flush()

        # Set all existing memberships for this user to not current
        Membership.query.filter_by(user_id=owner.id).update({"is_current": False})

        Membership(
            user_id=owner.id,
            organization_id=org.id,
            role=Role.OWNER.value,
            is_current=True,
        )

        AuditLog(
            actor_id=owner.id,
            organization_id=org.id,
            action="organization.created",
            resource_type="organization",
            resource_id=org.id,
            metadata={"name": name},
        )

        db.session.commit()
        cache_service.invalidate_org_data(str(org.id))
        cache_service.invalidate_analytics()
        return org

    @staticmethod
    def switch_organization(user: User, organization_id: str) -> bool:
        membership = Membership.query.filter_by(
            user_id=user.id, organization_id=organization_id
        ).first()
        if not membership:
            raise PermissionError("You are not a member of this organization.")

        Membership.query.filter_by(user_id=user.id).update({"is_current": False})
        membership.is_current = True
        db.session.commit()
        cache_service.invalidate_org_data(organization_id)
        return True

    @staticmethod
    def get_members(organization_id: str) -> list[dict]:
        cached = cache.get("org", f"members:{organization_id}")
        if cached is not None:
            return cached
        memberships = Membership.query.filter_by(organization_id=organization_id).all()
        result = []
        for m in memberships:
            user = User.query.get(m.user_id)
            result.append({
                "id": m.id,
                "user_id": m.user_id,
                "name": user.name,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "role": m.role,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            })
        cache.set("org", f"members:{organization_id}", result, 300)
        return result

    @staticmethod
    def update_member_role(organization_id: str, user_id: str, new_role: str, actor: User) -> bool:
        org = Organization.query.get(organization_id)
        if not org:
            raise NotFoundError("Organization not found.")

        if org.owner_id != actor.id:
            raise PermissionError("Only the organization owner can change roles.")

        if new_role not in [r.value for r in Role]:
            raise ValidationError(f"Invalid role: {new_role}")

        membership = Membership.query.filter_by(
            user_id=user_id, organization_id=organization_id
        ).first()
        if not membership:
            raise NotFoundError("Member not found.")

        old_role = membership.role
        membership.role = new_role

        AuditLog(
            actor_id=actor.id,
            organization_id=organization_id,
            action="member.role_changed",
            resource_type="membership",
            resource_id=membership.id,
            metadata={"user_id": user_id, "old_role": old_role, "new_role": new_role},
        )

        db.session.commit()
        cache_service.invalidate_org_data(str(org.id))
        cache_service.invalidate_analytics()
        return True

    @staticmethod
    def remove_member(organization_id: str, user_id: str, actor: User) -> bool:
        org = Organization.query.get(organization_id)
        if not org:
            raise NotFoundError("Organization not found.")

        if org.owner_id != actor.id and actor.id != user_id:
            permission = PermissionError("Only the owner can remove members.")
            if org.owner_id != actor.id:
                raise permission

        if org.owner_id == user_id:
            raise ValidationError("Cannot remove the organization owner. Transfer ownership first.")

        membership = Membership.query.filter_by(
            user_id=user_id, organization_id=organization_id
        ).first()
        if not membership:
            raise NotFoundError("Member not found.")

        db.session.delete(membership)

        AuditLog(
            actor_id=actor.id,
            organization_id=organization_id,
            action="member.removed",
            resource_type="membership",
            resource_id=membership.id,
            metadata={"user_id": user_id},
        )

        db.session.commit()
        cache_service.invalidate_org_data(str(organization_id))
        cache_service.invalidate_analytics()
        return True

    @staticmethod
    def transfer_ownership(organization_id: str, new_owner_id: str, actor: User) -> bool:
        org = Organization.query.get(organization_id)
        if not org:
            raise NotFoundError("Organization not found.")

        if org.owner_id != actor.id:
            raise PermissionError("Only the owner can transfer ownership.")

        membership = Membership.query.filter_by(
            user_id=new_owner_id, organization_id=organization_id
        ).first()
        if not membership:
            raise NotFoundError("User is not a member of this organization.")

        # Transfer ownership
        old_owner_membership = Membership.query.filter_by(
            user_id=org.owner_id, organization_id=organization_id
        ).first()
        if old_owner_membership:
            old_owner_membership.role = Role.ADMIN.value

        org.owner_id = new_owner_id
        membership.role = Role.OWNER.value

        AuditLog(
            actor_id=actor.id,
            organization_id=organization_id,
            action="organization.ownership_transferred",
            resource_type="organization",
            resource_id=org.id,
            metadata={"new_owner_id": new_owner_id},
        )

        db.session.commit()
        cache_service.invalidate_org_data(str(organization_id))
        cache_service.invalidate_analytics()
        return True

    @staticmethod
    def invite_member(organization_id: str, email: str, role: str, invited_by: User) -> Invitation:
        org = Organization.query.get(organization_id)
        if not org:
            raise NotFoundError("Organization not found.")

        if org.member_count >= org.max_members:
            raise ValidationError("Organization has reached its member limit. Upgrade your plan.")

        # Check if user is already a member
        user = User.query.filter_by(email=email).first()
        if user and user.belongs_to(org):
            raise ValidationError("User is already a member of this organization.")

        # Check for existing pending invitation
        existing = Invitation.query.filter_by(
            organization_id=organization_id,
            email=email,
            revoked=False,
            accepted_at=None,
        ).filter(Invitation.expires_at > datetime.now(UTC)).first()
        if existing:
            raise ValidationError("An invitation has already been sent to this email.")

        invitation = Invitation(
            organization_id=organization_id,
            email=email,
            role=role,
            invited_by_id=invited_by.id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db.session.add(invitation)

        AuditLog(
            actor_id=invited_by.id,
            organization_id=organization_id,
            action="member.invited",
            resource_type="invitation",
            resource_id=invitation.id,
            metadata={"email": email, "role": role},
        )

        db.session.commit()

        # Send invitation email
        from app.services.email_service import EmailService
        invite_url = f"{db.session.info.get('app_url', '') or 'http://localhost:5000'}/org/invitations/{invitation.token}/accept"
        EmailService.send_invitation_email(email, invited_by.name, org.name, invite_url)

        return invitation

    @staticmethod
    def accept_invitation(token: str, user: User) -> Organization:
        invitation = Invitation.query.filter_by(token=token).first()
        if not invitation:
            raise NotFoundError("Invitation not found or invalid.")

        if not invitation.is_valid:
            raise ValidationError("Invitation has expired or been revoked.")

        if invitation.email != user.email:
            raise ValidationError("This invitation was sent to a different email address.")

        org = Organization.query.get(invitation.organization_id)
        if not org:
            raise NotFoundError("Organization not found.")

        if org.member_count >= org.max_members:
            raise ValidationError("Organization has reached its member limit.")

        invitation.accepted_at = datetime.now(UTC)

        Membership(
            user_id=user.id,
            organization_id=org.id,
            role=invitation.role,
            is_current=False,
        )

        AuditLog(
            actor_id=user.id,
            organization_id=org.id,
            action="member.invitation_accepted",
            resource_type="invitation",
            resource_id=invitation.id,
        )

        db.session.commit()
        cache_service.invalidate_org_data(str(org.id))
        cache_service.invalidate_analytics()
        return org

    @staticmethod
    def revoke_invitation(invitation_id: str, actor: User) -> bool:
        invitation = Invitation.query.get(invitation_id)
        if not invitation:
            raise NotFoundError("Invitation not found.")

        if invitation.organization.owner_id != actor.id:
            raise PermissionError("Only the organization owner can revoke invitations.")

        invitation.revoked = True
        db.session.commit()
        cache_service.invalidate_org_data(str(invitation.organization_id))
        return True

    @staticmethod
    def _generate_slug(name: str) -> str:
        slug = name.lower().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        slug = slug[:50]

        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while Organization.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug
