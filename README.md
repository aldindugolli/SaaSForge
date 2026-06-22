# SaaSForge

A production-ready Flask SaaS boilerplate with multi-tenant organizations, subscription billing, RBAC, 2FA, background jobs, REST API, admin dashboard, **observability platform**, **customer webhook system**, **scoped API platform**, **performance engineering**, **executive business metrics**, and **demo environment**. Designed for teams that want to launch a SaaS product without rebuilding the foundation — then scale it with enterprise-grade operational excellence.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Observability](#observability)
- [Services](#services)
- [Models](#models)
- [Routes & Blueprints](#routes--blueprints)
- [Background Jobs](#background-jobs)
- [API Reference](#api-reference)
- [CLI Commands](#cli-commands)
- [Testing](#testing)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)
- [Security](#security)
- [Database Migrations](#database-migrations)

---

## Features

### Authentication & Account Security
| Feature | Description |
|---------|-------------|
| Email/password registration & login | bcrypt hashing, Flask-Login sessions |
| Google OAuth 2.0 | Authlib integration with callback |
| Email verification | Token-based email confirmation flow |
| Password reset | Secure token-based reset with email delivery |
| Two-factor authentication (TOTP) | QR setup via pyotp, authenticator apps, backup codes |
| 2FA challenge flow | Intercept on login when 2FA is enabled |
| Session management | Track active sessions with browser/OS/IP, revoke individual or all |
| Security center dashboard | Overview of login activity, failed attempts, sessions, 2FA status, API keys |

### Multi-Tenant Organizations
| Feature | Description |
|---------|-------------|
| Organization creation | Each org is a tenant boundary |
| Member roles | Owner (full access), Admin (manage members/settings), Member (basic) |
| Granular permissions | 13 permissions across 3 roles, `@require_permission` decorator |
| Invitations | Email-based invite flow with token, expiry, and revocation |
| Ownership transfer | Transfer org ownership to another member |
| Per-org settings | Brand color, description, timezone, website |
| Activity feed | Per-org audit log timeline |
| Org switching | Users can belong to multiple orgs and switch between them |

### Subscription Billing
| Feature | Description |
|---------|-------------|
| Stripe Checkout | Create checkout sessions for pro/business plans |
| Stripe Customer Portal | Self-serve subscription management |
| Webhook handling | 6 event types with idempotent processing via `WebhookEventLog` |
| Plan tiers | Free, Pro, Business with configurable Stripe price IDs |
| Trial periods | Configurable trial with conversion analytics |
| Payment history | Invoice records with PDF links |
| Entitlement checks | `@entitlement_required` decorator for feature gating |
| Plan-based limits | Max members, max projects per tier |

### Observability Platform
| Feature | Description |
|---------|-------------|
| Structured JSON logging | `StructuredFormatter` with timestamp, level, module, function, correlation_id |
| Correlation IDs | `X-Correlation-ID` header propagated through all services, DB queries, jobs |
| Prometheus metrics | HTTP counters/histograms, DB query duration, cache hits/misses, worker throughput |
| Health monitoring | `GET /health` (basic) and `GET /health/detailed` (5-component check: DB, Redis, Queue, Stripe, Email) |
| Metrics endpoint | `GET /metrics` with Prometheus text format |

### PostgreSQL Optimization
| Feature | Description |
|---------|-------------|
| JSONB column helpers | `jsonb_column()` factory with SQLite fallback |
| GIN indexes | Expression indexes for JSONB path queries |
| Full-text search | tsvector trigger-based auto-updating columns |
| Materialized views | `mv_dashboard_stats`, `mv_revenue_by_month`, `mv_api_usage_stats` |
| Query optimization | `eager_load_*`, `ANALYZE` helpers |
| Graceful degradation | All PG features no-op on SQLite |

### Customer Webhook System
| Feature | Description |
|---------|-------------|
| Endpoint management UI | Create, update, toggle, delete webhook endpoints |
| Event subscription | Subscribe to specific event types via checkboxes |
| HMAC signing | `sha256` signature in `X-Webhook-Signature` header |
| Delivery history | Status, attempts, response code/body for each delivery |
| Retry mechanism | Up to 5 retries with exponential backoff |
| Test endpoint | Send test event to verify endpoint connectivity |
| Admin dead-letter queue | View and retry failed Stripe webhook events |

### Advanced API Platform
| Feature | Description |
|---------|-------------|
| Scoped permissions | 12 API permission scopes (read:users, write:orgs, admin:analytics, etc.) |
| Preset permission groups | `read`, `write`, `admin`, `full` scope presets |
| `@require_api_permission` | Decorator-level scope enforcement |
| Usage limits per plan | Free 1k/day, Pro 10k/day, Business 100k/day |
| `api_auth_required` middleware | Key lookup, expiry check, daily limit enforcement |
| API request logging | Full audit trail with response times, status codes |

### Performance Engineering
| Feature | Description |
|---------|-------------|
| P95/P99 response tracking | From `ApiRequestLog` with percentile_cont |
| Slowest endpoints analysis | Grouped by method + endpoint, sorted by avg latency |
| `@monitor_query` decorator | Tracks slow service methods (>500ms) |
| Slow query registry | In-memory list (capped at 100 entries) with timestamps |
| Cache analytics | Hit/miss counters, operations total |
| pg_stat_statements | DB query analysis when available (PostgreSQL) |

### Executive Business Metrics
| Feature | Description |
|---------|-------------|
| MRR (Monthly Recurring Revenue) | From active subscriptions × plan prices |
| ARR (Annual Recurring Revenue) | MRR × 12 |
| Churn rate | Canceled / (existing + new) over configurable period |
| LTV (Lifetime Value) | avg_revenue_per_customer × avg_lifespan_months |
| Trial conversion funnel | Trials → converted → expired → still trialing |
| Active orgs by tier | Breakdown by Free/Pro/Business |
| Growth rate | Month-over-month user and revenue growth |
| Revenue trend | 180-day monthly revenue chart |

### Demo Environment
| Feature | Description |
|---------|-------------|
| Demo mode flag | `DEMO_MODE=true` env var toggles safety middleware |
| Safety middleware | Blocks destructive POST/PUT/DELETE for non-admin users |
| Demo banner | Amber warning strip visible on all pages |
| 4 demo accounts | admin (Business), demo (Pro), manager (Admin role), member (Member role) |
| Seed data | Orgs, subscriptions, invoices, feature flags, extra users |
| Reset capability | Admin-only "Reset Demo Data" button — full teardown and reseed |
| Demo CLI | `flask seed-demo-data` for easy initialization |

### Admin Dashboard
| Feature | Description |
|---------|-------------|
| User management | List, detail, ban/unban, disable/enable |
| Organization management | List orgs with member count, subscription tier, status |
| Subscription overview | All subscriptions with status, plan, period |
| Payment history | All invoices with amounts, status, PDF links |
| Audit log viewer | Searchable by actor, action, resource type, date range |
| Cache management | View cache stats, clear keys, invalidate patterns |
| Job queue | View RQ jobs, cancel jobs, enqueue new jobs |
| API usage stats | Request counts, response times, endpoint breakdown |
| Trial conversion analytics | Signup-to-trial-to-paid funnel metrics |
| User impersonation | Admin can impersonate any user with audit trail |
| **Performance dashboard** | Avg/P95/P99 response times, slowest endpoints, cache stats |
| **Business metrics** | MRR, ARR, churn rate, LTV, trial conversion, revenue trend |
| **Webhook admin** | Dead-letter queue, failed event retry |

### Analytics
| Feature | Description |
|---------|-------------|
| User growth chart | Daily/weekly new user registrations |
| Revenue/MRR tracking | Monthly recurring revenue over time |
| Churn rate | Calculated from subscription cancellations |
| Subscription distribution | Free vs Pro vs Business breakdown |
| Dashboard stats | Total users, active users, total orgs, MRR, churn rate |
| Trial conversion | Signup -> trial start -> paid conversion funnel |
| Chart.js visualizations | Interactive charts with JSON data endpoints |

### REST API
| Feature | Description |
|---------|-------------|
| Versioned API | `/api/v1` with API key authentication |
| API key management | Create, list, revoke (prefix `sf_`) |
| Scoped permissions | Read/write/admin/full scope presets |
| Usage limits | Per-plan daily limits with 429 enforcement |
| Rate limiting | Per-key rate limits with Redis backend |
| Usage tracking | Log every request with response time, status code |
| OpenAPI documentation | Interactive Swagger UI at `/apidocs/` |
| Endpoints | User profile, organizations, members, admin stats |

### Background Jobs
| Feature | Description |
|---------|-------------|
| RQ workers | Redis Queue with dedicated `saasforge-jobs` queue |
| Email jobs | Async email sending, verification emails |
| Analytics processing | Periodic data aggregation |
| Cleanup jobs | Expired invitations, stale tokens |
| Weekly reports | Admin digest generation |
| Job monitoring | JobRecord model, status tracking, cancel support |
| Job scheduling | RQ Scheduler for recurring jobs |
| Admin job UI | View queue, cancel jobs, manually enqueue |

### Infrastructure & DevOps
| Feature | Description |
|---------|-------------|
| Docker support | Multi-stage Dockerfile for production |
| Docker Compose | 5 services: web, worker, scheduler, PostgreSQL, Redis |
| Production Compose | Adds Nginx reverse proxy |
| CI/CD pipeline | GitHub Actions: lint -> test -> build -> deploy |
| Security scanning | Bandit (SAST), Safety (dependencies), Gitleaks (secrets) |
| Railway deployment | `railway.json` configured |
| Health monitoring | `GET /health` and `GET /health/detailed` with 5 checks |
| Prometheus endpoint | `GET /metrics` for external monitoring |
| Sentry error tracking | Configurable DSN |
| Dark mode | Full light/dark theme, cookie-persisted |
| Responsive design | Mobile-first with TailwindCSS |
| HTMX + Alpine.js | Dynamic UI without full page reloads |

### Notifications
| Feature | Description |
|---------|-------------|
| In-app notifications | HTMX-powered notification center |
| Email notifications | SendGrid with dev console fallback |
| Notification types | Info, Success, Warning, Error |
| Unread count badge | Global header indicator |
| Mark as read | Individual or bulk mark read |

### Audit Logging
| Feature | Description |
|---------|-------------|
| All critical actions logged | Authentication, org changes, billing, admin actions |
| Decorator-based | `@audit_log(action, resource_type)` |
| Searchable | By actor, action, resource type, date range |
| Rich metadata | IP address, user agent, structured metadata JSON |

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | Python | 3.13+ |
| | Flask | 3.x |
| | SQLAlchemy | 2.0 |
| | Alembic | -- |
| **Frontend** | HTMX | 2.x |
| | Alpine.js | 3.x |
| | TailwindCSS (CDN) | 3.x |
| | Chart.js | 4.x |
| **Database** | PostgreSQL (production) | 16+ |
| | SQLite (development) | -- |
| **Cache & Queue** | Redis | 7+ |
| **Payments** | Stripe (Checkout, Customer Portal, Webhooks) | -- |
| **Authentication** | bcrypt (Werkzeug) | -- |
| | Flask-Login | -- |
| | Authlib (Google OAuth) | -- |
| **Background Tasks** | RQ (Redis Queue) | -- |
| **Email** | SendGrid | -- |
| **Infrastructure** | Docker, Docker Compose, Nginx | -- |
| | Gunicorn + gevent | -- |
| **CI/CD** | GitHub Actions | -- |
| **Deployment** | Railway, VPS | -- |
| **Monitoring** | Structured JSON logging, Prometheus metrics, Sentry SDK | -- |
| **API Docs** | Flasgger + APISpec | -- |
| **2FA** | pyotp | -- |
| **Static Analysis** | Ruff, mypy | -- |
| **Security Scanning** | Bandit, Safety, Gitleaks | -- |
| **Testing** | pytest, coverage | -- |

---

## Quick Start

### Prerequisites
- Python 3.13+
- Git

### Option 1: Local with SQLite (no external services)

```bash
git clone https://github.com/aldindugolli/SaaSForge.git
cd SaaSForge
python -m venv venv

# Activate:
# Linux/macOS: source venv/bin/activate
# Windows:      venv\Scripts\activate

pip install -r requirements.txt
python run.py       # Auto-detects SQLite, no env vars needed
```

Then in another terminal:

```bash
flask db upgrade    # Apply all 8 migration revisions
flask seed-data     # Creates admin + demo users
```

Open http://localhost:5000
- **Admin:** admin@saasforge.com / Admin123!
- **Demo:** demo@saasforge.com / Demo123!

> `python run.py` auto-selects SQLite when `DATABASE_URL` is not set to a PostgreSQL URI. CSRF and rate limiting are disabled in this mode; emails are logged to console.
> On first run, run `flask db upgrade` to create all tables (8 revisions: initial schema → webhook tables). PostgreSQL-only features (JSONB, GIN, FTS, materialized views) gracefully no-op on SQLite.

### Option 2: Docker (full stack with PostgreSQL + Redis)

```bash
docker-compose up -d
docker-compose exec web flask db upgrade
docker-compose exec web flask seed-data
```

### Option 3: Local with PostgreSQL

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/saasforge
export REDIS_URL=redis://localhost:6379/0
flask db upgrade
flask seed-data
python run.py
```

---

## Project Structure

```
saasforge/
├── app/
│   ├── __init__.py              # Application factory (create_app)
│   │                           # init_observability() - correlation IDs, metrics, JSON logging
│   │   # ├── init_database_extensions() - JSONB, GIN indexes, FTS, materialized views
│   │   # └── init_demo_environment() - demo safety middleware
│   ├── jobs.py                  # 5 background job definitions
│   │
│   ├── admin/                   # Admin dashboard (20+ routes)
│   │   └── routes.py            # User/org mgmt, audit, cache, jobs, analytics,
│   │                            # performance, business_metrics, webhooks
│   ├── analytics/               # Analytics (5 routes)
│   │   └── routes.py            # Chart data endpoints + dashboard
│   ├── api/                     # REST API v1 (10 routes)
│   │   └── routes.py            # API key auth, org/member endpoints
│   ├── auth/                    # Authentication (10 routes)
│   │   └── routes.py            # Login, register, OAuth, 2FA, password reset
│   ├── billing/                 # Subscription billing (5 routes)
│   │   └── routes.py            # Checkout, portal, webhooks, history
│   ├── core/                    # Core infrastructure
│   │   ├── cli.py               # 5 Flask CLI commands
│   │   ├── config.py            # Production + Local config classes
│   │   ├── context_processors.py # Global template context
│   │   ├── error_handlers.py    # 5 error handlers (400/403/404/429/500)
│   │   ├── extensions.py        # Flask extensions (db, login, csrf, etc.)
│   │   ├── models.py            # 17 models + 5 enums (incl. CustomerWebhookEndpoint, WebhookDelivery, WebhookEventLog)
│   │   └── routes.py            # Core routes (15 routes: +health/detailed, /metrics)
│   ├── db/                      # PostgreSQL optimization module
│   │   └── __init__.py          # JSONB helpers, GIN/expression indexes, FTS triggers, materialized views
│   ├── notifications/           # In-app notifications (5 routes)
│   │   └── routes.py
│   ├── organizations/           # Team management (12 routes)
│   │   └── routes.py
│   ├── security/                # Security center (1 route)
│   │   └── routes.py
│   ├── webhooks/                # Customer webhook management (8 routes)
│   │   └── routes.py            # CRUD, toggle, test, delivery history, retry
│   │
│   ├── services/                # Business logic layer (20 files)
│   │   ├── analytics_service.py
│   │   ├── api_platform.py      # APIPermission enum, SCOPE_PERMISSIONS, UsageLimitService, create_api_key(), api_auth_required
│   │   ├── audit_service.py
│   │   ├── auth_service.py
│   │   ├── base.py              # BaseService[T] + 4 error classes
│   │   ├── billing_service.py
│   │   ├── business_metrics.py  # MRR, ARR, churn, LTV, trial conversion, growth rate, revenue trend
│   │   ├── cache_service.py
│   │   ├── decorators.py        # 6 route decorators
│   │   ├── demo_service.py      # DEMO_ACCOUNTS, DemoMiddleware, create_seed_data(), reset_demo_data()
│   │   ├── email_service.py
│   │   ├── entitlement_service.py
│   │   ├── impersonation_service.py
│   │   ├── job_scheduler.py
│   │   ├── notification_service.py
│   │   ├── org_service.py
│   │   ├── performance_service.py # PerformanceMetrics, @monitor_query, get_slow_queries, cache analytics
│   │   ├── role_service.py
│   │   ├── session_service.py
│   │   ├── two_factor_service.py
│   │   └── webhook_service.py   # StripeWebhookProcessor + CustomerWebhookService (register, deliver, retry)
│   │
│   ├── templates/               # Jinja2 templates (55+ files)
│   │   ├── base.html            # Base layout (Tailwind CDN, dark mode, HTMX, Alpine, demo banner)
│   │   ├── webhooks/            # index.html (endpoint mgmt), deliveries.html (delivery history)
│       │   ├── admin/               # 16 admin templates, all extending base.html
│   │   ├── components/
│   │   │   ├── navbar.html
│   │   │   ├── sidebar.html     # Full admin nav with 12 links
│   │   │   └── demo_banner.html # Demo mode amber warning strip
│   │   └── ... (47 other templates)
│   │
│   └── observability.py         # StructuredFormatter, CorrelationMiddleware, MetricsRegistry, HealthStatus
│
├── tests/                       # 98 pytest tests
│   ├── conftest.py
│   ├── integration/
│   │   ├── test_admin_routes.py # 15 auth-required checks
│   │   ├── test_auth_routes.py  # Auth flow tests
│   │   └── test_webhooks_routes.py # 9 auth-required checks
│   └── unit/
│       ├── test_auth_service.py
│       ├── test_business_metrics.py # 7 metric validation tests
│       ├── test_cache_service.py
│       ├── test_demo_service.py # Seed data, demo mode, allowed actions
│       ├── test_impersonation_service.py
│       ├── test_job_scheduler.py
│       ├── test_models.py
│       ├── test_org_service.py
│       └── test_performance_service.py # Avg response, slow queries, decorator, cache analytics
│
├── migrations/                  # Alembic migrations (8 revisions)
│   └── versions/
│       ├── cb91a1ee165e_initial_schema.py
│       ├── 4626fbde516c_add_job_records_table.py
│       ├── 8757bf2ba419_add_user_sessions_table.py
│       ├── 78e2f1f46958_add_api_request_logs_table.py
│       ├── 2d1b9e4ca700_add_2fa_fields_to_users.py
│       ├── 29131e9dc678_add_brand_color_to_organizations.py
│       ├── 3a1b2c3d4e5f_postgresql_optimizations.py   # JSONB, GIN, FTS, materialized views
│       └── 4b2c3d4e5f6a_add_webhook_tables.py         # CustomerWebhookEndpoint, WebhookDelivery, WebhookEventLog
│
├── docs/
│   ├── architecture.md          # Layered architecture, observability, PostgreSQL features, webhooks
│   ├── api.md                   # All API endpoints including webhook management
│   ├── development.md           # Local setup, demo env, observability, performance
│   ├── deployment.md            # Docker, Railway, env vars for all features
│   ├── diagrams.md              # Mermaid diagrams (system, auth, billing, multi-tenant, jobs, API lifecycle, observability, webhooks)
│   └── adr/index.md             # Architecture Decision Records
│
├── Dockerfile                   # Multi-stage production build
├── docker-compose.yml           # Dev: web + worker + scheduler + db + redis
├── docker-compose.prod.yml      # Production: + nginx
├── requirements.txt             # 86+ pinned dependencies
├── pyproject.toml               # Project config + tool configs
├── pytest.ini                   # Test configuration
├── railway.json                 # Railway deployment config
├── run.py                       # Dev entrypoint (auto SQLite)
├── wsgi.py                      # Production WSGI entrypoint
└── .env.example                 # 55+ env var references
```

---

## Architecture

### Layered Architecture

```
+-------------------------------------------------------+
|                   Presentation                       |
|  Blueprints (routes) -> HTTP handling, validation,    |
|                        template rendering            |
+-------------------------------------------------------+
|                   Service Layer                      |
|  20 service classes -> business logic, queries,       |
|                        cross-cutting concerns        |
+-------------------------------------------------------+
|                   Data Layer                         |
|  17 SQLAlchemy models -> DB access, relationships     |
+-------------------------------------------------------+
|                   Infrastructure                     |
|  Stripe API, SendGrid, Redis, RQ, filesystem,        |
|  Prometheus, structured logging, correlation IDs    |
+-------------------------------------------------------+
```

**Key principles:**
- Routes are thin (~30-50 lines): parse input, call service, handle result, render template or redirect
- Services encapsulate all business logic, database operations, and side effects (caching, auditing, notifications, metric recording)
- Services raise typed exceptions (`ValidationError`, `NotFoundError`, `PermissionError`, `ServiceError`)
- Controllers catch exceptions and render appropriate responses

### Application Factory

`create_app()` in `app/__init__.py` orchestrates initialization in order:

1. `initialize_extensions(app)` — SQLAlchemy, Migrate, LoginManager, CSRF, Limiter, RQ, Swagger
2. `register_blueprints(app)` — 10 blueprints (added `webhooks_bp`)
3. `register_error_handlers(app)` — 5 error handlers
4. `register_context_processors(app)` — global template variables
5. `register_template_filters(app)` — `humanize`, `currency`, `compact`, `pct_change`
6. `register_shell_context(app)` — db, all models for `flask shell`
7. `register_cli_commands(app)` — 5 CLI commands (added `seed-demo-data`)
8. `register_scheduled_jobs(app)` — recurring job setup
9. `init_oauth(app)` — Google OAuth provider
10. **`init_observability(app)`** — structured logging, CorrelationMiddleware, MetricsMiddleware
11. **`init_database_extensions(app)`** — JSONB helpers, GIN indexes, FTS, materialized views (PG only)
12. **`init_demo_environment(app)`** — DemoMiddleware safety guards

### Multi-Tenancy

```
Organization (tenant boundary)
+-- Owner    -- full access, billing, delete org, transfer ownership
+-- Admin    -- manage members, roles, settings
+-- Member   -- basic access
```

- `Organization` is the tenant boundary
- `Membership` links `User` <-> `Organization` with a `role` (owner/admin/member)
- All domain models reference `organization_id` for data isolation
- Queries always filter by `organization_id`
- Users can belong to multiple orgs; active org tracked via `is_current`

### Caching Strategy

- `RedisCache` wraps Redis with automatic in-memory fallback (backed by a dict)
- Analytics cached with 5-minute TTL under `analytics:*` namespace
- Cache invalidated on data mutations (user registration, org changes, subscription updates)
- Pattern-based invalidation (`analytics:*`) — coarse but correct

---

## Observability

### Correlation IDs

Every request receives a `X-Correlation-ID` header (generated or forwarded). The ID flows through:

```
Browser → Flask → Service → DB Query → Job → Webhook Delivery
```

Stored in a `ContextVar` for thread-safe access across the request lifecycle.

### Structured Logging

All logs emit as JSON lines with consistent fields:

```json
{"timestamp": "2026-06-22T20:08:34+00:00", "level": "INFO",
 "logger": "app", "message": "Observability initialized",
 "module": "__init__", "function": "init_observability",
 "line": 172, "correlation_id": "a1b2c3d4e5f6a7b8"}
```

### Prometheus Metrics

Available at `GET /metrics`:

| Metric | Type | Labels |
|--------|------|--------|
| `http_request_duration_ms` | Histogram | method, endpoint |
| `http_requests_total` | Counter | method, endpoint, status |
| `http_errors_total` | Counter | method, endpoint, status |
| `db_query_duration_ms` | Histogram | — |
| `db_queries_total` | Counter | — |
| `cache_hits_total` / `cache_misses_total` | Counter | operation |
| `worker_job_duration_ms` | Histogram | job, status |
| `queue_operations_total` | Counter | operation, queue |

### Health Checks

| Endpoint | Checks |
|----------|--------|
| `GET /health` | Database, cache, queue, webhook events |
| `GET /health/detailed` | Database, Redis, Queue, Stripe, Email |

---

## Services

| Service | File | Responsibility |
|---------|------|----------------|
| **BaseService[T]** | `base.py` | Generic CRUD base class |
| **AuthService** | `auth_service.py` | Authentication, password management, email verification |
| **AnalyticsService** | `analytics_service.py` | Dashboard stats, growth charts, MRR, churn, trial conversion |
| **AuditService** | `audit_service.py` | Audit logging + `@audit_log` decorator |
| **BillingService** | `billing_service.py` | Stripe Checkout, Customer Portal, webhook processing |
| **CacheService** | `cache_service.py` | Redis caching with in-memory fallback |
| **EmailService** | `email_service.py` | SendGrid email with dev console fallback |
| **EntitlementService** | `entitlement_service.py` | Plan-based feature gating |
| **ImpersonationService** | `impersonation_service.py` | Admin user impersonation with audit trail |
| **JobScheduler** | `job_scheduler.py` | RQ job scheduling with monitoring |
| **NotificationService** | `notification_service.py` | In-app notification system |
| **OrganizationService** | `org_service.py` | Organization CRUD, member management, invitations |
| **RoleService** | `role_service.py` | Granular RBAC + `@require_permission` decorator |
| **SessionService** | `session_service.py` | User session tracking |
| **TwoFactorService** | `two_factor_service.py` | TOTP 2FA (pyotp) |
| **StripeWebhookProcessor** | `webhook_service.py` | Idempotent Stripe webhook processing, dead-letter queue |
| **CustomerWebhookService** | `webhook_service.py` | Customer endpoint management, HMAC delivery, retry |
| **PerformanceMetrics** | `performance_service.py` | P95/P99, slowest endpoints, cache analytics |
| **BusinessMetricsService** | `business_metrics.py` | MRR, ARR, churn, LTV, trial conversion, growth rate |
| **DemoService** | `demo_service.py` | Demo middleware, seed data, reset |
| **UsageLimitService** | `api_platform.py` | Per-plan API usage limits |
| **APIPermission** (enum) | `api_platform.py` | 12 scoped permissions + presets |

### Route Decorators (`app/services/decorators.py`)

| Decorator | Checks |
|-----------|--------|
| `@require_role(role)` | User has at least the given role in current org |
| `@require_owner` | User is the owner of current org |
| `@require_admin` | User is a site admin (`is_admin`) |
| `@require_email_verified` | User has verified their email |
| `@require_active_subscription` | Current org has an active subscription |
| `@org_required` | User has a current organization selected |

### Error Classes (`app/services/base.py`)

| Exception | HTTP Code | When Raised |
|-----------|-----------|-------------|
| `ServiceError` | 400 | Base service exception |
| `ValidationError(ServiceError)` | 400 | Invalid input data |
| `NotFoundError(ServiceError)` | 404 | Resource not found |
| `PermissionError(ServiceError)` | 403 | Insufficient permissions |

---

## Models

### Enums

| Enum | Values |
|------|--------|
| `Role` | `OWNER`, `ADMIN`, `MEMBER` |
| `SubscriptionStatus` | `ACTIVE`, `TRIALING`, `PAST_DUE`, `CANCELED`, `INCOMPLETE`, `INCOMPLETE_EXPIRED`, `UNPAID` |
| `PlanType` | `FREE`, `PRO`, `BUSINESS` |
| `APIKeyType` | `TEST`, `LIVE` |
| `NotificationType` | `INFO`, `SUCCESS`, `WARNING`, `ERROR` |
| `WebhookStatus` | `pending`, `processing`, `completed`, `failed`, `dead\_letter` |
| `WebhookDeliveryStatus` | `pending`, `delivered`, `failed`, `retrying` |

### User (`users`)
UUID PK, email (unique), bcrypt password hash, profile fields, email verification, admin flag, ban support, login tracking, Google OAuth ID, TOTP 2FA fields, password reset token.

**Relationships:** `memberships`, `owned_organizations`, `notifications`, `api_keys`, `audit_logs`

### Organization (`organizations`)
UUID PK, name, unique slug, brand color, timezone, owner (FK -> User), subscription tier, trial end, max members.

**Relationships:** `memberships`, `subscriptions`, `invitations`, `feature_flags`, `webhook_endpoints`

### Membership (`memberships`)
User-Org join table with role (owner/admin/member), `is_current` flag.

### Subscription (`subscriptions`)
Org-scoped with Stripe IDs, plan, status, period dates. Property `is_active` checks status in (ACTIVE, TRIALING).

### Invoice (`invoices`)
Org-scoped, amount_due/amount_paid in cents, status, Stripe ID, PDF URL.

### CustomerWebhookEndpoint (`customer_webhook_endpoints`)
Org-scoped, URL, HMAC secret, subscribed event types (JSON array), active flag, delivery tracking.

### WebhookDelivery (`webhook_deliveries`)
Per-endpoint delivery attempts: event_type, payload (JSON), status, status_code, response_body, attempt_count, timestamps.

### WebhookEventLog (`webhook_event_logs`)
Stripe webhook idempotency: stripe_event_id (unique), type, status, error_message.

### Other Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `ApiRequestLog` | `api_request_logs` | user_id, org_id, api_key_id, method, endpoint, status_code, response_time_ms |
| `APIKey` | `api_keys` | user_id, org_id, name, key_prefix, key_hash, permissions (JSON), is_active, usage_count |
| `AuditLog` | `audit_logs` | actor_id, org_id, action, resource_type, resource_id, metadata (JSON) |
| `FeatureFlag` | `feature_flags` | name, key, enabled, scope, org_id |
| `Invitation` | `invitations` | org_id, email, token, role, expires_at |
| `JobRecord` | `job_records` | name, queue, status, rq_job_id, result, error |
| `Notification` | `notifications` | user_id, type, title, message, link, is_read |
| `PaymentEvent` | `payment_events` | org_id, stripe_event_id, type, status, data (JSON) |
| `UserSession` | `user_sessions` | user_id, session_id, browser, OS, IP, is_current |

---

## Routes & Blueprints

### Blueprint Registration

| Blueprint | Variable | URL Prefix | Route Count |
|-----------|----------|------------|-------------|
| Core | `core_bp` | `/` | 15 |
| Auth | `auth_bp` | `/auth` | 10 |
| Organizations | `org_bp` | `/org` | 12 |
| Billing | `billing_bp` | `/billing` | 6 |
| Admin | `admin_bp` | `/admin` | 20+ |
| Analytics | `analytics_bp` | `/analytics` | 5 |
| Notifications | `notifications_bp` | `/notifications` | 5 |
| API | `api_bp` | `/api/v1` | 10 |
| Security | `security_bp` | `/security` | 1 |
| Webhooks | `webhooks_bp` | `/webhooks` | 8 |

### Key Routes

**Core (`/`):** `GET /` (landing/dashboard), `GET /settings`, `GET /sessions`, `GET /2fa/setup`, `GET /health`, `GET /health/detailed`, `GET /metrics`

**Auth (`/auth`):** `GET/POST /register`, `GET/POST /login`, `GET /logout`, `GET /2fa-challenge`, `GET /verify-email/<token>`, `GET/POST /forgot-password`, `GET /reset-password/<token>`, `GET /google/login`, `GET /google/callback`

**Admin (`/admin`):** `GET /` (overview), `GET /users`, `GET /users/<id>`, `POST /users/<id>/ban|unban|disable`, `GET /organizations`, `GET /organizations/<id>`, `GET /subscriptions`, `GET /payments`, `GET /audit-logs`, `GET /analytics`, `GET /cache`, `GET /jobs`, `POST /jobs/<id>/cancel`, `POST /jobs/enqueue`, `GET /api-stats`, `GET /trial-analytics`, `POST /impersonate`, **`GET /performance`**, **`GET /business-metrics`**, **`GET /webhooks`**, **`POST /webhooks/retry`**, **`POST /reset-demo`**

**Webhooks (`/webhooks`):** `GET /` (endpoint list), `POST /create`, `POST /<id>/update`, `POST /<id>/toggle`, `POST /<id>/delete`, `POST /<id>/test`, `GET /<id>/deliveries`, `POST /deliveries/<id>/retry`

**API (`/api/v1`):** `GET /` (status), `GET /me`, `GET /organizations`, `GET /organizations/<id>`, `GET /organizations/<id>/members`, `GET /keys`, `POST /keys`, `POST /keys/<id>/revoke`, `GET /admin/stats`

---

## Background Jobs

### Job Definitions (`app/jobs.py`)

| Function | Queue | Schedule | Description |
|----------|-------|----------|-------------|
| `send_email_job(to, subject, html_body)` | saasforge-jobs | On-demand | Send transactional email |
| `send_verification_email_job(user_id, email, verify_url)` | saasforge-jobs | On-demand | Send email verification |
| `process_analytics_job(organization_id)` | saasforge-jobs | Hourly | Process analytics data |
| `cleanup_expired_data_job()` | saasforge-jobs | Daily (midnight) | Remove expired invitations and tokens |
| `generate_weekly_report_job()` | saasforge-jobs | Weekly (Mon 9am) | Generate admin digest report |

### Webhook Async Delivery

The `CustomerWebhookService` performs synchronous HTTP delivery. For high-throughput production use, enqueue deliveries via RQ.

---

## API Reference

### Authentication

API endpoints use `X-API-Key` header authentication. Keys created via UI or API have scoped permissions.

```bash
curl -H "X-API-Key: sf_your_api_key" http://localhost:5000/api/v1/me
```

### Scoped Permissions

| Scope | Grants |
|-------|--------|
| `read` | read:users, read:organizations, read:billing, webhooks:read, audit:read |
| `write` | read scope + write:organizations, write:members, webhooks:write, api_keys:write |
| `admin` | admin:analytics, admin:users |
| `full` | All 12 permission scopes |

### Usage Limits

| Plan | Daily Limit | Rate/Minute |
|------|-------------|-------------|
| Free | 1,000 | 10 |
| Pro | 10,000 | 60 |
| Business | 100,000 | 300 |

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/` | None | API status and version |
| GET | `/api/v1/me` | API Key | Current user profile |
| GET | `/api/v1/organizations` | API Key | List user's organizations |
| GET | `/api/v1/organizations/:id` | API Key | Organization details |
| GET | `/api/v1/organizations/:id/members` | API Key | Members list |
| GET | `/api/v1/keys` | Session | List API keys |
| POST | `/api/v1/keys` | Session | Create API key |
| POST | `/api/v1/keys/:id/revoke` | Session | Revoke API key |
| GET | `/api/v1/admin/stats` | API Key + Admin | Admin dashboard stats |

### Error Responses

All API errors follow a consistent format with correlation IDs:

```json
{
  "error": "insufficient_permissions",
  "message": "Requires 'admin:analytics' permission",
  "required": "admin:analytics",
  "correlation_id": "a1b2c3d4e5f6a7b8"
}
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `flask seed-data` | Seed admin@saasforge.com and demo@saasforge.com |
| **`flask seed-demo-data`** | Seed 4 demo accounts with orgs, subscriptions, invoices, feature flags |
| `flask create-admin <email> <password> <name>` | Create an admin user |
| `flask list-routes` | Display all registered routes |
| `flask schedule-jobs` | Register recurring jobs with RQ Scheduler |
| `flask shell` | Interactive shell with db, all models pre-imported |

---

## Testing

### Test Suite

```bash
pytest                           # All 98+ tests
pytest -v                        # Verbose output
pytest -k "performance"          # Filter by keyword
pytest -m unit                   # Unit tests only
pytest -m integration            # Integration tests only
```

### Test Structure

```
tests/
├── conftest.py                  # App, client, db, registered_user, organization fixtures
├── integration/
│   ├── test_admin_routes.py     # 15 auth-required checks for admin pages
│   ├── test_auth_routes.py      # Auth flow integration tests
│   └── test_webhooks_routes.py  # 9 auth-required checks for webhook endpoints
└── unit/
    ├── test_auth_service.py     # Password validation, registration, login
    ├── test_business_metrics.py # MRR, ARR, churn, LTV, growth rate validation
    ├── test_cache_service.py    # Redis operations, invalidation, decorator
    ├── test_demo_service.py     # Seed data, demo mode, allowed actions
    ├── test_impersonation_service.py
    ├── test_job_scheduler.py    # Enqueue, schedule, cancel, recent jobs
    ├── test_models.py           # User, org, membership CRUD
    ├── test_org_service.py      # Org CRUD, member management
    └── test_performance_service.py # Avg response, slow queries, decorator, cache analytics
```

### Database

Tests use in-memory SQLite (`sqlite:///:memory:`) with session-scoped app and function-scoped transactional rollback.

---

## Deployment

### Railway

```bash
railway login
railway up
```

Set required environment variables in the Railway dashboard. A `railway.json` is included.

### Docker (VPS)

**Development:**
```bash
docker-compose up -d
```
5 services: web, worker, scheduler, PostgreSQL, Redis.

**Production:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```
Adds Nginx reverse proxy. Env vars from `.env.prod`.

### Manual

```bash
pip install -r requirements.txt
flask db upgrade
flask seed-data
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --timeout 120 wsgi:app
```

### Dockerfile

Multi-stage build (builder + runtime), Python 3.13-slim, gunicorn with 4 gevent workers, healthcheck every 30s.

---

## Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SECRET_KEY` | `change-this-in-production` | Yes | Flask secret key |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/saasforge` | Yes | PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | `10` | No | Connection pool size |
| `DATABASE_POOL_MAX_OVERFLOW` | `20` | No | Max pool overflow |
| `REDIS_URL` | `redis://localhost:6379/0` | Conditional | Redis (needed for sessions, rate limits, queue, cache) |
| `DEMO_MODE` | `false` | No | Enable demo environment safety middleware |
| `STRIPE_SECRET_KEY` | — | Yes | Stripe API secret key |
| `STRIPE_PUBLISHABLE_KEY` | — | Yes | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | — | Conditional (prod) | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` / `STRIPE_BUSINESS_PRICE_ID` | — | Yes | Stripe price IDs |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | — | Optional | Google OAuth |
| `SENDGRID_API_KEY` | — | Optional | SendGrid API key |
| `APP_NAME` / `APP_URL` / `APP_DOMAIN` | SaaSForge / localhost | No | Application metadata |
| `ADMIN_EMAIL` | `admin@saasforge.com` | No | Admin email address |
| `SENTRY_DSN` | — | Optional | Sentry error tracking DSN |
| `SESSION_TYPE` | `redis` | No | Session storage backend |
| `SESSION_COOKIE_SECURE` | `False` | No | Secure session cookie flag |
| `RATELIMIT_DEFAULT` | `100/hour` | No | Default rate limit |
| `UPLOAD_FOLDER` | `app/static/uploads` | No | File upload directory |
| `FEATURE_NEW_DASHBOARD` / `FEATURE_BETA_API` | `true` / `false` | No | Feature flags |

> **Local dev:** `python run.py` needs no env vars — auto-selects SQLite, disables CSRF/rate limiting, logs emails to console, uses filesystem sessions.

---

## Security

### Authentication & Sessions
- CSRF protection via Flask-WTF (disabled in dev for convenience)
- Session-based auth with HTTP-only cookies
- bcrypt password hashing (Werkzeug 6000 rounds)
- TOTP 2FA with authenticator apps + 10 backup codes
- Session tracking with browser/OS/IP identification
- Individual or bulk session revocation

### Access Control
- 13 granular permissions across 3 roles
- `@require_permission`, `@require_owner`, `@require_admin`, `@require_email_verified` decorators
- Admin-only routes for management features

### Input Validation
- Service-layer validation with typed exceptions
- Email format validation, password strength validation (8+ chars, upper/lower/number/special)
- Jinja2 auto-escaping, SQLAlchemy ORM injection protection

### API Security
- API key authentication with bcrypt-hashed keys in DB
- Scoped permissions (`read:users`, `write:orgs`, etc.)
- Per-plan daily usage limits with 429 enforcement
- API request logging for full audit trail

### Webhook Security
- Stripe webhook signature verification (idempotent via `WebhookEventLog`)
- Customer webhooks signed with HMAC-SHA256 (`X-Webhook-Signature` header)
- Unique secret per endpoint, shown only at creation

### Demo Environment Safety
- `DemoMiddleware` blocks destructive POST/PUT/DELETE for non-admin users
- Admin-only data reset capability
- Visual amber banner indicating demo mode

### Infrastructure
- Health monitoring (`GET /health`, `GET /health/detailed`)
- Prometheus metrics endpoint (`GET /metrics`)
- Correlation IDs across all services
- Sentry error tracking (configurable)
- Docker health checks
- Production Nginx reverse proxy
- CI/CD security scanning: Bandit (SAST), Safety (dependencies), Gitleaks (secrets)

### Audit Trail
- All critical actions logged to `audit_logs` table
- Tracks: actor, action, resource type, resource ID, IP, user agent, metadata
- `@audit_log` decorator for easy action logging
- Admin audit log viewer with search/filter

---

## Database Migrations

### Current Revisions (8 total)

| Revision | Description |
|----------|-------------|
| `cb91a1ee165e` | Initial schema |
| `4626fbde516c` | Add `job_records` table |
| `8757bf2ba419` | Add `user_sessions` table |
| `78e2f1f46958` | Add `api_request_logs` table |
| `2d1b9e4ca700` | Add 2FA fields to users |
| `29131e9dc678` | Add `brand_color` to organizations |
| `3a1b2c3d4e5f` | **PostgreSQL optimizations**: JSONB helpers, GIN indexes, FTS triggers, materialized views (mv_dashboard_stats, mv_revenue_by_month, mv_api_usage_stats) |
| `4b2c3d4e5f6a` | **Webhook tables**: customer_webhook_endpoints, webhook_deliveries, webhook_event_logs |

All 8 revisions are applied on `flask db upgrade`. PostgreSQL-only revisions (`3a1b2c3d4e5f`, `4b2c3d4e5f6a`) create tables on SQLite but skip PG-specific features (JSONB, GIN, FTS, materialized views).

### Commands

```bash
flask db upgrade          # Apply all 8 migration revisions
flask db downgrade <rev>  # Rollback to revision
flask db migrate -m "msg" # Generate new migration
flask db current          # Show current revision
flask db history          # Show migration history
```
