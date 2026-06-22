# SaaSForge

A production-ready Flask SaaS boilerplate — authentication, team management, subscription billing, analytics, and more.

---

## Features

| Category | Capabilities |
|----------|-------------|
| **Authentication** | Email/password & Google OAuth, email verification, password reset, session management |
| **Multi-Tenant Orgs** | Teams with roles (Owner/Admin/Member), invitations, ownership transfer |
| **Subscription Billing** | Stripe Checkout, Customer Portal, webhooks, invoices, trial periods |
| **Admin Dashboard** | User/org management, ban/disable, audit logs, subscription overview |
| **Analytics** | User growth, revenue/MRR tracking, churn rate, subscription distribution (Chart.js) |
| **Background Jobs** | Redis-backed RQ workers for email, webhooks, data cleanup, scheduled reports |
| **REST API** | Versioned (`/api/v1`), API keys, rate limiting, usage tracking |
| **Notifications** | In-app (HTMX) and email (SendGrid) |
| **Feature Flags** | Global, organization, and user-level |
| **Audit Logging** | Track all critical actions with searchable logs |
| **RBAC** | Reusable decorators (`@require_owner`, `@require_admin`, `@require_role`) |
| **Dark Mode** | Full light/dark theme, cookie-persisted |
| **Responsive** | Mobile-first with TailwindCSS |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13+, Flask 3.x, SQLAlchemy 2.0, Alembic, Marshmallow, Pydantic |
| Frontend | HTMX 2.x, Alpine.js 3.x, TailwindCSS 3.x (CDN), Chart.js 4.x |
| Database | PostgreSQL 16+ (production), SQLite (development, auto-detected) |
| Cache & Queue | Redis 7+ |
| Payments | Stripe (Checkout, Customer Portal, Webhooks) |
| Auth | bcrypt (Werkzeug), Flask-Login, Authlib (Google OAuth) |
| Tasks | RQ (Redis Queue) with scheduled jobs |
| Infrastructure | Docker, Docker Compose, Nginx (alpine) |
| CI/CD | GitHub Actions (lint → test → build → deploy) |
| Deployment | Railway, VPS |
| Monitoring | Sentry SDK |
| API Documentation | Flasgger + APISpec |

## Quick Start

### Prerequisites
- Python 3.13+, Docker (optional for PostgreSQL/Redis)

### Local (SQLite — no external services)

```bash
git clone https://github.com/aldindugolli/SaaSForge.git
cd SaaSForge
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
venv\Scripts\activate                              # Windows PowerShell
pip install -r requirements.txt
python run.py                                       # Auto-detects SQLite, no config needed
```

Then in another terminal:
```bash
source venv/bin/activate
flask seed-data
```

Open http://localhost:5000
Login with admin@saasforge.com / Admin123!

### Docker (PostgreSQL + Redis)

```bash
docker-compose up -d
docker-compose exec web flask db upgrade
docker-compose exec web flask seed-data
```

### Demo Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@saasforge.com | Admin123! | Admin + Org Owner |
| demo@saasforge.com | Demo123! | User + Org Owner |

> **Note:** `python run.py` automatically switches to SQLite (`LocalConfig`) when `DATABASE_URL` is not set or is not PostgreSQL. For PostgreSQL/Redis, set `DATABASE_URL` and `REDIS_URL` env vars and the app uses the full `Config` class.

## Project Structure

```
saasforge/
├── app/
│   ├── admin/           # Admin dashboard routes & views
│   ├── analytics/       # Analytics endpoints + Chart.js
│   ├── api/             # REST API v1 (API key auth)
│   ├── auth/            # Authentication (login, register, OAuth, password reset)
│   ├── billing/         # Stripe billing & webhooks
│   ├── core/            # Config, models (11), extensions, CLI, error handlers
│   ├── notifications/   # In-app notification system
│   ├── organizations/   # Team management & invitations
│   ├── services/        # Business logic layer (8 service classes)
│   ├── static/          # CSS, JS
│   └── templates/       # Jinja2 templates (30+ pages)
├── tests/               # 35+ pytest unit & integration tests
├── migrations/          # Alembic migration config
├── docker/              # Nginx config for production
├── .github/workflows/   # CI/CD pipeline
├── Dockerfile           # Multi-stage build (gunicorn + gevent)
├── docker-compose.yml   # Dev: web + worker + scheduler + db + redis
├── docker-compose.prod.yml  # + nginx
├── requirements.txt     # 82 pinned dependencies
├── pyproject.toml       # Ruff, Black, mypy, pytest config
├── railway.json
├── run.py               # Dev entrypoint (auto SQLite)
└── wsgi.py              # Production entrypoint (gunicorn)
```

