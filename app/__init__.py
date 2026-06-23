import logging
from datetime import UTC, datetime, timezone

from flask import Flask

from app.core.config import Config
from app.core.context_processors import inject_global_context
from app.core.extensions import (
    cache,
    csrf,
    db,
    limiter,
    login_manager,
    migrate,
    rq,
    swagger,
)

logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    initialize_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_context_processors(app)
    register_template_filters(app)
    register_shell_context(app)
    register_cli_commands(app)
    register_scheduled_jobs(app)
    init_oauth(app)
    init_observability(app)
    init_database_extensions(app)
    init_demo_environment(app)

    return app


def initialize_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    limiter.init_app(app)
    if rq is not None:
        rq.init_app(app)
    cache.init_app(app)
    swagger.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.login_message = "Please log in to access this page."

    with app.app_context():
        import app.core.models  # noqa: F401  ensure models registered
        import app.services.webhook_service  # noqa: F401


def register_blueprints(app):
    from app.admin.routes import admin_bp
    from app.analytics.routes import analytics_bp
    from app.api.routes import api_bp
    from app.auth.routes import auth_bp
    from app.billing.routes import billing_bp
    from app.core.routes import core_bp
    from app.notifications.routes import notifications_bp
    from app.organizations.routes import org_bp
    from app.security.routes import security_bp
    from app.webhooks.routes import webhooks_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(org_bp, url_prefix="/org")
    app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(security_bp)
    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")


def register_error_handlers(app):
    from app.core.error_handlers import (
        handle_400,
        handle_403,
        handle_404,
        handle_429,
        handle_500,
    )

    app.register_error_handler(400, handle_400)
    app.register_error_handler(403, handle_403)
    app.register_error_handler(404, handle_404)
    app.register_error_handler(429, handle_429)
    app.register_error_handler(500, handle_500)


def register_context_processors(app):
    app.context_processor(inject_global_context)


def register_template_filters(app):
    def humanize_date(dt):
        if not dt:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(UTC)
        diff = now - dt
        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = int(seconds / 60)
            return f"{m}m ago"
        if seconds < 86400:
            h = int(seconds / 3600)
            return f"{h}h ago"
        if seconds < 2592000:
            d = int(seconds / 86400)
            return f"{d}d ago"
        return dt.strftime("%b %d, %Y")

    app.jinja_env.filters["humanize"] = humanize_date

    def format_currency(cents: int, currency: str = "USD") -> str:
        """Format cents to currency string."""
        from markupsafe import Markup
        symbols = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}
        symbol = symbols.get(currency.upper(), "$")
        # Return safe HTML for inline usage
        return Markup(f"{symbol}{cents / 100:.2f}")

    app.jinja_env.filters["currency"] = format_currency

    def format_number(n: int) -> str:
        """Format large numbers with K/M suffixes."""
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)

    app.jinja_env.filters["compact"] = format_number

    def pct_change(current: float, previous: float) -> str:
        """Format percentage change."""
        if previous == 0:
            return "+100%"
        change = ((current - previous) / previous) * 100
        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.1f}%"

    app.jinja_env.filters["pct_change"] = pct_change


def init_oauth(app):
    from app.auth.routes import init_oauth as _init_oauth
    _init_oauth(app)


def init_observability(app):
    """Initialize observability: structured logging, correlation IDs, metrics."""
    from app.observability import CorrelationMiddleware, MetricsMiddleware, setup_logging
    setup_logging(app)
    CorrelationMiddleware(app)
    MetricsMiddleware(app)
    logger.info("Observability initialized")


def init_database_extensions(app):
    """Initialize database extensions (PostgreSQL-specific)."""
    with app.app_context():
        try:
            from app.db import create_gin_indexes, create_expression_indexes, create_full_text_search, create_materialized_views
            create_gin_indexes()
            create_expression_indexes()
            create_full_text_search()
            create_materialized_views()
        except Exception as e:
            logger.warning(f"Database extensions setup skipped: {e}")


def register_shell_context(app):
    @app.shell_context_processor
    def shell_context():
        from app.core.models import (
            Membership,
            Notification,
            Organization,
            Subscription,
            User,
        )
        from app.services.webhook_service import (
            CustomerWebhookEndpoint,
            WebhookDelivery,
            WebhookEventLog,
        )

        return {
            "db": db,
            "User": User,
            "Organization": Organization,
            "Membership": Membership,
            "Subscription": Subscription,
            "Notification": Notification,
            "WebhookEndpoint": CustomerWebhookEndpoint,
            "WebhookDelivery": WebhookDelivery,
            "WebhookEventLog": WebhookEventLog,
        }


def register_cli_commands(app):
    from app.core.cli import create_admin, list_routes, schedule_jobs, seed_data, seed_demo_data

    app.cli.add_command(seed_data)
    app.cli.add_command(seed_demo_data)
    app.cli.add_command(create_admin)
    app.cli.add_command(list_routes)
    app.cli.add_command(schedule_jobs)


def init_demo_environment(app):
    """Initialize demo environment safety middleware."""
    from app.services.demo_service import DemoMiddleware
    DemoMiddleware(app)
    logger.info("Demo environment middleware initialized")


def register_scheduled_jobs(app):
    pass  # Jobs are scheduled via `flask schedule-jobs` CLI command
