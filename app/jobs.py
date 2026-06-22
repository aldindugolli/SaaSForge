"""Background job definitions for RQ workers."""
from datetime import UTC, datetime

from app.core.extensions import rq
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService


@rq.job("saasforge-jobs")
def send_email_job(to: str, subject: str, html_body: str):
    """Send an email as a background job."""
    return EmailService.send_email(to, subject, html_body)


@rq.job("saasforge-jobs")
def send_verification_email_job(user_id: str, email: str, verify_url: str):
    """Send verification email in background."""
    return EmailService.send_verification_email(email, verify_url)


@rq.job("saasforge-jobs")
def process_analytics_job(organization_id: str):
    """Process analytics data for an organization."""
    from app.services.analytics_service import AnalyticsService
    AnalyticsService.get_dashboard_stats()
    return {"status": "processed", "organization_id": organization_id}


@rq.job("saasforge-jobs")
def cleanup_expired_data_job():
    """Clean up expired invitations, tokens, etc."""
    from app.core.extensions import db
    from app.core.models import Invitation

    now = datetime.now(UTC)

    # Clean expired invitations
    expired = Invitation.query.filter(
        Invitation.expires_at < now,
        Invitation.accepted_at.is_(None),
    ).all()
    count = len(expired)
    for inv in expired:
        db.session.delete(inv)
    db.session.commit()

    return {"cleaned": count, "type": "expired_invitations"}


@rq.job("saasforge-jobs")
def generate_weekly_report_job():
    """Generate and send weekly analytics report to admins."""

    from app.core.models import User
    from app.services.analytics_service import AnalyticsService

    admins = User.query.filter_by(is_admin=True).all()
    stats = AnalyticsService.get_dashboard_stats()

    for admin in admins:
        NotificationService.create_notification(
            user_id=admin.id,
            title="Weekly Report",
            message=f"Users: {stats['total_users']}, MRR: ${stats['mrr']}, Churn: {stats['churn_rate']}%",
            type="info",
        )

    return {"notified": len(admins)}
