from flask import current_app
from flask_login import current_user


def inject_global_context():
    from app.services.impersonation_service import ImpersonationService
    ctx = {
        "app_name": current_app.config["APP_NAME"],
        "app_url": current_app.config["APP_URL"],
        "current_year": __import__("datetime").datetime.now().year,
        "stripe_publishable_key": current_app.config["STRIPE_PUBLISHABLE_KEY"],
        "feature_new_dashboard": current_app.config["FEATURE_NEW_DASHBOARD"],
        "feature_beta_api": current_app.config["FEATURE_BETA_API"],
        "is_impersonating": ImpersonationService.is_impersonating() if current_user.is_authenticated else False,
        "impersonation_reason": ImpersonationService.get_impersonation_reason() if current_user.is_authenticated else "",
    }

    if current_user.is_authenticated:
        ctx["current_org"] = current_user.current_organization
        ctx["user_orgs"] = current_user.organizations
        ctx["unread_notifications"] = current_user.notifications.filter_by(is_read=False).count()

    return ctx
