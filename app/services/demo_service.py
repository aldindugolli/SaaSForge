"""Demo environment management: safety guards, seeding, and reset."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app, g, request, session
from flask_login import current_user

from app.core.extensions import db
from app.core.models import (
    FeatureFlag,
    Invoice,
    Membership,
    Notification,
    Organization,
    Subscription,
    SubscriptionStatus,
    User,
)
from app.services.auth_service import AuthService
from app.services.org_service import OrganizationService

logger = logging.getLogger(__name__)

DEMO_ACCOUNTS = [
    {
        "email": "admin@saasforge.com",
        "password": "Admin123!",
        "name": "Admin User",
        "is_admin": True,
        "org_name": "SaaSForge Admin",
        "org_slug": "saasforge-admin",
        "tier": "business",
    },
    {
        "email": "demo@saasforge.com",
        "password": "Demo123!",
        "name": "Demo User",
        "is_admin": False,
        "org_name": "Demo Company",
        "org_slug": "demo-company",
        "tier": "pro",
    },
    {
        "email": "manager@saasforge.com",
        "password": "Manager123!",
        "name": "Team Manager",
        "is_admin": False,
        "org_name": "Demo Company",
        "org_slug": "demo-company",
        "tier": "pro",
    },
    {
        "email": "member@saasforge.com",
        "password": "Member123!",
        "name": "Team Member",
        "is_admin": False,
        "org_name": "Demo Company",
        "org_slug": "demo-company",
        "tier": "pro",
    },
]


def is_demo_mode() -> bool:
    """Check if the app is running in demo mode."""
    return current_app.config.get("DEMO_MODE", False)


def is_demo_user(user: User | None = None) -> bool:
    """Check if the current user is a demo account."""
    if user is None:
        user = current_user
    if not user or not user.is_authenticated:
        return False
    demo_emails = {a["email"] for a in DEMO_ACCOUNTS}
    return user.email in demo_emails


def is_destructive_action() -> bool:
    """Check if the current request is a destructive action."""
    method = request.method.upper()
    path = request.path

    destructive_patterns = [
        "/admin/users/",
        "/admin/organizations/",
        "/org/",
        "/billing/",
    ]
    destructive_methods = {"POST", "PUT", "PATCH", "DELETE"}

    if method not in destructive_methods:
        return False

    if method == "POST":
        safe_post_paths = [
            "/auth/login",
            "/auth/register",
            "/auth/forgot-password",
            "/auth/reset-password",
            "/auth/logout",
            "/settings",
            "/2fa/verify",
            "/2fa/disable",
            "/impersonate/stop",
            "/sessions/revoke-all",
            "/billing/create-checkout-session",
            "/billing/customer-portal",
            "/security/",
            "/webhooks/",
        ]
        for safe in safe_post_paths:
            if path.startswith(safe):
                return False

    for pattern in destructive_patterns:
        if path.startswith(pattern):
            return True

    return False


class DemoMiddleware:
    """Protect demo environment from destructive actions."""

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app) -> None:
        app.before_request(self._before_request)

    def _before_request(self):
        if not is_demo_mode():
            return
        if not current_user.is_authenticated:
            return
        if current_user.is_admin:
            return
        if request.path.startswith("/auth/logout"):
            return
        if is_destructive_action():
            from flask import flash, redirect, request as req
            flash("This action is disabled in the demo environment.", "warning")
            return redirect(req.referrer or "/dashboard")


@staticmethod
def get_allowed_actions() -> list[str]:
    """Return list of actions allowed in demo mode."""
    return [
        "View dashboards and analytics",
        "Browse admin pages (read-only)",
        "Create/view API keys",
        "Explore webhook settings",
        "Toggle dark mode",
        "Update profile name/bio",
        "Change password for demo accounts",
    ]


def create_seed_data() -> list[dict]:
    """Create comprehensive seed data for the demo environment."""
    created: list[dict] = []

    existing_users = set()
    for u in User.query.all():
        existing_users.add(u.email)

    orgs: dict[str, Organization] = {}

    for account in DEMO_ACCOUNTS:
        email = account["email"]
        if email in existing_users:
            user = User.query.filter_by(email=email).first()
            if not user:
                continue
        else:
            user = User(
                email=email,
                name=account["name"],
                email_verified=True,
                is_admin=account.get("is_admin", False),
                is_active=True,
            )
            user.set_password(account["password"])
            db.session.add(user)
            db.session.flush()
            existing_users.add(email)
            created.append({"type": "user", "email": email})

        slug = account["org_slug"]
        if slug not in orgs:
            existing_org = Organization.query.filter_by(slug=slug).first()
            if existing_org:
                orgs[slug] = existing_org
                created.append({"type": "org", "slug": slug, "status": "existing"})
            else:
                org = Organization(
                    name=account["org_name"],
                    slug=slug,
                    owner_id=user.id,
                    subscription_tier=account["tier"],
                    max_members=100,
                )
                db.session.add(org)
                db.session.flush()
                orgs[slug] = org
                created.append({"type": "org", "slug": slug, "status": "created"})

        org = orgs[slug]
        existing_membership = Membership.query.filter_by(
            user_id=user.id, organization_id=org.id
        ).first()
        if not existing_membership:
            from app.core.models import Role
            role = Role.OWNER.value if org.owner_id == user.id else Role.MEMBER.value
            if account.get("email") == "manager@saasforge.com":
                role = Role.ADMIN.value
            db.session.add(Membership(
                user_id=user.id, organization_id=org.id, role=role, is_current=True
            ))

    for slug, org in orgs.items():
        existing_sub = Subscription.query.filter_by(
            organization_id=org.id, status=SubscriptionStatus.ACTIVE.value
        ).first()
        if not existing_sub:
            sub = Subscription(
                organization_id=org.id,
                plan=org.subscription_tier,
                status=SubscriptionStatus.ACTIVE.value,
                current_period_start=datetime.now(UTC),
                current_period_end=datetime.now(UTC) + timedelta(days=30),
            )
            db.session.add(sub)
            created.append({"type": "subscription", "org": slug})

    org_admin = orgs.get("saasforge-admin")
    if org_admin:
        invoices = Invoice.query.filter_by(
            organization_id=org_admin.id
        ).count()
        if invoices == 0:
            for i in range(3):
                inv = Invoice(
                    organization_id=org_admin.id,
                    amount_due=9900 + i * 1000,
                    amount_paid=9900 + i * 1000,
                    currency="usd",
                    status="paid",
                    stripe_invoice_id=f"demo_inv_{i}",
                    paid_at=datetime.now(UTC) - timedelta(days=90 - i * 30),
                )
                db.session.add(inv)

    existing_flags = FeatureFlag.query.count()
    if existing_flags == 0:
        flags = [
            FeatureFlag(name="New Dashboard", key="new_dashboard", enabled=True, scope="global"),
            FeatureFlag(name="Beta API", key="beta_api", enabled=False, scope="global"),
            FeatureFlag(name="Dark Mode", key="dark_mode", enabled=True, scope="global"),
            FeatureFlag(name="Two-Factor Auth", key="two_factor_auth", enabled=True, scope="global"),
            FeatureFlag(name="Webhook System", key="webhooks", enabled=True, scope="global"),
        ]
        db.session.add_all(flags)
        created.append({"type": "feature_flags", "count": len(flags)})

    user_count = User.query.count()
    if user_count <= len(DEMO_ACCOUNTS):
        for i in range(5):
            idx = i + 1
            extra_email = f"extra-user{idx}@example.com"
            if not User.query.filter_by(email=extra_email).first():
                extra_user = User(
                    email=extra_email,
                    name=f"Extra User {idx}",
                    email_verified=True,
                    is_active=True,
                )
                extra_user.set_password("Demo123!")
                db.session.add(extra_user)
                if org_admin:
                    db.session.add(Membership(
                        user_id=extra_user.id,
                        organization_id=org_admin.id,
                        role="member",
                        is_current=False,
                    ))
                created.append({"type": "extra_user", "email": extra_email})

    db.session.commit()
    return created


def reset_demo_data() -> dict[str, Any]:
    """Reset all demo data to a clean state."""
    demo_emails = {a["email"] for a in DEMO_ACCOUNTS}

    users = User.query.filter(User.email.in_(demo_emails)).all()
    user_ids = [u.id for u in users]

    orgs = Organization.query.filter(
        Organization.owner_id.in_(user_ids)
    ).all()
    org_ids = [o.id for o in orgs]

    Subscription.query.filter(
        Subscription.organization_id.in_(org_ids)
    ).delete()
    Invoice.query.filter(
        Invoice.organization_id.in_(org_ids)
    ).delete()
    Notification.query.filter(
        Notification.user_id.in_(user_ids)
    ).delete()
    Membership.query.filter(
        Membership.organization_id.in_(org_ids)
    ).delete()
    Organization.query.filter(Organization.id.in_(org_ids)).delete()

    extra_emails = set()
    for u in User.query.all():
        if u.email not in demo_emails:
            extra_emails.add(u.email)
    if extra_emails:
        extra_users = User.query.filter(User.email.in_(extra_emails)).all()
        for u in extra_users:
            Membership.query.filter_by(user_id=u.id).delete()
            Notification.query.filter_by(user_id=u.id).delete()
        User.query.filter(User.email.in_(extra_emails)).delete()

    db.session.commit()

    created = create_seed_data()
    return {"users": len(DEMO_ACCOUNTS), "orgs": len(org_ids), "created": created}
