from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.extensions import cache, cache_service, db
from app.core.models import (
    ApiRequestLog,
    AuditLog,
    Invoice,
    JobRecord,
    Organization,
    Subscription,
    User,
)
from app.services.analytics_service import AnalyticsService
from app.services.audit_service import AuditService
from app.services.business_metrics import BusinessMetricsService
from app.services.decorators import require_admin
from app.services.impersonation_service import ImpersonationService
from app.services.performance_service import PerformanceMetrics, get_slow_queries
from app.services.webhook_service import StripeWebhookProcessor

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
    cache_service.invalidate_analytics()
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
    cache_service.invalidate_analytics()
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
    cache_service.invalidate_analytics()
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


@admin_bp.route("/cache", methods=["GET", "POST"])
def cache_management():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "clear_all":
            cache.clear()
            flash("All cache cleared.", "success")
        elif action == "clear_analytics":
            cache.invalidate_pattern("analytics:*")
            flash("Analytics cache cleared.", "success")
        elif action == "clear_org":
            org_id = request.form.get("org_id", "").strip()
            if org_id:
                cache_service.invalidate_org_data(org_id)
                flash(f"Cache for org {org_id} cleared.", "success")
            else:
                flash("Org ID required.", "error")

    return render_template("admin/cache.html", cache_available=cache.available)


@admin_bp.route("/jobs")
def jobs():
    page = request.args.get("page", 1, type=int)
    per_page = 50
    records = JobRecord.query.order_by(JobRecord.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template("admin/jobs.html", records=records)


@admin_bp.route("/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    from app.services.job_scheduler import JobScheduler
    record = JobRecord.query.get_or_404(job_id)
    if record.rq_job_id:
        JobScheduler.cancel(record.rq_job_id)
    record.status = "canceled"
    db.session.commit()
    flash("Job canceled.", "success")
    return redirect(url_for("admin.jobs"))


@admin_bp.route("/jobs/enqueue", methods=["POST"])
def enqueue_job():
    from app.jobs import cleanup_expired_data_job, process_analytics_job
    from app.services.job_scheduler import JobScheduler

    job_name = request.form.get("job_name")
    if job_name == "analytics":
        JobScheduler.enqueue("Analytics Refresh", process_analytics_job)
        flash("Analytics job enqueued.", "success")
    elif job_name == "cleanup":
        JobScheduler.enqueue("Cleanup Expired", cleanup_expired_data_job)
        flash("Cleanup job enqueued.", "success")
    else:
        flash("Unknown job.", "error")

    return redirect(url_for("admin.jobs"))


@admin_bp.route("/api-stats")
def api_stats():
    from sqlalchemy import func

    total = ApiRequestLog.query.count()
    by_endpoint = (
        db.session.query(
            ApiRequestLog.endpoint,
            func.count(ApiRequestLog.id).label("count"),
            func.avg(ApiRequestLog.response_time_ms).label("avg_ms"),
        )
        .group_by(ApiRequestLog.endpoint)
        .order_by(func.count(ApiRequestLog.id).desc())
        .limit(20)
        .all()
    )
    by_status = (
        db.session.query(
            ApiRequestLog.status_code,
            func.count(ApiRequestLog.id).label("count"),
        )
        .group_by(ApiRequestLog.status_code)
        .order_by(func.count(ApiRequestLog.id).desc())
        .all()
    )
    recent = ApiRequestLog.query.order_by(ApiRequestLog.created_at.desc()).limit(50).all()

    return render_template(
        "admin/api_stats.html",
        total=total,
        by_endpoint=by_endpoint,
        by_status=by_status,
        recent=recent,
    )


@admin_bp.route("/trial-analytics")
def trial_analytics():
    stats = AnalyticsService.get_trial_conversion_stats(90)
    return render_template("admin/trial_analytics.html", stats=stats)


@admin_bp.route("/performance")
def performance():
    data = PerformanceMetrics.get_dashboard_data()
    slow_queries = get_slow_queries(20)
    return render_template("admin/performance.html", data=data, slow_queries=slow_queries)


@admin_bp.route("/business-metrics")
def business_metrics():
    metrics = BusinessMetricsService.get_all_metrics()
    return render_template("admin/business_metrics.html", metrics=metrics)


@admin_bp.route("/webhooks")
def webhook_admin():
    stats = StripeWebhookProcessor.get_event_stats()
    return render_template("admin/webhooks.html", stats=stats)


@admin_bp.route("/webhooks/retry", methods=["POST"])
def retry_webhooks():
    results = StripeWebhookProcessor.retry_failed_events()
    flash(f"Retried {len(results)} webhook events.", "success")
    return redirect(url_for("admin.webhook_admin"))


@admin_bp.route("/reset-demo", methods=["POST"])
def reset_demo():
    """Reset all demo data to a clean state."""
    from app.services.demo_service import reset_demo_data
    result = reset_demo_data()
    flash(f"Demo data reset: {len(result.get('created', []))} records recreated.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/impersonate", methods=["POST"])
def impersonate():
    email = request.form.get("email", "").strip()
    reason = request.form.get("reason", "").strip()
    if not email:
        flash("Email is required.", "error")
        return redirect(url_for("admin.users"))
    if not reason:
        flash("A reason is required for impersonation.", "error")
        return redirect(url_for("admin.users"))
    target = User.query.filter_by(email=email).first()
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))
    if target.is_admin and target.id != current_user.id:
        flash("Cannot impersonate other admins.", "error")
        return redirect(url_for("admin.users"))
    if ImpersonationService.start_impersonation(current_user, target, reason):
        flash(f"Now impersonating {target.email}.", "warning")
    else:
        flash("Impersonation failed.", "error")
    return redirect(url_for("core.dashboard"))



