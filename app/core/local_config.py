from app.core.config import Config


def _sqlite_engine_options():
    return {"pool_pre_ping": True}


class LocalConfig(Config):
    SECRET_KEY = "local-dev-key-change-in-production"
    SQLALCHEMY_DATABASE_URI = "sqlite:///dev.db"
    SQLALCHEMY_ENGINE_OPTIONS = _sqlite_engine_options()
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    SESSION_TYPE = "filesystem"
    STRIPE_SECRET_KEY = "sk_test_placeholder"
    STRIPE_PUBLISHABLE_KEY = "pk_test_placeholder"
