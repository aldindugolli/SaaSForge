import re
import secrets
from datetime import UTC, datetime

from flask import current_app
from itsdangerous import SignatureExpired, URLSafeTimedSerializer

from app.core.extensions import cache_service, db
from app.core.models import AuditLog, Membership, Organization, PlanType, Role, User
from app.services.base import NotFoundError, PermissionError, ValidationError
from app.services.notification_service import NotificationService


class AuthService:
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#]).{8,}$")

    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        if len(password) < AuthService.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {AuthService.PASSWORD_MIN_LENGTH} characters long."
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter."
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter."
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number."
        if not re.search(r"[@$!%*?&#]", password):
            return False, "Password must contain at least one special character (@$!%*?&#)."
        return True, ""

    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            return False, "Invalid email address."
        return True, ""

    @staticmethod
    def register(email: str, password: str, name: str) -> User:
        is_valid, error = AuthService.validate_email(email)
        if not is_valid:
            raise ValidationError(error)

        if User.query.filter_by(email=email).first():
            raise ValidationError("An account with this email already exists.")

        is_valid, error = AuthService.validate_password(password)
        if not is_valid:
            raise ValidationError(error)

        user = User(email=email, name=name)
        user.set_password(password)

        # Generate email verification token
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        user.email_verify_token = serializer.dumps(email)
        user.email_verify_sent_at = datetime.now(UTC)

        db.session.add(user)
        db.session.flush()

        # Create personal organization
        org = Organization(
            name=f"{name}'s Workspace",
            slug=f"personal-{secrets.token_hex(4)}",
            owner_id=user.id,
            is_personal=True,
            subscription_tier=PlanType.FREE.value,
            max_members=1,
        )
        db.session.add(org)
        db.session.flush()

        # Create membership
        Membership(
            user_id=user.id,
            organization_id=org.id,
            role=Role.OWNER.value,
            is_current=True,
        )

        # Log audit
        AuditLog(
            actor_id=user.id,
            action="user.registered",
            resource_type="user",
            resource_id=user.id,
            metadata={"email": email},
        )

        db.session.commit()
        cache_service.invalidate_analytics()

        # Send welcome email (async)
        AuthService._send_verification_email(user)

        NotificationService.create_notification(
            user_id=user.id,
            title="Welcome to SaaSForge!",
            message="Your account has been created successfully. Please verify your email to get started.",
            type="success",
        )

        return user

    @staticmethod
    def login(email: str, password: str, ip_address: str = None, user_agent: str = None) -> User:
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValidationError("Invalid email or password.")

        if not user.check_password(password):
            raise ValidationError("Invalid email or password.")

        if not user.is_active:
            raise PermissionError("This account has been deactivated.")

        if user.is_banned:
            raise PermissionError(f"This account has been banned. Reason: {user.ban_reason or 'No reason provided.'}")

        # Update login tracking
        user.last_login_at = datetime.now(UTC)
        user.last_login_ip = ip_address
        user.last_user_agent = user_agent
        user.login_count = (user.login_count or 0) + 1

        AuditLog(
            actor_id=user.id,
            action="user.login",
            resource_type="user",
            resource_id=user.id,
            metadata={"ip_address": ip_address},
        )

        db.session.commit()

        from app.services.session_service import SessionService
        try:
            SessionService.create_session(str(user.id))
        except Exception:
            pass

        return user

    @staticmethod
    def send_password_reset(email: str) -> bool:
        user = User.query.filter_by(email=email).first()
        if not user:
            return False  # Don't reveal if email exists

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = serializer.dumps(email, salt="password-reset")
        user.password_reset_token = token
        user.password_reset_sent_at = datetime.now(UTC)
        db.session.commit()

        # In production, send email via background job
        # reset_url = f"{current_app.config['APP_URL']}/auth/reset-password/{token}"
        # send_email(to=email, subject="Password Reset", body=render_template("emails/password_reset.html", url=reset_url))

        return True

    @staticmethod
    def reset_password(token: str, new_password: str) -> bool:
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            email = serializer.loads(token, salt="password-reset", max_age=3600)
        except SignatureExpired:
            raise ValidationError("Reset link has expired. Please request a new one.")
        except Exception:
            raise ValidationError("Invalid reset link.")

        user = User.query.filter_by(email=email).first()
        if not user:
            raise NotFoundError("User not found.")

        if user.password_reset_token != token:
            raise ValidationError("Invalid reset link.")

        is_valid, error = AuthService.validate_password(new_password)
        if not is_valid:
            raise ValidationError(error)

        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_sent_at = None

        AuditLog(
            actor_id=user.id,
            action="user.password_reset",
            resource_type="user",
            resource_id=user.id,
        )

        db.session.commit()
        return True

    @staticmethod
    def verify_email(token: str) -> bool:
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            email = serializer.loads(token, max_age=86400)  # 24 hours
        except SignatureExpired:
            raise ValidationError("Verification link has expired.")
        except Exception:
            raise ValidationError("Invalid verification link.")

        user = User.query.filter_by(email=email).first()
        if not user:
            raise NotFoundError("User not found.")

        if user.email_verified:
            return True

        user.email_verified = True
        user.email_verify_token = None
        user.email_verify_sent_at = None

        AuditLog(
            actor_id=user.id,
            action="user.email_verified",
            resource_type="user",
            resource_id=user.id,
        )

        db.session.commit()
        return True

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> bool:
        if not user.check_password(current_password):
            raise ValidationError("Current password is incorrect.")

        is_valid, error = AuthService.validate_password(new_password)
        if not is_valid:
            raise ValidationError(error)

        user.set_password(new_password)

        AuditLog(
            actor_id=user.id,
            action="user.password_changed",
            resource_type="user",
            resource_id=user.id,
        )

        db.session.commit()
        return True

    @staticmethod
    def _send_verification_email(user: User):
        """Send verification email (placeholder for actual email sending)."""
        from app.services.email_service import EmailService
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = serializer.dumps(user.email)
        verify_url = f"{current_app.config['APP_URL']}/auth/verify-email/{token}"
        EmailService.send_verification_email(user.email, verify_url)
