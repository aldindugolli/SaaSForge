import os
from datetime import timedelta
from pathlib import Path


def _compute_engine_options(db_uri):
    opts = {"pool_pre_ping": True}
    if not db_uri.startswith("sqlite"):
        opts.update({
            "pool_size": int(os.environ.get("DATABASE_POOL_SIZE", 10)),
            "pool_max_overflow": int(os.environ.get("DATABASE_POOL_MAX_OVERFLOW", 20)),
            "pool_recycle": 300,
        })
    return opts


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")
    APP_NAME = os.environ.get("APP_NAME", "SaaSForge")
    APP_URL = os.environ.get("APP_URL", "http://localhost:5000")
    APP_DOMAIN = os.environ.get("APP_DOMAIN", "localhost:5000")

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/saasforge"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def _engine_options():
        return _compute_engine_options(Config.SQLALCHEMY_DATABASE_URI)

    SQLALCHEMY_ENGINE_OPTIONS = _compute_engine_options(
        os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/saasforge")
    )

    # Redis
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # RQ
    RQ_REDIS_URL = REDIS_URL

    # Session
    SESSION_TYPE = os.environ.get("SESSION_TYPE", "redis")
    SESSION_REDIS = REDIS_URL
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(
        seconds=int(os.environ.get("PERMANENT_SESSION_LIFETIME", 2592000))
    )

    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Stripe
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRO_PRICE_ID = os.environ.get("STRIPE_PRO_PRICE_ID", "")
    STRIPE_BUSINESS_PRICE_ID = os.environ.get("STRIPE_BUSINESS_PRICE_ID", "")

    STRIPE_PLANS = {
        "free": {
            "name": "Free",
            "price": 0,
            "price_id": None,
            "max_members": 1,
            "max_projects": 1,
            "features": ["Basic support"],
            "entitlements": {"api_access": False, "analytics": False, "custom_integrations": False, "sla": False},
        },
        "pro": {
            "name": "Pro",
            "price": 29,
            "price_id": os.environ.get("STRIPE_PRO_PRICE_ID", ""),
            "max_members": 5,
            "max_projects": 10,
            "features": ["Priority support", "API access", "Analytics"],
            "entitlements": {"api_access": True, "analytics": True, "custom_integrations": False, "sla": False},
        },
        "business": {
            "name": "Business",
            "price": 99,
            "price_id": os.environ.get("STRIPE_BUSINESS_PRICE_ID", ""),
            "max_members": 9999,
            "max_projects": 9999,
            "features": ["Dedicated support", "API access", "Advanced analytics", "Custom integrations", "SLA"],
            "entitlements": {"api_access": True, "analytics": True, "custom_integrations": True, "sla": True},
        },
    }

    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

    # Email
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@saasforge.com")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
    MAIL_SUPPRESS_SEND = os.environ.get("FLASK_ENV") == "development"

    # Rate Limiting
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "100/hour")
    RATELIMIT_STORAGE_URL = os.environ.get(
        "RATELIMIT_STORAGE_URL", "redis://localhost:6379/0"
    )
    RATELIMIT_STRATEGY = "moving-window"

    # Upload
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", str(BASE_DIR / "app" / "static" / "uploads")
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5242880))
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # Sentry
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

    # Feature Flags
    FEATURE_NEW_DASHBOARD = os.environ.get("FEATURE_NEW_DASHBOARD", "true").lower() == "true"
    FEATURE_BETA_API = os.environ.get("FEATURE_BETA_API", "false").lower() == "true"

    # Admin
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@saasforge.com")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
