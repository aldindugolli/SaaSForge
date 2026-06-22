from datetime import UTC, datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.extensions import cache, db
from app.services.auth_service import AuthService
from app.services.base import NotFoundError, ValidationError
from app.services.impersonation_service import ImpersonationService
from app.services.session_service import SessionService
from app.services.two_factor_service import TwoFactorService

core_bp = Blueprint("core", __name__)


@core_bp.route("/")
def index():
    if current_user.is_authenticated:
        org = current_user.current_organization
        if org:
            return redirect(url_for("core.dashboard"))
        return redirect(url_for("organizations.create"))
    return render_template("landing.html")


@core_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@core_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "").strip()
        bio = request.form.get("bio", "").strip()
        website = request.form.get("website", "").strip()

        if name:
            current_user.name = name
        current_user.company = company
        current_user.location = location
        current_user.bio = bio
        current_user.website = website
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("core.settings"))

    return render_template("settings.html")


@core_bp.route("/auth/change-password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("core.settings"))

    try:
        AuthService.change_password(current_user, current_password, new_password)
        flash("Password changed successfully.", "success")
    except ValidationError as e:
        flash(e.message, "error")

    return redirect(url_for("core.settings"))


@core_bp.route("/impersonate/stop", methods=["POST"])
@login_required
def stop_impersonation():
    ImpersonationService.stop_impersonation()
    flash("Impersonation stopped.", "info")
    return redirect(url_for("admin.users"))


@core_bp.route("/sessions")
@login_required
def sessions():
    user_sessions = SessionService.get_user_sessions(current_user.id)
    return render_template("sessions.html", sessions=user_sessions)


@core_bp.route("/sessions/<session_id>/revoke", methods=["POST"])
@login_required
def revoke_session(session_id):
    try:
        if SessionService.revoke_session(session_id, current_user.id):
            flash("Session revoked.", "success")
        else:
            flash("Cannot revoke current session.", "error")
    except NotFoundError as e:
        flash(e.message, "error")
    return redirect(url_for("core.sessions"))


@core_bp.route("/sessions/revoke-all", methods=["POST"])
@login_required
def revoke_all_sessions():
    count = SessionService.revoke_all_sessions(current_user.id, exclude_current=True)
    flash(f"Revoked {count} other session(s).", "success")
    return redirect(url_for("core.sessions"))


@core_bp.route("/2fa/setup")
@login_required
def two_factor_setup():
    if current_user.totp_enabled:
        flash("Two-factor authentication is already enabled.", "info")
        return redirect(url_for("core.settings"))

    if not current_user.totp_secret:
        current_user.totp_secret = TwoFactorService.generate_secret()
        db.session.commit()

    qr = TwoFactorService.generate_qr_code_base64(current_user.totp_secret, current_user.email)
    backup_codes = TwoFactorService.generate_backup_codes()
    return render_template("two_factor_setup.html", qr=qr, secret=current_user.totp_secret, backup_codes=backup_codes)


@core_bp.route("/2fa/verify", methods=["POST"])
@login_required
def two_factor_verify():
    code = request.form.get("code", "").strip()
    backup_codes_raw = request.form.get("backup_codes", "")
    if not code:
        flash("Verification code is required.", "error")
        return redirect(url_for("core.two_factor_setup"))

    if current_user.totp_enabled:
        flash("2FA is already enabled.", "info")
        return redirect(url_for("core.settings"))

    secret = current_user.totp_secret
    if not secret:
        flash("2FA setup not started. Generate a secret first.", "error")
        return redirect(url_for("core.two_factor_setup"))

    if TwoFactorService.verify_code(secret, code):
        current_user.totp_enabled = True
        current_user.totp_backup_codes = [bc.strip() for bc in backup_codes_raw.split(",") if bc.strip()]
        db.session.commit()
        flash("Two-factor authentication enabled.", "success")
    else:
        flash("Invalid code. Try again.", "error")

    return redirect(url_for("core.settings"))


@core_bp.route("/2fa/disable", methods=["POST"])
@login_required
def two_factor_disable():
    if not current_user.totp_enabled:
        flash("2FA is not enabled.", "info")
        return redirect(url_for("core.settings"))

    code = request.form.get("code", "").strip()
    if not code or not TwoFactorService.verify_code(current_user.totp_secret, code):
        flash("Invalid verification code.", "error")
        return redirect(url_for("core.settings"))

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_backup_codes = None
    db.session.commit()
    flash("Two-factor authentication disabled.", "success")
    return redirect(url_for("core.settings"))


@core_bp.route("/health")
def health():
    """Health check endpoint for monitoring."""
    import time

    from sqlalchemy import text

    from app.core.extensions import db

    start = time.time()
    healthy = {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

    try:
        db.session.execute(text("SELECT 1"))
        healthy["database"] = "up"
    except Exception as e:
        healthy["database"] = f"down: {e}"
        healthy["status"] = "degraded"

    try:
        if cache.available:
            cache._client.ping()
            healthy["cache"] = "up"
        else:
            healthy["cache"] = "in-memory"
    except Exception as e:
        healthy["cache"] = f"down: {e}"
        healthy["status"] = "degraded"

    try:
        import redis
        from flask import current_app
        redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        healthy["queue"] = "up"
    except Exception:
        healthy["queue"] = "unavailable"

    try:
        from app.services.webhook_service import StripeWebhookProcessor
        stats = StripeWebhookProcessor.get_event_stats()
        healthy["webhook_events"] = stats["total"]
        healthy["webhook_dead_letter"] = len(stats["dead_letter"])
    except Exception:
        healthy["webhook_events"] = 0

    healthy["response_time_ms"] = int((time.time() - start) * 1000)

    status_code = 200 if healthy["status"] == "ok" else 503
    return jsonify(healthy), status_code


@core_bp.route("/health/detailed")
def health_detailed():
    """Detailed health check with component-level status."""
    from app.observability import (
        HealthStatus,
        check_database,
        check_email_service,
        check_queue,
        check_redis,
        check_stripe,
    )

    hs = HealthStatus()
    hs.check("database", check_database, "PostgreSQL connectivity")
    hs.check("redis", check_redis, "Redis cache connectivity")
    hs.check("queue", check_queue, "Background job queue (Redis)")
    hs.check("stripe", check_stripe, "Stripe API connectivity")
    hs.check("email", check_email_service, "Email service configuration")

    return jsonify(hs.to_dict(detailed=True))


@core_bp.route("/metrics")
def metrics():
    """Prometheus-compatible metrics endpoint."""
    from app.observability import metrics_registry
    return metrics_registry.render(), 200, {"Content-Type": "text/plain; version=0.0.4"}
