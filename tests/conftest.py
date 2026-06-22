import pytest
from app import create_app
from app.core.extensions import db as _db
from app.core.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    RATELIMIT_ENABLED = False
    RQ_ASYNC = False
    SECRET_KEY = "test-secret-key"
    STRIPE_SECRET_KEY = "sk_test_placeholder"
    STRIPE_PUBLISHABLE_KEY = "pk_test_placeholder"


@pytest.fixture(scope="session")
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    _db.session.begin_nested()
    yield _db
    _db.session.rollback()


@pytest.fixture(scope="function")
def client(app, db):
    return app.test_client()


@pytest.fixture(scope="function")
def auth_headers(client):
    return {"Content-Type": "application/x-www-form-urlencoded"}


@pytest.fixture(scope="function")
def registered_user(app, db):
    from app.services.auth_service import AuthService
    user = AuthService.register("test@example.com", "TestPass123!", "Test User")
    return user


@pytest.fixture(scope="function")
def logged_in_client(client, registered_user):
    from flask_login import login_user
    with client.application.test_request_context():
        login_user(registered_user)
    return client


@pytest.fixture(scope="function")
def organization(app, db, registered_user):
    from app.services.org_service import OrganizationService
    org = OrganizationService.create("Test Org", registered_user, "test-org")
    return org
