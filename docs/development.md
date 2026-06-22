# Development Guide

Guide for setting up a local development environment, understanding the codebase conventions, and contributing to SaaSForge.

---

## Table of Contents

- [Development Environment](#development-environment)
- [Setup](#setup)
- [Configuration](#configuration)
- [Codebase Conventions](#codebase-conventions)
- [Adding a New Feature](#adding-a-new-feature)
- [Database Migrations](#database-migrations)
- [Templates & UI](#templates--ui)
- [Testing](#testing)
- [Linting & Type Checking](#linting--type-checking)
- [Common Tasks](#common-tasks)

---

## Development Environment

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.13+ | Runtime |
| Git | — | Version control |
| PostgreSQL | 16+ (optional) | Production database |
| Redis | 7+ (optional) | Cache & job queue |

### Quick Start (No External Services)

```bash
git clone https://github.com/aldindugolli/SaaSForge.git
cd SaaSForge

python -m venv venv
# Activate:
#   Linux/macOS: source venv/bin/activate
#   Windows:      venv\Scripts\activate

pip install -r requirements.txt
python run.py
```

This automatically:
- Detects no PostgreSQL URL → uses SQLite
- Disables CSRF protection
- Disables rate limiting
- Logs emails to console instead of sending
- Uses filesystem sessions instead of Redis

### Full Stack (PostgreSQL + Redis)

```bash
# Start services
docker-compose up -d db redis

# Set environment variables
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/saasforge
export REDIS_URL=redis://localhost:6379/0

# Run database migrations
flask db upgrade

# Seed demo data
flask seed-data

# Start the app
python run.py
```

Or use Docker Compose for everything:

```bash
docker-compose up -d
docker-compose exec web flask db upgrade
docker-compose exec web flask seed-data
```

---

## Setup

### Step-by-Step

1. **Clone the repository**
   ```bash
   git clone https://github.com/aldindugolli/SaaSForge.git
   cd SaaSForge
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings (or leave defaults for SQLite dev)
   ```

5. **Seed the database** (creates admin + demo users)
   ```bash
   flask seed-data
   ```

6. **Run the app**
   ```bash
   python run.py
   ```

7. **Open in browser**
   ```
   http://localhost:5000
   ```

### Demo Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@saasforge.com | Admin123! | Admin + Org Owner |
| demo@saasforge.com | Demo123! | User + Org Owner |

---

## Configuration

### Environment Variables

Configuration is managed through environment variables and the `.env.example` file. The app uses two configuration classes:

#### LocalConfig (automatic when no PostgreSQL)

| Setting | Value | Notes |
|---------|-------|-------|
| Database | `sqlite:///dev.db` | Local file |
| CSRF | Disabled | WTF_CSRF_ENABLED=False |
| Rate Limiting | Disabled | RATELIMIT_ENABLED=False |
| Email | Suppressed | MAIL_SUPPRESS_SEND=True |
| Sessions | Filesystem | No Redis needed |
| Stripe | Placeholder keys | Can set real ones |

#### Config (when DATABASE_URL is PostgreSQL)

Full production configuration. Requires:
- `DATABASE_URL` — PostgreSQL connection
- `REDIS_URL` — Redis connection (sessions, cache, queue)
- `STRIPE_SECRET_KEY` + `STRIPE_PUBLISHABLE_KEY` — Payment processing
- `SECRET_KEY` — Flask session signing

### Switching Environments

The `run.py` entrypoint detects the environment:

```python
db_uri = os.environ.get("DATABASE_URL", "")
if not db_uri or "postgresql" not in db_uri:
    app = create_app(LocalConfig)  # SQLite dev mode
else:
    app = create_app(Config)       # PostgreSQL production mode
```

---

## Codebase Conventions

### Python

- **Style:** Ruff (compatible with Black)
- **Types:** mypy strict where practical
- **Imports:** stdlib → Flask/extensions → app modules
- **Line length:** 100 characters
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants

### Flask Patterns

**Route handler pattern:**
```python
@core_bp.route("/example", methods=["GET", "POST"])
@login_required
def example():
    form_data = request.form
    try:
        result = some_service.do_something(form_data)
        flash("Success!", "success")
        return redirect(url_for(".next_page"))
    except ValidationError as e:
        flash(str(e), "error")
        return render_template("example.html")
    except NotFoundError:
        abort(404)
```

**Service method pattern:**
```python
def do_something(self, input_data: str) -> Model:
    self._validate(input_data)
    record = self.base.create(**input_data)
    cache_service.invalidate_org_data(record.organization_id)
    audit_service.log("resource.created", ...)
    return record
```

### Template Conventions

- Extend `base.html` for consistent layout
- Use Tailwind utility classes exclusively (no custom CSS)
- Dark mode via `dark:` variants
- HTMX for dynamic updates, Alpine.js for interactive state
- Page header: `text-3xl font-bold tracking-tight`
- Cards: `bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm`

### JavaScript

- HTMX 2.x for AJAX/partial updates
- Alpine.js 3.x for client-side interactivity
- Chart.js 4.x for analytics charts
- No jQuery
- No build step (CDN-loaded libraries)

---

## Adding a New Feature

### 1. Database Model

Add your model to `app/core/models.py`:

```python
class MyModel(db.Model):
    __tablename__ = "my_models"
    id = db.Column(UUID, primary_key=True, default=uuid4)
    organization_id = db.Column(UUID, db.ForeignKey("organizations.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
```

Generate and apply migration:

```bash
flask db migrate -m "add my_models table"
flask db upgrade
```

### 2. Service Layer

Create a service class in `app/services/`:

```python
class MyModelService:
    def __init__(self):
        self.base = BaseService(MyModel)

    def create(self, org_id, name, actor_id):
        record = self.base.create(organization_id=org_id, name=name)
        audit_service.log("mymodel.created", "my_model", str(record.id),
                          actor_id=actor_id)
        return record

    def list_for_org(self, org_id):
        return MyModel.query.filter_by(organization_id=org_id).all()
```

### 3. Routes

Add a blueprint or extend an existing one in `app/*/routes.py`:

```python
from app.services.my_model_service import MyModelService
my_model_service = MyModelService()

MODELS_BP = Blueprint("models", __name__, url_prefix="/models")

@MODELS_BP.route("/")
@login_required
@org_required
def list_models():
    models = my_model_service.list_for_org(g.current_org.id)
    return render_template("models/index.html", models=models)
```

Register in `app/__init__.py`:

```python
from app.models.routes import MODELS_BP

def register_blueprints(app):
    # ... existing blueprints
    app.register_blueprint(MODELS_BP)
```

### 4. Templates

Create your template extending `base.html`:

```html
{% extends "base.html" %}
{% block title %}Models — {{ app_name }}{% endblock %}
{% block content %}
<div class="max-w-5xl mx-auto">
  <h1 class="text-3xl font-bold tracking-tight">Models</h1>
  <!-- Your content -->
</div>
{% endblock %}
```

### 5. Tests

Write unit tests for your service and integration tests for your routes:

```python
# tests/unit/test_my_model_service.py
def test_create_model(db_session, sample_user):
    service = MyModelService()
    model = service.create(org_id, "Test Model", sample_user.id)
    assert model.name == "Test Model"

# tests/integration/test_my_model_routes.py
def test_list_models(client, auth_headers):
    resp = client.get("/models/", headers=auth_headers)
    assert resp.status_code == 200
```

---

## Database Migrations

### Migration Commands

| Command | Description |
|---------|-------------|
| `flask db init` | Initialize migration repository (already done) |
| `flask db migrate -m "message"` | Generate migration from model changes |
| `flask db upgrade` | Apply all pending migrations |
| `flask db downgrade <revision>` | Rollback to revision |
| `flask db current` | Show current revision |
| `flask db history` | Show migration history |

### Migration Workflow

1. **Modify models** in `app/core/models.py`
2. **Generate migration:**
   ```bash
   flask db migrate -m "describe your changes"
   ```
3. **Review migration** in `migrations/versions/` — check for correctness
4. **Apply migration:**
   ```bash
   flask db upgrade
   ```
5. **Test** that everything works
6. **Commit** both model changes and migration file

### Migration Best Practices

- One migration per logical change
- Review auto-generated migrations for accuracy
- Test both `upgrade` and `downgrade`
- Never edit an existing migration that's been committed

---

## Templates & UI

### Template Structure

```
app/templates/
├── base.html              # Layout with Tailwind CDN, HTMX, Alpine.js
├── components/            # Reusable partials
│   ├── navbar.html        # Top navigation bar
│   ├── sidebar.html       # Sidebar navigation
│   ├── toast.html         # Toast notification container
│   ├── error_toast.html   # HTMX error toast
│   └── notification_list.html  # Notification dropdown
├── auth/                  # Authentication pages
├── admin/                 # Admin dashboard (14 pages)
├── organizations/         # Org management
├── billing/               # Subscription & payments
├── analytics/             # Charts & metrics
├── notifications/         # Notification center
├── security/              # Security settings
├── errors/                # Error pages (4xx, 5xx)
├── emails/                # Email templates
└── dashboard.html         # Main dashboard
```

### UI Conventions

| Element | Classes |
|---------|---------|
| Page title | `text-3xl font-bold tracking-tight` |
| Page subtitle | `text-gray-500 dark:text-gray-400 mt-1` |
| Card | `bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm` |
| Card header | `px-6 py-4 border-b border-gray-100 dark:border-gray-700` with `text-lg font-semibold` |
| Input | `w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none transition-all` |
| Label | `block text-sm font-medium mb-1.5` |
| Button (primary) | `bg-brand-600 text-white px-6 py-2.5 rounded-xl font-semibold hover:bg-brand-700 transition-colors` |
| Button (full width) | Add `w-full` |
| Link | `text-sm text-brand-600 hover:text-brand-700 font-medium` |
| Badge | `px-2.5 py-0.5 rounded-full text-xs font-medium` |
| Icon container | `w-10 h-10 rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center shadow-sm` |
| Container width | `max-w-7xl` (dashboard), `max-w-5xl` (security/analytics), `max-w-3xl` (settings) |
| Spacing between sections | `space-y-8` or `gap-6` grid |
| Hover row | `rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors` |

### HTMX Patterns

```html
<!-- Load content on page load -->
<div hx-get="/api/data" hx-trigger="load" hx-swap="innerHTML">
  Loading...
</div>

<!-- Form submission -->
<form hx-post="/resource" hx-target="#result" hx-swap="innerHTML">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  ...
</form>

<!-- Error handling -->
<body hx-on:htmx:before-swap="handleError(event)">
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Verbose
pytest -v

# Filter by test name
pytest -k "login"

# Run specific file
pytest tests/unit/test_auth_service.py -v

# Run by marker
pytest -m unit
pytest -m integration
```

### Test Structure

```
tests/
├── conftest.py               # Shared fixtures (app, client, db, auth)
│
├── unit/                     # Unit tests (no HTTP)
│   ├── test_base.py          # BaseService CRUD operations
│   └── test_auth_service.py  # AuthService methods
│
└── integration/              # Integration tests (with HTTP)
    └── test_auth_routes.py   # Auth route responses
```

### Writing Tests

**Unit test example:**
```python
def test_validate_password_valid(auth_service):
    is_valid, msg = auth_service.validate_password("Str0ng!Pass")
    assert is_valid
    assert msg == ""

def test_validate_password_too_short(auth_service):
    is_valid, msg = auth_service.validate_password("Ab1!")
    assert not is_valid
    assert "at least 8" in msg.lower()
```

**Integration test example:**
```python
def test_login_page(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"Sign In" in resp.data

def test_login_submission(client):
    resp = client.post("/auth/login", data={
        "email": "admin@saasforge.com",
        "password": "Admin123!",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data
```

### Fixtures

Available fixtures from `conftest.py`:

| Fixture | Returns | Scope |
|---------|---------|-------|
| `app` | Flask application | session |
| `client` | Flask test client | session |
| `db_session` | SQLAlchemy session | function |
| `sample_user` | User object | function |
| `auth_headers` | dict with auth cookie | function |

---

## Linting & Type Checking

### Running Linters

```bash
# Ruff (linting + formatting)
ruff check .                  # Check all files
ruff format .                 # Auto-format

# mypy (type checking)
mypy app/

# Pre-commit (all checks)
pre-commit run --all-files
```

### CI Pipeline

The GitHub Actions workflow runs:
1. `ruff check` — linting
2. `pytest --cov=app` — tests with coverage
3. `bandit -r app/` — security SAST
4. `safety check` — dependency vulnerabilities
5. `gitleaks detect` — secrets scanning

---

## Common Tasks

### Creating a New Admin User

```bash
flask create-admin admin@example.com "password123" "Admin Name"
```

### Viewing All Routes

```bash
flask list-routes
```

### Setting Up Recurring Jobs

```bash
flask schedule-jobs
```

This registers:
- Analytics processing (hourly)
- Expired data cleanup (daily at midnight)
- Weekly admin report (Monday 9am)

### Starting the RQ Worker (manually)

```bash
rq worker --url redis://localhost:6379/0 saasforge-jobs
```

### Inspecting the Database

```bash
flask shell
>>> User.query.all()
>>> Organization.query.first().members
```

### Clearing the Cache

```bash
# Via Flask shell
flask shell
>>> from app.core.extensions import cache
>>> cache.clear()
```

Or via the admin UI at `/admin/cache`.

### Debug Mode

In local development (SQLite mode):
- Debug toolbar available
- CSRF disabled for easy form testing
- Emails printed to console instead of sent
- No rate limiting

### Adding Environment Variables

1. Add to `.env.example` with a comment explaining the variable
2. Add to the appropriate config class (`Config` in `config.py` and/or `LocalConfig` in `local_config.py`)
3. Use `os.environ.get("VARIABLE_NAME", "default")` in the config
4. Reference in the `inject_global_context()` if needed in templates
