import uuid
import enum
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.core.extensions import db, login_manager


def gen_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    UNPAID = "unpaid"


class PlanType(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class APIKeyType(str, enum.Enum):
    TEST = "test"
    LIVE = "live"


class NotificationType(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(512), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    company = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    website = db.Column(db.String(512), nullable=True)

    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verify_token = db.Column(db.String(255), nullable=True)
    email_verify_sent_at = db.Column(db.DateTime, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    banned_at = db.Column(db.DateTime, nullable=True)
    ban_reason = db.Column(db.Text, nullable=True)

    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    last_user_agent = db.Column(db.Text, nullable=True)
    login_count = db.Column(db.Integer, default=0, nullable=False)

    google_id = db.Column(db.String(255), unique=True, nullable=True)

    password_reset_token = db.Column(db.String(255), nullable=True)
    password_reset_sent_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    memberships = db.relationship("Membership", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    owned_organizations = db.relationship("Organization", back_populates="owner", lazy="dynamic", foreign_keys="Organization.owner_id")
    notifications = db.relationship("Notification", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    api_keys = db.relationship("APIKey", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", back_populates="actor", lazy="dynamic", foreign_keys="AuditLog.actor_id")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def current_organization(self):
        membership = self.memberships.filter_by(is_current=True).first()
        if membership:
            return membership.organization
        # Fall back to first membership
        membership = self.memberships.first()
        return membership.organization if membership else None

    @property
    def organizations(self):
        return Organization.query.join(Membership).filter(Membership.user_id == self.id).all()

    def has_role(self, organization, role):
        membership = Membership.query.filter_by(
            user_id=self.id, organization_id=organization.id
        ).first()
        if not membership:
            return False
        roles = list(Role)
        return roles.index(membership.role) <= roles.index(role)

    def belongs_to(self, organization):
        return Membership.query.filter_by(
            user_id=self.id, organization_id=organization.id
        ).first() is not None

    def __repr__(self):
        return f"<User {self.email}>"


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    logo_url = db.Column(db.String(512), nullable=True)
    description = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(512), nullable=True)
    timezone = db.Column(db.String(50), default="UTC")

    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    owner = db.relationship("User", back_populates="owned_organizations", foreign_keys=[owner_id])

    subscription_tier = db.Column(db.String(20), nullable=False, default=PlanType.FREE.value)
    subscription_status = db.Column(db.String(20), nullable=True)
    trial_ends_at = db.Column(db.DateTime, nullable=True)

    max_members = db.Column(db.Integer, default=1, nullable=False)
    is_personal = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    memberships = db.relationship("Membership", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    subscriptions = db.relationship("Subscription", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    invitations = db.relationship("Invitation", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    feature_flags = db.relationship("FeatureFlag", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def members(self):
        return User.query.join(Membership).filter(Membership.organization_id == self.id).all()

    @property
    def member_count(self):
        return self.memberships.count()

    @property
    def active_subscription(self):
        return self.subscriptions.filter(
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE.value,
                SubscriptionStatus.TRIALING.value,
                SubscriptionStatus.PAST_DUE.value,
            ])
        ).first()

    @property
    def is_trialing(self):
        if self.trial_ends_at and self.trial_ends_at > utcnow():
            return True
        return False

    @property
    def plan(self):
        from app.core.config import Config
        return Config.STRIPE_PLANS.get(self.subscription_tier, Config.STRIPE_PLANS["free"])

    def __repr__(self):
        return f"<Organization {self.name}>"


class Membership(db.Model):
    __tablename__ = "memberships"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.MEMBER.value)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    joined_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="memberships")
    organization = db.relationship("Organization", back_populates="memberships")

    __table_args__ = (
        db.UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
    )

    def __repr__(self):
        return f"<Membership {self.user.email} @ {self.organization.name} ({self.role})>"


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=True)
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    stripe_price_id = db.Column(db.String(255), nullable=True)
    plan = db.Column(db.String(20), nullable=False, default=PlanType.FREE.value)
    status = db.Column(db.String(20), nullable=False, default=SubscriptionStatus.ACTIVE.value)
    quantity = db.Column(db.Integer, default=1)
    trial_end = db.Column(db.DateTime, nullable=True)
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    canceled_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = db.relationship("Organization", back_populates="subscriptions")
    invoices = db.relationship("Invoice", back_populates="subscription", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_active(self):
        return self.status in [
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.TRIALING.value,
        ]

    def __repr__(self):
        return f"<Subscription {self.plan} ({self.status})>"


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    subscription_id = db.Column(db.String(36), db.ForeignKey("subscriptions.id"), nullable=True)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    stripe_invoice_id = db.Column(db.String(255), unique=True, nullable=True)
    amount_due = db.Column(db.Integer, nullable=False)
    amount_paid = db.Column(db.Integer, nullable=True)
    currency = db.Column(db.String(3), default="usd")
    status = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    pdf_url = db.Column(db.String(512), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    subscription = db.relationship("Subscription", back_populates="invoices")
    organization = db.relationship("Organization")

    def __repr__(self):
        return f"<Invoice {self.id} ({self.status})>"


class PaymentEvent(db.Model):
    __tablename__ = "payment_events"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=True)
    stripe_event_id = db.Column(db.String(255), unique=True, nullable=True)
    type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="processed")
    data = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def __repr__(self):
        return f"<PaymentEvent {self.type}>"


class Invitation(db.Model):
    __tablename__ = "invitations"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, default=gen_uuid)
    role = db.Column(db.String(20), nullable=False, default=Role.MEMBER.value)
    invited_by_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    organization = db.relationship("Organization", back_populates="invitations")
    invited_by = db.relationship("User", foreign_keys=[invited_by_id])

    @property
    def is_expired(self):
        return utcnow() > self.expires_at

    @property
    def is_valid(self):
        return not self.revoked and not self.is_expired and self.accepted_at is None

    def __repr__(self):
        return f"<Invitation {self.email} -> {self.organization.name}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False, default=NotificationType.INFO.value)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(512), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.title}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.String(36), nullable=True)
    log_metadata = db.Column("metadata", db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    actor = db.relationship("User", back_populates="audit_logs", foreign_keys=[actor_id])

    __table_args__ = (
        db.Index("idx_audit_logs_created_at", "created_at"),
        db.Index("idx_audit_logs_action", "action"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.actor_id}>"


class APIKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    key_prefix = db.Column(db.String(8), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False)
    key_type = db.Column(db.String(20), nullable=False, default=APIKeyType.TEST.value)
    permissions = db.Column(db.JSON, nullable=True, default=list)
    last_used_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="api_keys")
    organization = db.relationship("Organization")

    @property
    def is_expired(self):
        if self.expires_at and utcnow() > self.expires_at:
            return True
        return False

    def __repr__(self):
        return f"<APIKey {self.name} ({self.key_prefix}...)>"


class FeatureFlag(db.Model):
    __tablename__ = "feature_flags"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    scope = db.Column(db.String(20), nullable=False, default="global")
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    organization = db.relationship("Organization", back_populates="feature_flags")

    __table_args__ = (
        db.UniqueConstraint("key", "scope", "organization_id", name="uq_feature_flag_scope"),
    )

    def __repr__(self):
        return f"<FeatureFlag {self.key} ({'on' if self.enabled else 'off'})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)
