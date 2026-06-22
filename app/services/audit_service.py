from typing import Optional, List
from datetime import datetime, timezone
from functools import wraps

from flask import request
from flask_login import current_user
from app.core.extensions import db
from app.core.models import AuditLog


class AuditService:
    @staticmethod
    def log(
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        actor_id: Optional[str] = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            actor_id=actor_id or (current_user.id if current_user.is_authenticated else None),
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            log_metadata=metadata,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request and request.user_agent else None,
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry

    @staticmethod
    def get_logs(
        organization_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        query = AuditLog.query
        if organization_id:
            query = query.filter_by(organization_id=organization_id)
        if actor_id:
            query = query.filter_by(actor_id=actor_id)
        if action:
            query = query.filter(AuditLog.action.contains(action))
        if resource_type:
            query = query.filter_by(resource_type=resource_type)
        return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def log_user_action(user_id: str, action: str, metadata: Optional[dict] = None):
        return AuditService.log(
            action=action,
            resource_type="user",
            resource_id=user_id,
            log_metadata=metadata,
            actor_id=user_id,
        )


def audit_log(action: str, resource_type: Optional[str] = None):
    """Decorator for auditing route actions."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            AuditService.log(
                action=action,
                resource_type=resource_type,
                metadata=request.view_args if request.view_args else None,
            )
            return result
        return wrapper
    return decorator
