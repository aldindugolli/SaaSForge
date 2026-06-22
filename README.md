# SaaSForge

A production-ready Flask SaaS boilerplate with multi-tenant organizations, subscription billing, role-based access control, two-factor authentication, background jobs, REST API, and full admin dashboard. Designed for teams that want to launch a SaaS product without rebuilding the foundation.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
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
| Webhook handling | 6 event types (checkout completed, subscription lifecycle, invoice events) |
| Plan tiers | Free, Pro, Business with configurable Stripe price IDs |
| Trial periods | Configurable trial with conversion analytics |
| Payment history | Invoice records with PDF links |
| Entitlement checks | `@entitlement_required` decorator for feature gating |
| Plan-based limits | Max members, max projects per tier |

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

### Analytics
| Feature | Description |
|---------|-------------|
| User growth chart | Daily/weekly new user registrations |
| Revenue/MRR tracking | Monthly recurring revenue over time |
| Churn rate | Calculated from subscription cancellations |
| Subscription distribution | Free vs Pro vs Business breakdown |
| Dashboard stats | Total users, active users, total orgs, MRR, churn rate |
| Trial conversion | Signup → trial start → paid conversion funnel |
| Chart.js visualizations | Interactive charts with JSON data endpoints |

### REST API
| Feature | Description |
|---------|-------------|
| Versioned API | `/api/v1` with API key authentication |
| API key management | Create, list, revoke (prefix `sf_`) |
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
| CI/CD pipeline | GitHub Actions: lint → test → build → deploy |
| Security scanning | Bandit (SAST), Safety (dependencies), Gitleaks (secrets) |
| Railway deployment | `railway.json` configured |
| Health monitoring | `GET /health` endpoint with DB + cache status |
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
| | Alembic | — |
| | Marshmallow | — |
| | Pydantic | — |
| **Frontend** | HTMX | 2.x |
| | Alpine.js | 3.x |
| | TailwindCSS (CDN) | 3.x |
| | Chart.js | 4.x |
| **Database** | PostgreSQL (production) | 16+ |
| | SQLite (development) | — |
| **Cache & Queue** | Redis | 7+ |
| **Payments** | Stripe (Checkout, Customer Portal, Webhooks) | — |
| **Authentication** | bcrypt (Werkzeug) | — |
| | Flask-Login | — |
| | Authlib (Google OAuth) | — |
| **Background Tasks** | RQ (Redis Queue) | — |
| **Email** | SendGrid | — |
| **Infrastructure** | Docker | — |
| | Docker Compose | — |
| | Nginx (production) | Alpine |
| | Gunicorn + gevent | — |
| **CI/CD** | GitHub Actions | — |
| **Deployment** | Railway, VPS | — |
| **Monitoring** | Sentry SDK | — |
| **API Docs** | Flasgger + APISpec | — |
| **2FA** | pyotp | — |
| **Static Analysis** | Ruff, mypy | — |
| **Security Scanning** | Bandit, Safety, Gitleaks | — |
| **Testing** | pytest, factory-boy, coverage | — |

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
flask seed-data     # Creates admin + demo users
```

Open http://localhost:5000
- **Admin:** admin@saasforge.com / Admin123!
- **Demo:** demo@saasforge.com / Demo123!

> `python run.py` auto-selects SQLite (`LocalConfig`) when `DATABASE_URL` is not set to a PostgreSQL URI. CSRF and rate limiting are disabled in this mode; emails are logged to console.

### Option 2: Docker (full stack with PostgreSQL + Redis)

```bash
docker-compose up -d
docker-compose exec web flask db upgrade
docker-compose exec web flask seed-data
```

Opens on http://localhost:5000 with PostgreSQL and Redis running.

### Option 3: Local with PostgreSQL

Set environment variables:

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/saasforge
export REDIS_URL=redis://localhost:6379/0
```

Then:

