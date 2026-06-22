from flask import Blueprint, jsonify, request, g
from flask_login import login_required, current_user
from werkzeug.exceptions import HTTPException

from app.core.extensions import db
from app.core.models import User, Organization, Membership, APIKey, AuditLog
from app.services.base import ServiceError, NotFoundError, PermissionError, ValidationError
from app.services.decorators import require_admin

api_bp = Blueprint("api", __name__)


def api_auth_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"error": "API key required"}), 401

        from werkzeug.security import check_password_hash
        key_obj = APIKey.query.filter_by(is_active=True).first()
        if not key_obj or not check_password_hash(key_obj.key_hash, api_key):
            return jsonify({"error": "Invalid API key"}), 401

        if key_obj.is_expired:
            return jsonify({"error": "API key has expired"}), 401

        key_obj.usage_count = (key_obj.usage_count or 0) + 1
        from datetime import datetime, timezone
        key_obj.last_used_at = datetime.now(timezone.utc)
        db.session.commit()

        g.api_key = key_obj
        g.api_user = key_obj.user
        return f(*args, **kwargs)

    return decorated


@api_bp.route("/")
def index():
    return jsonify({
        "name": "SaaSForge API",
        "version": "v1",
        "status": "operational",
    })


@api_bp.route("/me")
@api_auth_required
def me():
    user = g.api_user
    return jsonify({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    })


@api_bp.route("/organizations")
@api_auth_required
def list_organizations():
    user = g.api_user
    orgs = user.organizations
    return jsonify([{
        "id": o.id,
        "name": o.name,
        "slug": o.slug,
        "plan": o.subscription_tier,
        "member_count": o.member_count,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    } for o in orgs])


@api_bp.route("/organizations/<org_id>")
@api_auth_required
def get_organization(org_id):
    user = g.api_user
    org = Organization.query.get(org_id)
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    if not user.belongs_to(org):
        return jsonify({"error": "Access denied"}), 403

    subscription = org.active_subscription
    return jsonify({
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "plan": org.subscription_tier,
        "subscription_status": subscription.status if subscription else None,
        "member_count": org.member_count,
        "max_members": org.max_members,
        "created_at": org.created_at.isoformat() if org.created_at else None,
    })


@api_bp.route("/organizations/<org_id>/members")
@api_auth_required
def list_members(org_id):
    user = g.api_user
    org = Organization.query.get(org_id)
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    if not user.belongs_to(org):
        return jsonify({"error": "Access denied"}), 403

    from app.services.org_service import OrganizationService
    members = OrganizationService.get_members(org_id)
    return jsonify(members)


# API Key management endpoints
@api_bp.route("/keys", methods=["GET"])
@login_required
def list_api_keys():
    keys = APIKey.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        "id": k.id,
        "name": k.name,
        "key_prefix": k.key_prefix,
        "key_type": k.key_type,
        "is_active": k.is_active,
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        "usage_count": k.usage_count,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    } for k in keys])


@api_bp.route("/keys", methods=["POST"])
@login_required
def create_api_key():
    import secrets
    from werkzeug.security import generate_password_hash

    name = request.form.get("name", "Default Key").strip()
    key_type = request.form.get("key_type", "test")

    raw_key = f"sf_{secrets.token_hex(24)}"
    key_obj = APIKey(
        user_id=current_user.id,
        organization_id=current_user.current_organization.id if current_user.current_organization else None,
        name=name,
        key_prefix=raw_key[:8],
        key_hash=generate_password_hash(raw_key),
        key_type=key_type,
    )
    db.session.add(key_obj)
    db.session.commit()

    return jsonify({
        "id": key_obj.id,
        "name": key_obj.name,
        "key": raw_key,
        "key_prefix": key_obj.key_prefix,
        "key_type": key_obj.key_type,
        "warning": "Store this key securely. It will not be shown again.",
    }), 201


@api_bp.route("/keys/<key_id>/revoke", methods=["POST"])
@login_required
def revoke_api_key(key_id):
    key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    if not key:
        return jsonify({"error": "API key not found"}), 404

    key.is_active = False
    db.session.commit()
    return jsonify({"status": "revoked"})


# Admin-only API stats
@api_bp.route("/admin/stats")
@login_required
@require_admin
def admin_stats():
    from app.services.analytics_service import AnalyticsService
    stats = AnalyticsService.get_dashboard_stats()
    return jsonify(stats)


# Error handlers for API
@api_bp.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request", "message": str(e)}), 400


@api_bp.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "Unauthorized"}), 401


@api_bp.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Forbidden"}), 403


@api_bp.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@api_bp.errorhandler(429)
def too_many_requests(e):
    return jsonify({"error": "Rate limit exceeded"}), 429


@api_bp.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500
