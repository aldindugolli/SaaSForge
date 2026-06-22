from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.core.models import APIKey, AuditLog, UserSession

security_bp = Blueprint("security", __name__, url_prefix="/security")


@security_bp.route("/")
@login_required
def index():
    recent_logins = AuditLog.query.filter_by(
        actor_id=current_user.id, action="user.login"
    ).order_by(AuditLog.created_at.desc()).limit(10).all()

    failed_logins = AuditLog.query.filter_by(
        actor_id=current_user.id, action="user.login_failed"
    ).order_by(AuditLog.created_at.desc()).limit(10).all()

    active_sessions = UserSession.query.filter_by(
        user_id=current_user.id, is_current=False
    ).order_by(UserSession.last_activity_at.desc()).limit(10).all()

    api_keys = APIKey.query.filter_by(
        user_id=current_user.id, is_active=True
    ).all()

    recent_audit = AuditLog.query.filter_by(
        actor_id=current_user.id
    ).order_by(AuditLog.created_at.desc()).limit(20).all()

    return render_template(
        "security/index.html",
        recent_logins=recent_logins,
        failed_logins=failed_logins,
        active_sessions=active_sessions,
        api_keys=api_keys,
        recent_audit=recent_audit,
    )
