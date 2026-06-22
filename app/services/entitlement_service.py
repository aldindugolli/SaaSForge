from flask import abort, current_app
from flask_login import current_user

from app.core.models import Organization


class EntitlementService:
    """Check feature entitlements based on the organization's subscription plan."""

    @staticmethod
    def get_plan_config(org: Organization | None = None) -> dict:
        plan_name = (org or current_user.current_organization).subscription_tier if (org or current_user.current_organization) else "free"
        return current_app.config["STRIPE_PLANS"].get(plan_name, current_app.config["STRIPE_PLANS"]["free"])

    @staticmethod
    def has_feature(feature: str, org: Organization | None = None) -> bool:
        """Check if the org has a specific entitlement feature."""
        plan = EntitlementService.get_plan_config(org)
        return plan.get("entitlements", {}).get(feature, False)

    @staticmethod
    def max_members(org: Organization | None = None) -> int:
        return EntitlementService.get_plan_config(org).get("max_members", 1)

    @staticmethod
    def max_projects(org: Organization | None = None) -> int:
        return EntitlementService.get_plan_config(org).get("max_projects", 1)

    @staticmethod
    def can_add_member(org: Organization | None = None) -> bool:
        from app.core.models import Membership
        org = org or current_user.current_organization
        if not org:
            return False
        current_count = Membership.query.filter_by(organization_id=org.id).count()
        return current_count < EntitlementService.max_members(org)


def entitlement_required(feature: str):
    """Decorator that returns 403 if the user's current org lacks a feature."""
    from functools import wraps

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            org = current_user.current_organization
            if not org or not EntitlementService.has_feature(feature, org):
                abort(403, description=f"Your plan does not include '{feature}'. Upgrade to enable it.")
            return f(*args, **kwargs)
        return wrapper
    return decorator