## Architecture

### Service Layer Pattern

```
Presentation (routes/HTMX) → Service Layer (business logic) → Data Layer (models/DB)
                                  ↕
                          Infrastructure (email, Stripe, Redis)
```

All business logic lives in `app/services/`. Routes are thin — they validate input, call services, and render templates.

### Multi-Tenancy

```
Organization
├── Owner    — full access, billing, delete
├── Admin    — manage members, settings
└── Member   — basic access
```

Data is isolated by `organization_id` on all resources.

### Services

| Service | Responsibility |
|---------|---------------|
| `AuthService` | Register, login, password management, email verification, Google OAuth |
| `OrganizationService` | Org CRUD, invitations, member roles, ownership transfer |
| `BillingService` | Stripe Checkout, Customer Portal, webhook handling (6 event types) |
| `AnalyticsService` | Dashboard stats, user/revenue growth, churn, MRR, plan distribution |
| `EmailService` | SendGrid with dev log fallback, 5 email templates |
| `NotificationService` | In-app notifications CRUD, unread count, bulk create |
| `AuditService` | Audit logging with decorator support, searchable logs |
| `BaseService[T]` | Generic CRUD base class for data access |

### Background Jobs

Jobs in `app/jobs.py` run via RQ workers on the `saasforge-jobs` queue:
- `send_email_job` / `send_verification_email_job` — async email delivery
- `process_analytics_job` — periodic analytics processing
- `cleanup_expired_data_job` — expired invitations/tokens cleanup
- `generate_weekly_report_job` — admin digest notifications

## API

Base URL: `/api/v1`

Authenticate with `X-API-Key` header:

```bash
curl -H "X-API-Key: sf_your_api_key" http://localhost:5000/api/v1/me
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/` | API info |
| GET | `/api/v1/me` | Current user profile |
| GET | `/api/v1/organizations` | List user's orgs |
| GET | `/api/v1/organizations/:id` | Org details |
| GET | `/api/v1/organizations/:id/members` | Org members |
| GET | `/api/v1/keys` | List API keys |
| POST | `/api/v1/keys` | Create API key |
| POST | `/api/v1/keys/:id/revoke` | Revoke API key |
| GET | `/api/v1/admin/stats` | Admin dashboard stats |

### Create API Key

```bash
curl -X POST http://localhost:5000/api/v1/keys \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=My Key&key_type=test" \
  -b "session=your_session_cookie"
```

## Deployment

### Railway

```bash
railway login
railway up
```
Set env vars in Railway dashboard. `railway.json` included.

### VPS (Docker)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables

See `.env.example` for all 55 config options covering:
- Flask (secret key, debug, session lifetime)
- Database (PostgreSQL URL, pool settings)
- Redis (URL for session store + RQ)
- Stripe (secret key, webhook secret, price IDs)
- Auth (Google OAuth client ID/secret)
- Email (SendGrid API key, sender)
- Monitoring (Sentry DSN)
- Rate limiting (default, storage backend)
- Feature flags
- Upload settings (max size, allowed extensions)

> **Local dev:** `python run.py` needs no env vars — it auto-selects SQLite, disables CSRF/rate limiting, and logs emails to console. Set `DATABASE_URL=postgresql://...` to run against PostgreSQL.

## Testing

```bash
pytest                          # All tests
pytest --cov=app --cov-report=html  # With coverage
pytest tests/unit/test_auth_service.py -v   # Single file
```

Test structure:
- `tests/unit/` — service & model unit tests
- `tests/integration/` — route integration tests

## Security

- CSRF protection (Flask-WTF) on all forms
- Session-based auth with HTTP-only secure cookies
- Password hashing via bcrypt (Werkzeug)
- Rate limiting (Flask-Limiter + Redis)
- Input validation at service layer
- XSS protection via Jinja2 auto-escaping
- Audit logging for all critical actions
- RBAC decorators enforce permissions
- Stripe webhook signature verification
- SQL injection protection via SQLAlchemy ORM

## License

MIT