```bash
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
│   ├── jobs.py                  # 5 background job definitions
│   │
│   ├── admin/                   # Admin dashboard (17 routes)
│   │   └── routes.py            # User/org mgmt, audit, cache, jobs, analytics
│   ├── analytics/               # Analytics (5 routes)
│   │   └── routes.py            # Chart data endpoints + dashboard
│   ├── api/                     # REST API v1 (10 routes)
│   │   └── routes.py            # API key auth, org/member endpoints
│   ├── auth/                    # Authentication (10 routes)
│   │   └── routes.py            # Login, register, OAuth, 2FA, password reset
│   ├── billing/                 # Subscription billing (5 routes)
│   │   └── routes.py            # Checkout, portal, webhooks, history
│   ├── core/                    # Core infrastructure
│   │   ├── __init__.py
│   │   ├── cli.py               # 4 Flask CLI commands
│   │   ├── config.py            # Production Config class (130 lines)
│   │   ├── context_processors.py # Global template context
│   │   ├── error_handlers.py    # 5 error handlers (400/403/404/429/500)
│   │   ├── extensions.py        # Flask extensions (db, login, csrf, etc.)
│   │   ├── local_config.py      # Dev config (SQLite, no CSRF/rate limit)
│   │   ├── models.py            # 15 models + 5 enums (494 lines)
│   │   └── routes.py            # Core routes (13 routes)
│   ├── notifications/           # In-app notifications (5 routes)
│   │   └── routes.py
│   ├── organizations/           # Team management (12 routes)
│   │   └── routes.py
│   ├── security/                # Security center (1 route)
│   │   └── routes.py
│   │
│   ├── services/                # Business logic layer (16 files)
│   │   ├── __init__.py
│   │   ├── analytics_service.py # AnalyticsService
│   │   ├── audit_service.py     # AuditService + @audit_log decorator
│   │   ├── auth_service.py      # AuthService
│   │   ├── base.py              # BaseService[T] + 4 error classes
│   │   ├── billing_service.py   # BillingService (Stripe)
│   │   ├── cache_service.py     # RedisCache + CacheService
│   │   ├── decorators.py        # 6 route decorators
│   │   ├── email_service.py     # EmailService (SendGrid)
│   │   ├── entitlement_service.py # EntitlementService
│   │   ├── impersonation_service.py # ImpersonationService
│   │   ├── job_scheduler.py     # JobScheduler + JobMonitorHooks
│   │   ├── notification_service.py # NotificationService
│   │   ├── org_service.py       # OrganizationService
│   │   ├── role_service.py      # Permission system + RoleService
│   │   ├── session_service.py   # SessionService
│   │   └── two_factor_service.py # TwoFactorService
│   │
│   ├── static/
│   │   └── js/
│   │       └── main.js          # Client-side JS
│   │
│   └── templates/               # Jinja2 templates (47 files)
│       ├── base.html            # Base layout (Tailwind CDN, dark mode, HTMX, Alpine)
│       ├── landing.html         # Landing page
│       ├── dashboard.html       # Main dashboard
│       ├── settings.html        # User profile settings
│       ├── sessions.html        # Active sessions
│       ├── two_factor_setup.html # 2FA setup
│       ├── auth/                # login, register, forgot/reset password, 2FA challenge
│       ├── admin/               # 14 admin templates
│       ├── analytics/           # Analytics dashboard
│       ├── billing/             # Billing overview + payment history
│       ├── components/          # navbar, sidebar, toast, notification_list, error_toast
│       ├── emails/              # welcome, verify_email, password_reset, invitation
│       ├── errors/              # 400, 403, 404, 429, 500
│       ├── notifications/       # Notification center
│       ├── organizations/       # create, settings, members, activity
│       └── security/            # Security center dashboard
│
├── tests/                       # 55+ pytest tests
│   ├── conftest.py              # Fixtures (app, client, db, auth)
│   ├── integration/             # Route integration tests
│   │   └── test_auth_routes.py  # Auth flow tests
│   └── unit/                    # Unit tests
│       ├── test_auth_service.py # Password validation, registration, login
│       └── test_base.py         # BaseService CRUD tests
│
├── migrations/                  # Alembic migrations (6 revisions)
│   ├── alembic.ini
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── cb91a1ee165e_initial_schema.py
│       ├── 4626fbde516c_add_job_records_table.py
│       ├── 8757bf2ba419_add_user_sessions_table.py
│       ├── 78e2f1f46958_add_api_request_logs_table.py
│       ├── 2d1b9e4ca700_add_2fa_fields_to_users.py
│       └── 29131e9dc678_add_brand_color_to_organizations.py
│
├── docker/
│   └── nginx.conf               # Production Nginx config
├── .github/workflows/
│   └── ci.yml                   # CI/CD pipeline
├── scripts/                     # Utility scripts
├── docs/
│   └── adr/
│       └── index.md             # Architecture Decision Records (3 ADRs)
│
├── Dockerfile                   # Multi-stage production build
├── docker-compose.yml           # Dev: web + worker + scheduler + db + redis
├── docker-compose.prod.yml      # Production: + nginx
├── requirements.txt             # 86 pinned dependencies
├── pyproject.toml               # Project config + tool configs
├── pytest.ini                   # Test configuration
├── railway.json                 # Railway deployment config
├── run.py                       # Dev entrypoint (auto SQLite)
├── wsgi.py                      # Production WSGI entrypoint
└── .env.example                 # 55 env var references
```

