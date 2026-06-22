from flask import session
from flask_login import login_user

from app.core.models import User
from app.services.audit_service import AuditService


class ImpersonationService:
    SESSION_ORIGINAL_USER = "_impersonator_id"
    SESSION_REASON = "_impersonator_reason"

    @staticmethod
    def start_impersonation(admin_user: User, target_user: User, reason: str) -> bool:
        if not admin_user.is_admin:
            return False
        if target_user.is_admin and target_user.id != admin_user.id:
            return False

        session[ImpersonationService.SESSION_ORIGINAL_USER] = admin_user.id
        session[ImpersonationService.SESSION_REASON] = reason

        AuditService.log(
            actor_id=admin_user.id,
            action="admin.impersonation_started",
            resource_type="user",
            resource_id=target_user.id,
            metadata={"impersonated_email": target_user.email, "reason": reason},
        )

        login_user(target_user)
        return True

    @staticmethod
    def stop_impersonation() -> bool:
        original_user_id = session.pop(ImpersonationService.SESSION_ORIGINAL_USER, None)
        reason = session.pop(ImpersonationService.SESSION_REASON, None)
        if not original_user_id:
            return False

        admin = User.query.get(original_user_id)
        if admin:
            AuditService.log(
                actor_id=admin.id,
                action="admin.impersonation_stopped",
                resource_type="user",
                metadata={"reason": reason},
            )
            login_user(admin)
        return True

    @staticmethod
    def is_impersonating() -> bool:
        return ImpersonationService.SESSION_ORIGINAL_USER in session

    @staticmethod
    def get_impersonator_id() -> str:
        return session.get(ImpersonationService.SESSION_ORIGINAL_USER)

    @staticmethod
    def get_impersonation_reason() -> str:
        return session.get(ImpersonationService.SESSION_REASON, "")
