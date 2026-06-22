# Architecture

**SaaSForge** follows a layered architecture with clean separation between HTTP controllers, business logic, and data access. This document describes the architectural patterns, enterprise features, and key decisions.

---

## Table of Contents

- [Layered Architecture](#layered-architecture)
- [Application Factory](#application-factory)
- [Observability](#observability)
- [PostgreSQL Optimization](#postgresql-optimization)
- [Webhook Delivery System](#webhook-delivery-system)
- [API Platform](#api-platform)
- [Performance Engineering](#performance-engineering)
- [Business Metrics](#business-metrics)
- [Demo Environment](#demo-environment)
- [Multi-Tenancy](#multi-tenancy)
- [Caching Strategy](#caching-strategy)
- [Background Jobs](#background-jobs)
- [Error Handling](#error-handling)
- [Key Architectural Decisions](#key-architectural-decisions)

---

## Layered Architecture

```
+-------------------------------------------------------+
|                   Presentation                        |
|  10 Blueprints (routes) -> HTTP, validation, render   |
+-------------------------------------------------------+
|                   Service Layer                       |
|  20 service classes -> business logic, queries,       |
|                        cross-cutting concerns         |
+-------------------------------------------------------+
|                   Data Layer                          |
|  17 SQLAlchemy models -> DB access, relationships     |
+-------------------------------------------------------+
|                   Infrastructure                      |
|  Stripe, SendGrid, Redis, RQ, filesystem,             |
|  Prometheus, structured logging, correlation IDs     |
+-------------------------------------------------------+
```

**Key principles:**
- Routes are thin (~30-50 lines): parse input, call service, handle result, render
- Services encapsulate all business logic, DB ops, and side effects (caching, auditing, notifications, metrics)
- Services raise typed exceptions (`ValidationError`, `NotFoundError`, `PermissionError`, `ServiceError`)
- Same service layer serves both HTML routes and JSON API endpoints
- All new services include structured logging, correlation ID propagation, and metric recording

---

## Application Factory

`create_app()` in `app/__init__.py` orchestrates initialization in dependency order:

```python
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    initialize_extensions(app)       # SQLAlchemy, Login, CSRF, Limiter, RQ, Swagger
    register_blueprints(app)         # 10 blueprints
    register_error_handlers(app)     # 5 handlers (400/403/404/429/500)
    register_context_processors(app) # Global template vars
    register_template_filters(app)   # humanize, currency, compact, pct_change
    register_shell_context(app)      # db + models for flask shell
    register_cli_commands(app)       # 5 CLI commands
    register_scheduled_jobs(app)     # Recurring job setup
    init_oauth(app)                  # Google OAuth
    init_observability(app)          # JSON logging, correlation IDs, metrics
    init_database_extensions(app)    # JSONB, GIN, FTS, materialized views (PG only)
    init_demo_environment(app)       # Demo safety middleware
    return app
```

---

## Observability

### Structured Logging

`StructuredFormatter` outputs every log line as JSON:

```json
{"timestamp": "2026-06-22T20:08:34+00:00", "level": "INFO",
 "logger": "app", "message": "Observability initialized",
 "module": "__init__", "function": "init_observability",
 "line": 172, "correlation_id": "a1b2c3d4e5f6a7b8"}
```

Configure via `LOG_FORMAT` env var (`json` or `text`).

### Correlation IDs

`CorrelationMiddleware` assigns a unique ID to every request:
- Read from `X-Correlation-ID` header if present (forwarded from upstream)
- Generated as `uuid.uuid4().hex[:16]` if absent
- Stored in a `ContextVar` for thread-safe access
- Propagated to responses via the same header
- Available anywhere via `get_correlation_id()`

### Prometheus Metrics

`MetricsRegistry` provides counters, gauges, and histograms. Rendered as Prometheus text format at `/metrics`.

### Health Checks

`HealthStatus` provides a composable health check system. `/health/detailed` runs 5 checks: database, Redis, queue, Stripe, email.

---

## PostgreSQL Optimization

The `app/db/__init__.py` module provides PostgreSQL-specific enhancements that gracefully degrade on SQLite.

### JSONB Support

`jsonb_column(name, default=None)` returns `db.JSON` on SQLite and maps to `JSONB` on PostgreSQL:

```python
from app.db import jsonb_column
metadata = jsonb_column("metadata", default=dict)
```

### GIN Indexes

`create_gin_indexes()` creates GIN indexes on JSONB columns for efficient path queries like `metadata->>'key'`. Skipped on SQLite.

### Full-Text Search

`create_full_text_search()` adds tsvector columns with trigger-based auto-update. Search via:

```python
from app.db import fts_search
results = fts_search(MyModel, "search query", "search_vector")
```

Triggers fire on INSERT/UPDATE to keep tsvectors in sync.

### Materialized Views

Three views with concurrent refresh support:

```sql
mv_dashboard_stats      -- Users, orgs, subscriptions, MRR
mv_revenue_by_month     -- Monthly revenue aggregation
mv_api_usage_stats      -- API call counts and response times
```

Refresh via:
```python
from app.db import refresh_materialized_view
refresh_materialized_view("mv_dashboard_stats")
```

---

## Webhook Delivery System

### Architecture

```
Stripe Event → POST /billing/webhook
  → Verify Stripe signature
  → WebhookEventLog: check idempotency (stripe_event_id unique)
  → Route to handler
  → Update PaymentEvent
  → Customer Webhook Delivery (if configured)

Customer Event (internal) → CustomerWebhookService.deliver_event()
  → Find active endpoints subscribed to event type
  → WebhookDelivery created (status: pending)
  → POST to endpoint URL with HMAC-SHA256 signature
  → Update status (delivered/failed)
  → Retry up to 5 times on failure
```

### Idempotency

Stripe webhooks are guaranteed exactly-once via `WebhookEventLog` table with a unique constraint on `stripe_event_id`.

### Retry Logic

- Initial attempt + up to 4 retries (5 total)
- Exponential backoff between retries
- Dead-letter queue for events that exhaust retries
- Admin can manually retry from admin UI

### Customer Webhooks

- HMAC-SHA256 signing with per-endpoint secrets
- Event type subscriptions (checkboxes in UI)
- Delivery history with response codes, bodies, and timestamps
- Test endpoint sends a `ping` event to verify connectivity

---

## API Platform

### Scoped Permissions

12 API permission scopes organized into preset groups:

```python
SCOPE_PERMISSIONS = {
    "read": ["read:users", "read:organizations", "read:billing", "webhooks:read", "audit:read"],
    "write": ["read:*", "write:organizations", "write:members", "webhooks:write", "api_keys:write"],
    "admin": ["admin:analytics", "admin:users"],
    "full": ["*all 12 scopes*"],
}
```

### Usage Limits

Per-plan limits enforced by `UsageLimitService`:
- Free: 1,000 requests/day, 10/min
- Pro: 10,000 requests/day, 60/min
- Business: 100,000 requests/day, 300/min

### Request Lifecycle

```
Client → api_auth_required → key lookup + expiry + limit check
      → require_api_permission → scope check
      → Route handler → Service → Response
      → log_api_request → ApiRequestLog recorded
```

---

## Performance Engineering

### Response Time Tracking

`PerformanceMetrics` queries `ApiRequestLog` for:
- Average response time (7/30 day window)
- P95/P99 via `percentile_cont` (PostgreSQL) with graceful fallback
- Slowest endpoints grouped by method + path
- Error rate (5xx / total)

### Slow Query Monitoring

`@monitor_query(name, threshold_ms)` decorator:

```python
@monitor_query(name="org_service.create", threshold_ms=200)
def create(self, ...):
    ...
```

Results accumulate in an in-memory list (capped at 100) with function name, duration, threshold, and timestamp.

### Cache Analytics

`get_cache_analytics()` reports hits, misses, and total operations from the Prometheus metrics registry.

---

## Business Metrics

`BusinessMetricsService` computes all metrics from local DB data (no external API calls):

| Metric | Calculation | Source |
|--------|------------|--------|
| MRR | active_pro × $29 + active_business × $99 | Subscriptions |
| ARR | MRR × 12 | Derived |
| Churn Rate | canceled / (existing + new) over period | Subscriptions |
| LTV | avg_revenue_per_customer × (1 / churn_rate) | Derived |
| Trial Conversion | converted / total_trials | Subscriptions |
| Growth Rate | MoM user and revenue change | Users, Invoices |
| Revenue Trend | Monthly revenue over 180 days | Invoices |

---

## Demo Environment

### Safety Middleware

`DemoMiddleware` runs before every request in demo mode:
- Skips for unauthenticated users, admin users, and logout
- Intercepts destructive POST/PUT/DELETE to `/admin/users/`, `/admin/orgs/`, `/org/`, `/billing/`
- Redirects with flash warning for non-admin users
- Whitelisted safe POST paths include `/auth/`, `/settings`, `/2fa/`, `/webhooks/`, `/security/`

### Seed Data

`create_seed_data()` creates 4 demo accounts with orgs, subscriptions, invoices, feature flags, and extra users. All data is self-contained and resettable.

### Reset

`reset_demo_data()` deletes all demo-created records and reseeds from scratch. Admin-only via `POST /admin/reset-demo`.

---

## Multi-Tenancy

```
Organization (tenant boundary)
+-- Owner    -- full access, billing, delete, transfer
+-- Admin    -- manage members, roles, settings
+-- Member   -- basic access
```

- `Organization` is the tenant boundary
- `Membership` links `User` ↔ `Organization` with a role and `is_current` flag
- All domain models reference `organization_id` for data isolation
- Queries always filter by `organization_id`
- Users can belong to multiple orgs

---

## Caching Strategy

- `RedisCache` wraps Redis with automatic in-memory fallback (Python dict)
- Analytics cached with 5-minute TTL under `analytics:*` namespace
- Cache invalidated on data mutations
- Pattern-based invalidation (`analytics:*`) — coarse but correct

---

## Background Jobs

RQ workers process jobs from the `saasforge-jobs` queue:
- **Analytics refresh** (hourly): aggregate dashboards
- **Cleanup** (daily 02:00 UTC): expired invitations, stale tokens
- **Weekly report** (Monday 09:00): admin digest
- **Email sending** (on-demand): transactional emails

Each job creates a `JobRecord` in the database for monitoring. `JobMonitorHooks` auto-updates status on completion/failure.

---

## Error Handling

All error handlers support both HTMX and regular requests:
- **HTMX:** inline error toast rendered from `components/error_toast.html`
- **Regular:** full error page (`errors/4xx.html` or `errors/5xx.html`)
- **API:** JSON error response with correlation ID

---

## Key Architectural Decisions

1. **Thin controllers, fat services** — Routes handle HTTP only; services handle all logic
2. **Service layer as middleware boundary** — Cross-cutting concerns (audit, cache, metrics) compose at the service layer, not in routes
3. **PostgreSQL-first with SQLite fallback** — All PG features wrapped in try/except; local dev works with zero config
4. **Idempotent webhooks** — `WebhookEventLog` unique constraint guarantees exactly-once processing
5. **HMAC-signed customer webhooks** — Per-endpoint secrets prevent forgery
6. **In-memory slow query tracking** — Capped list avoids DB overhead for monitoring data
7. **MRR from local DB** — Avoids Stripe API latency for business metrics
8. **Demo safety via middleware** — Prevents accidental destruction without modifying route logic
9. **Correlation IDs via ContextVar** — Thread-safe, no request object pollution
10. **Configuration-driven factory** — `create_app(config)` pattern supports testing and multiple environments