---

## Architecture

### Service Layer Pattern

The application follows a **thin controller, fat service** architecture:

```
┌─────────────────────────────────────────────────────┐
│                   Presentation                       │
│  Blueprints (routes) → HTTP handling, validation,    │
│                        template rendering            │
├─────────────────────────────────────────────────────┤
│                   Service Layer                      │
│  16 service classes → business logic, queries,       │
│                       cross-cutting concerns         │
├─────────────────────────────────────────────────────┤
│                   Data Layer                         │
│  15 SQLAlchemy models → DB access, relationships     │
├─────────────────────────────────────────────────────┤
│                   Infrastructure                     │
│  Stripe API, SendGrid, Redis, RQ, filesystem         │
└─────────────────────────────────────────────────────┘
```

**Key principles:**
- Routes are thin (~30-50 lines): parse input, call service, handle result, render template or redirect
- Services encapsulate all business logic, database operations, and side effects (caching, auditing, notifications)
- Services raise typed exceptions (`ValidationError`, `NotFoundError`, `PermissionError`, `ServiceError`)
- Controllers catch exceptions and render appropriate responses (flash messages, error templates, JSON errors)
- Same service layer serves both HTML routes and JSON API endpoints

### Multi-Tenancy

```
Organization (tenant boundary)
├── Owner    — full access, billing, delete org, transfer ownership
├── Admin    — manage members, roles, settings
└── Member   — basic access
```

- `Organization` is the tenant boundary
- `Membership` links `User` ↔ `Organization` with a `role` (owner/admin/member)
- All domain models reference `organization_id` for data isolation
- Queries always filter by `organization_id`
- Users can belong to multiple orgs; active org tracked via `is_current` flag on Membership

### Caching Strategy

- `RedisCache` wraps Redis with automatic in-memory fallback (backed by a dict)
- Analytics cached with 5-minute TTL under `analytics:*` namespace
- Cache invalidated on data mutations (user registration, org changes, subscription updates)
- Pattern-based invalidation (`analytics:*`) — coarse but correct

### Application Factory

`create_app()` in `app/__init__.py` orchestrates initialization:

1. `initialize_extensions(app)` — SQLAlchemy, Migrate, LoginManager, CSRF, Limiter, RQ, Swagger
2. `register_blueprints(app)` — 9 blueprints with URL prefixes
3. `register_error_handlers(app)` — 5 error handlers
4. `register_context_processors(app)` — global template variables
5. `register_template_filters(app)` — `humanize` Jinja filter
6. `register_shell_context(app)` — db, models for `flask shell`
7. `register_cli_commands(app)` — 4 CLI commands
8. `init_oauth(app)` — Google OAuth provider

### Error Handling

All error handlers support both HTMX and regular requests:
- HTMX requests → display an inline error toast
- Regular requests → render a full error page (`errors/4xx.html`)

---

## Services

