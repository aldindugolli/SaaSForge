from flasgger import Swagger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from app.services.cache_service import CacheService, RedisCache

try:
    from flask_rq2 import RQ
    rq = RQ()
except (ImportError, ModuleNotFoundError):
    rq = None

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()

cache = RedisCache()
cache_service = CacheService(cache)

swagger = Swagger(template={
    "info": {
        "title": "SaaSForge API",
        "description": "Enterprise SaaS platform API — multi-tenant, RBAC, billing, analytics.",
        "version": "1.0.0",
        "contact": {
            "email": "support@saasforge.dev",
        },
    },
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication. Generate keys from the dashboard.",
        },
        "SessionAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Cookie",
            "description": "Session cookie (flask session) for browser-based requests.",
        },
    },
    "security": [{"ApiKeyAuth": []}, {"SessionAuth": []}],
    "tags": [
        {"name": "Status", "description": "API health and status"},
        {"name": "Users", "description": "Current user information"},
        {"name": "Organizations", "description": "Multi-tenant organization management"},
        {"name": "API Keys", "description": "API key lifecycle management"},
        {"name": "Admin", "description": "Admin-only administrative endpoints"},
    ],
})
