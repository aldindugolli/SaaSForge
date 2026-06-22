from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from app.core.extensions import db
from app.core.models import User, Organization, Subscription, Invoice, AuditLog
from app.services.analytics_service import AnalyticsService
from app.services.audit_service import AuditService
from app.services.base import ServiceError, NotFoundError
from app.services.decorators import require_admin

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
@login_required
@require_admin
def before_request():
    pass


@admin_bp.route("/")
def index():
    stats = AnalyticsService.get_dashboard_stats()
    user_growth = AnalyticsService.get_user_growth(30)
    revenue = AnalyticsService.get_revenue_growth(90)
    subscription_dist = AnalyticsService.get_subscription_distribution()

    return render_template(
        "admin/index.html",
        stats=stats,
        user_growth=user_growth,
        revenue=revenue,
        subscription_dist=subscription_dist,
    )


@admin_bp.route("/users")
def users():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    per_page = 25

    query = User.query
    if search:
        query = query.filter(
            User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%")
        )

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "admin/users.html",
        users=users,
        search=search,
    )


@admin_bp.route("/users/<user_id>")
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    audit_logs = AuditLog.query.filter_by(actor_id=user_id).order_by(AuditLog.created_at.desc()).limit(50).all()
    return render_template("admin/user_detail.html", user=user, audit_logs=audit_logs)


@admin_bp.route("/users/<user_id>/ban", methods=["POST"])
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    reason = request.form.get("reason", "").strip()

    if user.is_admin:
        flash("Cannot ban admin users.", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    user.is_banned = True
    user.is_active = False
    user.ban_reason = reason or "No reason provided."

    AuditService.log(
        action="user.banned",
        resource_type="user",
        resource_id=user.id,
        metadata={"banned_by": current_user.id, "reason": reason},
    )

    db.session.commit()
    flash(f"User {user.email} has been banned.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/users/<user_id>/unban", methods=["POST"])
def unban_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_banned = False
    user.is_active = True
    user.ban_reason = None

    AuditService.log(
        action="user.unbanned",
        resource_type="user",
        resource_id=user.id,
    )

    db.session.commit()
    flash(f"User {user.email} has been unbanned.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/users/<user_id>/disable", methods=["POST"])
def disable_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active

    AuditService.log(
        action="user.disabled" if not user.is_active else "user.enabled",
        resource_type="user",
        resource_id=user.id,
    )

    db.session.commit()
    status = "disabled" if not user.is_active else "enabled"
    flash(f"User {user.email} has been {status}.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/organizations")
def organizations():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    per_page = 25

    query = Organization.query
    if search:
        query = query.filter(
            Organization.name.ilike(f"%{search}%") | Organization.slug.ilike(f"%{search}%")
        )

    orgs = query.order_by(Organization.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template("admin/organizations.html", orgs=orgs, search=search)


@admin_bp.route("/organizations/<org_id>")
def organization_detail(org_id):
    org = Organization.query.get_or_404(org_id)
    subscriptions = Subscription.query.filter_by(organization_id=org_id).order_by(Subscription.created_at.desc()).all()
    invoices = Invoice.query.filter_by(organization_id=org_id).order_by(Invoice.created_at.desc()).limit(20).all()
    audit_logs = AuditLog.query.filter_by(organization_id=org_id).order_by(AuditLog.created_at.desc()).limit(50).all()

    return render_template(
        "admin/org_detail.html",
        org=org,
        subscriptions=subscriptions,
        invoices=invoices,
        audit_logs=audit_logs,
    )


@admin_bp.route("/subscriptions")
def subscriptions():
    page = request.args.get("page", 1, type=int)
    per_page = 25

    subs = Subscription.query.order_by(Subscription.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template("admin/subscriptions.html", subs=subs)


@admin_bp.route("/payments")
def payments():
    page = request.args.get("page", 1, type=int)
    per_page = 25

    invoices = Invoice.query.order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template("admin/payments.html", invoices=invoices)


@admin_bp.route("/audit-logs")
def audit_logs():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    per_page = 50

    query = AuditLog.query
    if search:
        query = query.filter(AuditLog.action.ilike(f"%{search}%"))

    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template("admin/audit_logs.html", logs=logs, search=search)


@admin_bp.route("/analytics")
def analytics():
    stats = AnalyticsService.get_dashboard_stats()
    user_growth = AnalyticsService.get_user_growth(90)
    revenue_growth = AnalyticsService.get_revenue_growth(180)
    subscription_dist = AnalyticsService.get_subscription_distribution()

    return render_template(
        "admin/analytics.html",
        stats=stats,
        user_growth=user_growth,
        revenue_growth=revenue_growth,
        subscription_dist=subscription_dist,
    )