| Service | File | Methods | Responsibility |
|---------|------|---------|----------------|
| **BaseService[T]** | `base.py` | `get_by_id`, `get_all`, `create`, `update`, `delete` | Generic CRUD base class |
| **AuthService** | `auth_service.py` | `validate_password`, `validate_email`, `register`, `login`, `send_password_reset`, `reset_password`, `verify_email`, `change_password` | Authentication, password management, email verification |
| **AnalyticsService** | `analytics_service.py` | `get_user_growth`, `get_revenue_growth`, `get_subscription_distribution`, `get_dashboard_stats`, `get_user_analytics`, `get_trial_conversion_stats`, `invalidate` | Dashboard stats, growth charts, MRR, churn, trial conversion |
| **AuditService** | `audit_service.py` | `log`, `get_logs`, `log_user_action` + `@audit_log` decorator | Audit logging for all critical actions |
| **BillingService** | `billing_service.py` | `create_checkout_session`, `create_customer_portal_session`, `handle_webhook` (+ 6 internal event handlers), `get_subscription_usage` | Stripe Checkout, Customer Portal, webhook processing |
| **CacheService** | `cache_service.py` | `cached` (decorator), `invalidate_org_data`, `invalidate_user_data`, `invalidate_analytics` | Redis caching with in-memory fallback |
| **EmailService** | `email_service.py` | `send_email`, `send_verification_email`, `send_password_reset_email`, `send_welcome_email`, `send_invitation_email`, `send_subscription_receipt` | SendGrid email with dev console fallback |
| **EntitlementService** | `entitlement_service.py` | `get_plan_config`, `has_feature`, `max_members`, `max_projects`, `can_add_member` + `@entitlement_required` decorator | Plan-based feature gating |
| **ImpersonationService** | `impersonation_service.py` | `start_impersonation`, `stop_impersonation`, `is_impersonating`, `get_impersonator_id`, `get_impersonation_reason` | Admin user impersonation with audit trail |
| **JobScheduler** | `job_scheduler.py` | `enqueue`, `enqueue_at`, `enqueue_in`, `get_status`, `cancel`, `get_recent_jobs` + `JobMonitorHooks` | RQ job scheduling with monitoring |
| **NotificationService** | `notification_service.py` | `create_notification`, `mark_as_read`, `mark_all_as_read`, `get_user_notifications`, `get_unread_count`, `bulk_create` | In-app notification system |
| **OrganizationService** | `org_service.py` | `create`, `switch_organization`, `get_members`, `update_member_role`, `remove_member`, `transfer_ownership`, `invite_member`, `accept_invitation`, `revoke_invitation` | Organization CRUD, member management, invitations |
| **RoleService** | `role_service.py` | `get_user_role`, `has_permission`, `get_permissions`, `change_role` + `@require_permission` decorator + 13 permission constants | Granular RBAC |
| **SessionService** | `session_service.py` | `create_session`, `get_user_sessions`, `revoke_session`, `revoke_all_sessions`, `touch_session` | User session tracking |
| **TwoFactorService** | `two_factor_service.py` | `generate_secret`, `get_provisioning_uri`, `generate_qr_code_base64`, `verify_code`, `generate_backup_codes`, `verify_backup_code` | TOTP 2FA (pyotp) |

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
| `ServiceError` | 400 | Base service exception (message, code, details) |
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

### User (`users`)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| email | String(255) | Unique, indexed |
| password_hash | String(255) | bcrypt |
| name | String(255) | |
| avatar_url | Text | |
| bio, company, location, website | Text | |
| email_verified | Boolean | Default False |
| email_verify_token | String(255) | |
| is_active | Boolean | Default True |
| is_admin | Boolean | Site admin |
| is_banned | Boolean | |
| banned_at, ban_reason | DateTime, Text | |
| last_login_at | DateTime | |
| last_login_ip | String(45) | |
| last_user_agent | Text | |
| login_count | Integer | |
| google_id | String(255) | Google OAuth |
| totp_secret | String(32) | |
| totp_enabled | Boolean | |
| totp_backup_codes | Text | JSON array |
| password_reset_token | String(255) | |
| created_at, updated_at | DateTime | |

**Relationships:** `memberships`, `owned_organizations`, `notifications`, `api_keys`, `audit_logs`

### Organization (`organizations`)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| name | String(255) | |
| slug | String(255) | Unique |
| logo_url | Text | |
| brand_color | String(7) | Hex color |
| description | Text | |
| website | String(255) | |
| timezone | String(50) | |
| owner_id | UUID (FK → User) | |
| subscription_tier | Enum(PlanType) | FREE/PRO/BUSINESS |
| subscription_status | String(50) | |
| trial_ends_at | DateTime | |
| max_members | Integer | |
| is_personal | Boolean | |
| created_at, updated_at | DateTime | |

**Relationships:** `memberships`, `subscriptions`, `invitations`, `feature_flags`

### Membership (`memberships`)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| organization_id | UUID (FK → Organization) | |
| role | Enum(Role) | OWNER/ADMIN/MEMBER |
| is_current | Boolean | Active org for user |
| joined_at | DateTime | |

### Subscription (`subscriptions`)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| organization_id | UUID (FK → Organization) | |
| stripe_subscription_id | String(255) | |
| stripe_customer_id | String(255) | |
| stripe_price_id | String(255) | |
| plan | Enum(PlanType) | |
| status | Enum(SubscriptionStatus) | |
| quantity | Integer | |
| trial_end | DateTime | |
| current_period_start/end | DateTime | |
| canceled_at, ended_at | DateTime | |

**Property:** `is_active` — checks status in (ACTIVE, TRIALING)

### Invoice (`invoices`)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| subscription_id | UUID (FK) | |
| organization_id | UUID (FK) | |
| stripe_invoice_id | String(255) | |
| amount_due, amount_paid | Integer | Cents |
| currency | String(3) | |
| status | String(50) | |
| pdf_url | Text | |
| paid_at | DateTime | |

