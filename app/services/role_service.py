from flask import abort
from flask_login import current_user

from app.core.models import Membership, Role


class Permission:
    """Granular permission flags per role."""

    VIEW_BILLING = "view_billing"
    MANAGE_BILLING = "manage_billing"
    INVITE_MEMBERS = "invite_members"
    REMOVE_MEMBERS = "remove_members"
    MANAGE_ROLES = "manage_roles"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_ACTIVITY = "view_activity"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_API_KEYS = "manage_api_keys"
    DELETE_ORGANIZATION = "delete_organization"
    EXPORT_DATA = "export_data"


ROLE_PERMISSIONS = {
    Role.OWNER.value: [
        Permission.VIEW_BILLING,
        Permission.MANAGE_BILLING,
        Permission.INVITE_MEMBERS,
        Permission.REMOVE_MEMBERS,
        Permission.MANAGE_ROLES,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_ACTIVITY,
        Permission.MANAGE_SETTINGS,
        Permission.MANAGE_API_KEYS,
        Permission.DELETE_ORGANIZATION,
        Permission.EXPORT_DATA,
    ],
    Role.ADMIN.value: [
        Permission.VIEW_BILLING,
        Permission.INVITE_MEMBERS,
        Permission.REMOVE_MEMBERS,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_ACTIVITY,
        Permission.MANAGE_SETTINGS,
        Permission.MANAGE_API_KEYS,
        Permission.EXPORT_DATA,
    ],
    Role.MEMBER.value: [
        Permission.VIEW_BILLING,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_ACTIVITY,
    ],
}


class RoleService:
    @staticmethod
    def get_user_role(org_id: str) -> str | None:
        membership = Membership.query.filter_by(
            user_id=current_user.id, organization_id=org_id
        ).first()
        return membership.role if membership else None

    @staticmethod
    def has_permission(org_id: str, permission: str) -> bool:
        role = RoleService.get_user_role(org_id)
        if not role:
            return False
        return permission in ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    def get_permissions(org_id: str) -> list[str]:
        role = RoleService.get_user_role(org_id)
        return ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    def change_role(org_id: str, target_user_id: str, new_role: str) -> bool:
        actor_role = RoleService.get_user_role(org_id)
        actor_perms = ROLE_PERMISSIONS.get(actor_role, [])
        if Permission.MANAGE_ROLES not in actor_perms:
            return False
        membership = Membership.query.filter_by(
            user_id=target_user_id, organization_id=org_id
        ).first()
        if not membership:
            return False
        if actor_role == Role.ADMIN.value and new_role == Role.OWNER.value:
            return False
        membership.role = new_role
        return True


def require_permission(permission: str):
    """Decorator that checks permission against the org from the route param."""
    from functools import wraps

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            org_id = kwargs.get("org_id")
            if not org_id:
                abort(400)
            if not RoleService.has_permission(org_id, permission):
                abort(403, description=f"Missing permission: {permission}")
            return f(*args, **kwargs)
        return wrapper
    return decorator
