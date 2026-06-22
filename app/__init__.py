from datetime import UTC

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

    return app


def initialize_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    limiter.init_app(app)
    rq.init_app(app)
    cache.init_app(app)
    swagger.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.login_message = "Please log in to access this page."

    with app.app_context():
        import app.core.models  # noqa: F401  ensure models registered


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

    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(org_bp, url_prefix="/org")
    app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(security_bp)


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
    from datetime import datetime

    def humanize_date(dt):
        if not dt:
            return ""
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


def init_oauth(app):
    from app.auth.routes import init_oauth as _init_oauth
    _init_oauth(app)


def register_shell_context(app):
    @app.shell_context_processor
    def shell_context():
        from app.core.models import Membership, Organization, Subscription, User

        return {
            "db": db,
            "User": User,
            "Organization": Organization,
            "Membership": Membership,
            "Subscription": Subscription,
        }


def register_cli_commands(app):
    from app.core.cli import create_admin, list_routes, schedule_jobs, seed_data

    app.cli.add_command(seed_data)
    app.cli.add_command(create_admin)
    app.cli.add_command(list_routes)
    app.cli.add_command(schedule_jobs)


def register_scheduled_jobs(app):
    pass  # Jobs are scheduled via `flask schedule-jobs` CLI command