### Other Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `ApiRequestLog` | `api_request_logs` | user_id, organization_id, api_key_id, method, endpoint, status_code, ip_address, user_agent, response_time_ms |
| `APIKey` | `api_keys` | user_id, organization_id, name, key_prefix, key_hash, key_type, permissions, last_used_at, expires_at, is_active, usage_count |
| `AuditLog` | `audit_logs` | actor_id, organization_id, action, resource_type, resource_id, metadata (JSON), ip_address, user_agent |
| `FeatureFlag` | `feature_flags` | name, key, description, enabled, scope, organization_id, user_id |
| `Invitation` | `invitations` | organization_id, email, token, role, invited_by_id, accepted_at, expires_at, revoked |
| `JobRecord` | `job_records` | name, queue, status, rq_job_id, scheduled_at, started_at, finished_at, result, error |
| `Notification` | `notifications` | user_id, type (INFO/SUCCESS/WARNING/ERROR), title, message, link, is_read |
| `PaymentEvent` | `payment_events` | organization_id, stripe_event_id, type, status, data (JSON), error_message |
| `UserSession` | `user_sessions` | user_id, session_id, ip_address, user_agent, device_name, browser, os, location, is_current, last_activity_at |

---

## Routes & Blueprints

### Blueprint Registration

| Blueprint | Variable | URL Prefix | Route Count |
|-----------|----------|------------|-------------|
| Core | `core_bp` | `/` | 13 |
| Auth | `auth_bp` | `/auth` | 10 |
| Organizations | `org_bp` | `/org` | 12 |
| Billing | `billing_bp` | `/billing` | 6 |
| Admin | `admin_bp` | `/admin` | 17 |
| Analytics | `analytics_bp` | `/analytics` | 5 |
| Notifications | `notifications_bp` | `/notifications` | 5 |
| API | `api_bp` | `/api/v1` | 10 |
| Security | `security_bp` | `/security` | 1 |

### Full Route Table

#### Core Blueprint (`/`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET | `/` | `index` | Public |
| GET | `/dashboard` | `dashboard` | Login |
| GET | `/settings` | `settings` | Login |
| POST | `/settings` | `settings` | Login |
| POST | `/auth/change-password` | `change_password` | Login |
| POST | `/impersonate/stop` | `stop_impersonation` | Admin |
| GET | `/sessions` | `sessions` | Login |
| POST | `/sessions/<id>/revoke` | `revoke_session` | Login |
| POST | `/sessions/revoke-all` | `revoke_all_sessions` | Login |
| GET | `/2fa/setup` | `two_factor_setup` | Login |
| POST | `/2fa/verify` | `two_factor_verify` | Login |
| POST | `/2fa/disable` | `two_factor_disable` | Login |
| GET | `/health` | `health` | Public |

#### Auth Blueprint (`/auth`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET/POST | `/auth/register` | `register` | Anon |
| GET/POST | `/auth/login` | `login` | Anon |
| GET/POST | `/auth/2fa-challenge` | `two_factor_challenge` | Anon |
| GET | `/auth/logout` | `logout` | Login |
| GET | `/auth/verify-email/<token>` | `verify_email` | Anon |
| GET | `/auth/resend-verification` | `resend_verification` | Login |
| GET/POST | `/auth/forgot-password` | `forgot_password` | Anon |
| GET/POST | `/auth/reset-password/<token>` | `reset_password` | Anon |
| GET | `/auth/google/login` | `google_login` | Anon |
| GET | `/auth/google/callback` | `google_callback` | Anon |

#### Organization Blueprint (`/org`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET/POST | `/org/create` | `create` | Login |
| GET/POST | `/org/<id>/settings` | `settings` | @org_required |
| GET | `/org/<id>/members` | `members` | @org_required |
| POST | `/org/<id>/members/invite` | `invite_member` | @require_permission |
| POST | `/org/<id>/members/<id>/remove` | `remove_member` | @require_permission |
| POST | `/org/<id>/members/<id>/role` | `update_member_role` | @require_permission |
| POST | `/org/switch/<id>` | `switch` | Login |
| GET | `/org/invitations/<token>/accept` | `accept_invitation` | Login |
| POST | `/org/invitations/<id>/revoke` | `revoke_invitation` | @require_permission |
| POST | `/org/<id>/transfer` | `transfer_ownership` | @require_owner |
| GET | `/org/<id>/activity` | `activity` | @org_required |

#### Billing Blueprint (`/billing`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET | `/billing/` | `index` | @org_required |
| POST | `/billing/create-checkout-session/<price>` | `create_checkout_session` | @org_required |
| GET | `/billing/success` | `success` | @org_required |
| GET | `/billing/customer-portal` | `customer_portal` | @org_required |
| POST | `/billing/webhook` | `webhook` | Public (Stripe) |
| GET | `/billing/history` | `history` | @org_required |

