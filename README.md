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
| Backend | Python 3.13+, Flask, SQLAlchemy, Alembic |
| Frontend | HTMX 2.x, Alpine.js 3.x, TailwindCSS, Chart.js |
| Database | PostgreSQL 16+ |
| Cache & Queue | Redis 7+ |
| Payments | Stripe |
| Auth | bcrypt, Authlib (Google OAuth) |
| Tasks | RQ (Redis Queue) |
| Infrastructure | Docker, Docker Compose, Nginx |
| CI/CD | GitHub Actions |
| Deployment | Railway, VPS, Cloudflare-compatible |

## Quick Start

### Prerequisites
- Python 3.13+, PostgreSQL 16+, Redis 7+, Docker (optional)

### Local

```bash
git clone https://github.com/aldindugolli/SaaSForge.git
cd SaaSForge
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # Edit with your config
flask db upgrade
flask seed-data
flask run
```

### Docker

```bash
docker-compose up -d
docker-compose exec web flask db upgrade
docker-compose exec web flask seed-data
```

Open http://localhost:5000

### Demo Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@saasforge.com | Admin123! | Admin |
| demo@saasforge.com | Demo123! | User |

## Project Structure

```
saasforge/
├── app/
│   ├── admin/           # Admin dashboard routes & views
│   ├── analytics/       # Analytics endpoints
│   ├── api/             # REST API v1
│   ├── auth/            # Authentication (login, register, OAuth)
│   ├── billing/         # Stripe billing & webhooks
│   ├── core/            # Config, models, extensions, CLI, error handlers
│   ├── notifications/   # In-app notification system
│   ├── organizations/   # Team management & invitations
│   ├── services/        # Business logic layer (service classes)
│   ├── static/          # CSS, JS, images
│   └── templates/       # Jinja2 templates (20+ pages)
├── tests/               # pytest unit & integration tests
├── migrations/          # Alembic migration config
├── docker/              # Nginx config for production
├── .github/workflows/   # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml   # Dev setup
├── docker-compose.prod.yml
├── requirements.txt
├── pyproject.toml
├── railway.json
└── .pre-commit-config.yaml
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

### Background Jobs

Jobs in `app/jobs.py` run via RQ workers:
- `send_email_job` — async email delivery
- `process_analytics_job` — periodic analytics processing
- `cleanup_expired_data_job` — expired invitations/tokens
- `generate_weekly_report_job` — admin digest

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

See `.env.example` for all 30+ config options covering:
- Flask, database, Redis, Stripe, Google OAuth, SendGrid, Sentry, rate limiting, sessions, feature flags

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