#### Admin Blueprint (`/admin`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET | `/admin/` | `index` | Admin |
| GET | `/admin/users` | `users` | Admin |
| GET | `/admin/users/<id>` | `user_detail` | Admin |
| POST | `/admin/users/<id>/ban` | `ban_user` | Admin |
| POST | `/admin/users/<id>/unban` | `unban_user` | Admin |
| POST | `/admin/users/<id>/disable` | `disable_user` | Admin |
| GET | `/admin/organizations` | `organizations` | Admin |
| GET | `/admin/organizations/<id>` | `organization_detail` | Admin |
| GET | `/admin/subscriptions` | `subscriptions` | Admin |
| GET | `/admin/payments` | `payments` | Admin |
| GET | `/admin/audit-logs` | `audit_logs` | Admin |
| GET | `/admin/analytics` | `analytics` | Admin |
| GET/POST | `/admin/cache` | `cache_management` | Admin |
| GET | `/admin/jobs` | `jobs` | Admin |
| POST | `/admin/jobs/<id>/cancel` | `cancel_job` | Admin |
| POST | `/admin/jobs/enqueue` | `enqueue_job` | Admin |
| GET | `/admin/api-stats` | `api_stats` | Admin |
| GET | `/admin/trial-analytics` | `trial_analytics` | Admin |
| POST | `/admin/impersonate` | `impersonate` | Admin |

#### Analytics Blueprint (`/analytics`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET | `/analytics/` | `index` | @org_required |
| GET | `/analytics/data/user-growth` | `user_growth_data` | @org_required |
| GET | `/analytics/data/revenue` | `revenue_data` | @org_required |
| GET | `/analytics/data/subscriptions` | `subscription_data` | @org_required |
| GET | `/analytics/data/stats` | `stats_data` | @org_required |

#### Notifications Blueprint (`/notifications`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET | `/notifications/` | `index` | Login |
| GET | `/notifications/unread-count` | `unread_count` | Login |
| GET | `/notifications/list` | `list_notifications` | Login |
| GET | `/notifications/<id>/read` | `mark_read` | Login |
| GET | `/notifications/read-all` | `mark_all_read` | Login |

#### API Blueprint (`/api/v1`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET | `/api/v1/` | `index` | Public |
| GET | `/api/v1/me` | `me` | API Key |
| GET | `/api/v1/organizations` | `list_organizations` | API Key |
| GET | `/api/v1/organizations/<id>` | `get_organization` | API Key |
| GET | `/api/v1/organizations/<id>/members` | `list_members` | API Key |
| GET | `/api/v1/keys` | `list_api_keys` | Session |
| POST | `/api/v1/keys` | `create_api_key` | Session |
| POST | `/api/v1/keys/<id>/revoke` | `revoke_api_key` | Session |
| GET | `/api/v1/admin/stats` | `admin_stats` | API Key + Admin |

#### Security Blueprint (`/security`)
| Method | Path | View | Auth |
|--------|------|------|------|
| GET | `/security/` | `index` | Login |

---

## Background Jobs

### Job Definitions (`app/jobs.py`)

| Job Function | Queue | Schedule | Description |
|-------------|-------|----------|-------------|
| `send_email_job(to, subject, html_body)` | saasforge-jobs | On-demand | Send transactional email |
| `send_verification_email_job(user_id, email, verify_url)` | saasforge-jobs | On-demand | Send email verification |
| `process_analytics_job(organization_id)` | saasforge-jobs | Hourly | Process analytics data |
| `cleanup_expired_data_job()` | saasforge-jobs | Daily (midnight) | Remove expired invitations and tokens |
| `generate_weekly_report_job()` | saasforge-jobs | Weekly (Mon 9am) | Generate admin digest report |

### Job Monitoring

Each job creates a `JobRecord` in the database tracking:
- Status (queued/started/finished/failed)
- Timestamps (scheduled, started, finished)
- Result or error message
- RQ job ID for cross-reference

The `JobMonitorHooks` class automatically updates `JobRecord` on RQ job completion or failure.

### CLI Job Management

```bash
flask schedule-jobs    # Register recurring jobs with RQ Scheduler
```

---

## API Reference

### Authentication

Most API endpoints require an API key sent via the `X-API-Key` header:

```bash
curl -H "X-API-Key: sf_your_api_key" http://localhost:5000/api/v1/me
```

### Interactive Documentation

Open http://localhost:5000/apidocs/ for the Swagger UI. The API spec covers 9 endpoints with request/response schemas.

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/` | None | API status and version info |
| GET | `/api/v1/me` | API Key | Current user profile (id, email, name, avatar, orgs) |
| GET | `/api/v1/organizations` | API Key | List user's organizations |
| GET | `/api/v1/organizations/:id` | API Key | Organization details with member count |
| GET | `/api/v1/organizations/:id/members` | API Key | Organization members list |
| GET | `/api/v1/keys` | Session | List user's API keys |
| POST | `/api/v1/keys` | Session | Create API key |
| POST | `/api/v1/keys/:id/revoke` | Session | Revoke an API key |
| GET | `/api/v1/admin/stats` | API Key + Admin | Admin dashboard stats |

### Create API Key

```bash
curl -X POST http://localhost:5000/api/v1/keys \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=My API Key&key_type=test" \
  -b "session=your_session_cookie"
```

### Rate Limiting

API rate limits are configurable via environment variables (`RATELIMIT_DEFAULT`, `RATELIMIT_STORAGE_URL`). Default: 100 requests/hour.

### API Key Prefix

All generated API keys are prefixed with `sf_` for easy identification.

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `flask seed-data` | Seed admin@saasforge.com and demo@saasforge.com users with orgs, subscriptions, and feature flags |
| `flask create-admin <email> <password> <name>` | Create an admin user |
| `flask list-routes` | Display all registered routes with methods and paths |
| `flask schedule-jobs` | Register recurring jobs with RQ Scheduler |
| `flask shell` | Interactive shell with `db`, `User`, `Organization`, `Membership`, `Subscription` pre-imported |
| `flask db upgrade` | Apply Alembic migrations |
| `flask db downgrade` | Rollback migration |
| `flask db migrate` | Generate new migration |

---

## Testing

### Running Tests

```bash
pytest                           # All 55+ tests
pytest --cov=app --cov-report=html  # Coverage report
pytest -v                        # Verbose output
pytest -k "auth"                 # Filter by keyword
pytest -m unit                   # Run only unit tests
pytest -m integration            # Run only integration tests
```

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
│   ├── app              # Flask app instance
│   ├── client           # Test client
│   ├── db               # Test database (SQLite in-memory)
│   ├── auth_headers     # Authenticated request headers
│   └── sample_user      # Pre-created test user
│
├── unit/
│   ├── test_base.py     # BaseService CRUD (create, get, update, delete)
│   └── test_auth_service.py  # Password validation, email validation,
│                              # registration, login, duplicate prevention
│
└── integration/
    └── test_auth_routes.py    # Login page, register page,
                                # registration flow, login flow,
                                # invalid credentials, forgot password page
```

### Test Database

Tests use an in-memory SQLite database. The test app is created once per session, with tables created before each test and dropped after.

### Fixtures

The `conftest.py` provides:
- `app` — Flask application with test config
- `client` — Flask test client
- `db_session` — Clean database for each test
- `sample_user` — Pre-registered user for login tests
- `auth_headers` — Basic auth header for authenticated requests

---

## Deployment

### Railway

```bash
railway login
railway up
```

Set the required environment variables in the Railway dashboard. A `railway.json` is included with health check configuration.

### Docker (VPS)

**Development stack:**
```bash
docker-compose up -d
```
Starts: web (Flask dev server), worker (RQ), scheduler (RQ Scheduler), db (PostgreSQL 16), redis (Redis 7)

**Production stack:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```
Adds Nginx reverse proxy. Environment variables read from `.env.prod`.

### Manual (VPS)

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
flask db upgrade

# Seed data
flask seed-data

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --timeout 120 wsgi:app
```

### Dockerfile

Multi-stage build:
1. **Builder stage:** Python 3.13-slim, installs build-essential + libpq-dev + Python deps
2. **Runtime stage:** Python 3.13-slim, libpq-dev + curl, copies built dependencies and app code
3. Healthcheck on `/` endpoint every 30s
4. Runs gunicorn with 4 gevent workers

---

## Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SECRET_KEY` | `change-this-in-production` | Yes | Flask secret key |
| `FLASK_ENV` | `development` | No | Environment mode |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/saasforge` | Yes | PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | `10` | No | Connection pool size |
| `DATABASE_POOL_MAX_OVERFLOW` | `20` | No | Max pool overflow |
| `REDIS_URL` | `redis://localhost:6379/0` | Yes | Redis connection string |
| `STRIPE_SECRET_KEY` | — | Yes | Stripe API secret key |
| `STRIPE_PUBLISHABLE_KEY` | — | Yes | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | — | Yes (prod) | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | — | Yes | Price ID for Pro plan |
| `STRIPE_BUSINESS_PRICE_ID` | — | Yes | Price ID for Business plan |
| `GOOGLE_OAUTH_CLIENT_ID` | — | Optional | Google OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | — | Optional | Google OAuth client secret |
| `SENDGRID_API_KEY` | — | Optional | SendGrid API key |
| `MAIL_DEFAULT_SENDER` | `noreply@saasforge.com` | No | From address for emails |
| `APP_NAME` | `SaaSForge` | No | Application name |
| `APP_URL` | `http://localhost:5000` | No | Application base URL |
| `APP_DOMAIN` | `localhost:5000` | No | Application domain |
| `ADMIN_EMAIL` | `admin@saasforge.com` | No | Admin email address |
| `SENTRY_DSN` | — | Optional | Sentry error tracking DSN |
| `SESSION_TYPE` | `redis` | No | Session storage backend |
| `SESSION_COOKIE_SECURE` | `False` | No | Secure session cookie flag |
| `PERMANENT_SESSION_LIFETIME` | `2592000` (30 days) | No | Session lifetime in seconds |
| `RATELIMIT_DEFAULT` | `100/hour` | No | Default rate limit |
| `RATELIMIT_STORAGE_URL` | `redis://localhost:6379/0` | No | Rate limit storage backend |
| `UPLOAD_FOLDER` | `app/static/uploads` | No | File upload directory |
| `MAX_CONTENT_LENGTH` | `5242880` (5MB) | No | Max upload size in bytes |
| `FEATURE_NEW_DASHBOARD` | `true` | No | Feature flag |
| `FEATURE_BETA_API` | `false` | No | Feature flag |

> **Local dev:** `python run.py` needs no env vars — it auto-selects SQLite (`LocalConfig`), disables CSRF and rate limiting, logs emails to console, and uses filesystem sessions. Set `DATABASE_URL=postgresql://...` to run against PostgreSQL locally.

---

## Security

### Authentication & Sessions
- CSRF protection (Flask-WTF) on all forms (disabled in dev for convenience)
- Session-based auth with HTTP-only cookies
- Password hashing via bcrypt (Werkzeug 6000 rounds)
- Two-factor authentication (TOTP) with authenticator apps + 10 backup codes
- 2FA challenge flow intercepts login when TOTP is enabled
- Session tracking with browser/OS/IP identification
- Session revocation (individual or all other sessions)

### Access Control
- 13 granular permissions across 3 roles
- `@require_permission` decorator on sensitive routes
- `@require_owner` and `@require_admin` decorators
- `@require_email_verified` for sensitive actions
- Admin-only routes for management features

### Input Validation
- Service-layer input validation with typed exceptions
- Email format validation
- Password strength validation (8+ chars, uppercase, lowercase, number, special)
- Jinja2 auto-escaping for XSS protection
- SQL injection protection via SQLAlchemy ORM

### API Security
- API key authentication with SHA-256 hashed keys in DB
- API key prefix (`sf_`) for easy identification
- Rate limiting via Flask-Limiter + Redis
- API request logging for audit

### Payment Security
- Stripe webhook signature verification
- No raw card data handling (Stripe Checkout)
- PCI compliance via Stripe

### Infrastructure
- Health monitoring endpoint (`GET /health`)
- Sentry error tracking (configurable)
- CI/CD security scanning:
  - **Bandit** — Static Application Security Testing (SAST)
  - **Safety** — Dependency vulnerability scanning
  - **Gitleaks** — Secret/credential scanning
- Docker health checks
- Production Nginx reverse proxy

### Audit Trail
- All critical actions logged to `audit_logs` table
- Tracks: actor, action, resource type, resource ID, IP, user agent, metadata
- `@audit_log` decorator for easy action logging
- Admin audit log viewer with search/filter

---

## Database Migrations

The project uses Alembic (via Flask-Migrate) with 6 migration revisions:

| Revision | Description |
|----------|-------------|
| `cb91a1ee165e` | Initial schema: users, orgs, memberships, subscriptions, invoices, invitations, notifications, audit_logs, api_keys, feature_flags, payment_events |
| `4626fbde516c` | Add `job_records` table for background job tracking |
| `8757bf2ba419` | Add `user_sessions` table for session management |
| `78e2f1f46958` | Add `api_request_logs` table for API usage analytics |
| `2d1b9e4ca700` | Add 2FA fields to users: `totp_enabled`, `totp_secret`, `totp_backup_codes` |
| `29131e9dc678` | Add `brand_color` to organizations |

### Migration Commands

```bash
flask db upgrade          # Apply all pending migrations
flask db downgrade <rev>  # Rollback to revision
flask db migrate -m "message"  # Generate new migration from model changes
flask db current          # Show current revision
flask db history          # Show migration history
```
