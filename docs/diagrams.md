# SaaSForge Architecture Diagrams

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Browser / Client                              │
│                           (HTMX + Alpine.js)                             │
└──────────────────┬──────────────────────────────────┬───────────────────┘
                   │                                  │
                   ▼                                  ▼
            ┌──────────────┐                ┌──────────────────┐
            │   Nginx      │                │  CDN (Tailwind,  │
            │  (Reverse    │                │  Chart.js, HTMX) │
            │   Proxy)     │                └──────────────────┘
            └──────┬───────┘
                   │
            ┌──────▼───────┐
            │  Gunicorn    │
            │  (4 gevent   │
            │   workers)   │
            └──────┬───────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
┌───────────┐ ┌────────┐ ┌──────────┐
│ Flask App │ │ Static │ │ Sentry   │
│ (9 Blue-  │ │ Files  │ │ (Error   │
│  prints)  │ │        │ │ Tracking)│
└─────┬─────┘ └────────┘ └──────────┘
      │
      ├──────────────────┬──────────────────┐
      ▼                  ▼                  ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  PostgreSQL  │ │    Redis     │ │   RQ Worker       │
│  (Primary    │ │  (Cache +    │ │  (saasforge-jobs) │
│   Database)  │ │   Queue)     │ └──────────────────┘
└──────────────┘ └──────────────┘
      │                              ┌──────────────────┐
      │                              │  RQ Scheduler    │
      │                              │  (cron jobs)     │
      │                              └──────────────────┘
      │
      ├──────────────────┬──────────────────┐
      ▼                  ▼                  ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│   Stripe     │ │  SendGrid    │ │  Customer        │
│  (Payments)  │ │  (Email)     │ │  Webhooks        │
└──────────────┘ └──────────────┘ └──────────────────┘
```

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Registration Flow                                │
│                                                                         │
│  User → /auth/register → AuthService.register() → User created          │
│                                                     ↓                   │
│                              Verification email sent → EmailService     │
│                                                     ↓                   │
│                              User clicks link → /auth/verify-email/<t>  │
│                                                     ↓                   │
│                              email_verified = true → Redirect to login  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           Login Flow                                     │
│                                                                         │
│  User → /auth/login → AuthService.login()                               │
│                          ↓                                              │
│                    Validate credentials                                  │
│                          ↓                                              │
│                   ┌──────┴──────┐                                       │
│                   │             │                                       │
│               totp=no       totp=yes                                    │
│                   │             │                                       │
│                   ▼             ▼                                       │
│             ┌─────────┐  ┌──────────────┐                              │
│             │Session  │  │ /auth/2fa-   │                              │
│             │Created  │  │ challenge    │                              │
│             │         │  │      ↓       │                              │
│             │Redirect │  │ Verify code  │                              │
│             │to       │  │      ↓       │                              │
│             │Dashboard│  │ Session      │                              │
│             └─────────┘  │ Created      │                              │
│                          └──────────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          OAuth Flow (Google)                            │
│                                                                         │
│  User → /auth/google/login → Redirect to Google OAuth                   │
│                                      ↓                                  │
│  User approves → Google callback → /auth/google/callback                │
│                                      ↓                                  │
│              ┌──────────────────────┴──────────────┐                   │
│              │                                     │                   │
│         Existing user                       New user                    │
│              │                                     │                   │
│              ▼                                     ▼                   │
│         Login + link                     Register + link                │
│         Google account                   Google account                 │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       Password Reset Flow                                │
│                                                                         │
│  User → /auth/forgot-password → Email with reset link                   │
│                                      ↓                                  │
│  User clicks link → /auth/reset-password/<token>                        │
│                                      ↓                                  │
│              AuthService.reset_password(token, new_password)            │
│                                      ↓                                  │
│                         Password updated → Login                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Billing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Checkout Flow                                      │
│                                                                         │
│  User clicks "Upgrade" → POST /billing/create-checkout-session/<price> │
│                              ↓                                          │
│           BillingService.create_checkout_session()                      │
│                              ↓                                          │
│           Stripe Checkout Session created → Redirect to Stripe          │
│                              ↓                                          │
│           User fills payment details on Stripe Checkout                 │
│                              ↓                                          │
│           Stripe → POST /billing/webhook                                │
│              (checkout.session.completed)                               │
│                              ↓                                          │
│           BillingService._handle_checkout_completed()                   │
│                              ↓                                          │
│           Subscription created → Org tier updated → Cache invalidated   │
│                              ↓                                          │
│           User redirected to /billing/success                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      Webhook Processing Pipeline                         │
│                                                                         │
│  Stripe → POST /billing/webhook (signed payload)                        │
│              ↓                                                          │
│  BillingService.handle_webhook()                                        │
│              ↓                                                          │
│  Verify Stripe signature → construct_event()                            │
│              ↓                                                          │
│  WebhookEventLog: Check idempotency (stripe_event_id unique)            │
│              ↓                                                          │
│  Route to handler based on event.type:                                  │
│    ├── checkout.session.completed                                       │
│    ├── customer.subscription.created                                    │
│    ├── customer.subscription.updated                                    │
│    ├── customer.subscription.deleted                                    │
│    ├── invoice.paid                                                     │
│    └── invoice.payment_failed                                           │
│              ↓                                                          │
│  PaymentEvent stored (for audit/retry)                                  │
│              ↓                                                          │
│  WebhookEventLog: status = completed/failed                             │
│              ↓                                                          │
│  Customer Webhook Delivery (if configured)                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Subscription Lifecycle                                 │
│                                                                         │
│  Trial → Active → Past Due → Canceled                                   │
│    │        │         │           │                                     │
│    │        │         │           ▼                                     │
│    │        │         │     [Ended / Free tier]                         │
│    │        │         │                                                 │
│    │        │         ▼                                                 │
│    │        │   [Stripe sends reminder]                                 │
│    │        │                                                           │
│    │        ▼                                                           │
│    │   [Upgrade/Downgrade via Customer Portal]                          │
│    │                                                                    │
│    ▼                                                                    │
│  [Trial ending email → Convert or lose access]                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Multi-Tenant Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Organization Model & Isolation                         │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                    Organization                                 │      │
│  │  id (PK), name, slug, owner_id, subscription_tier, ...         │      │
│  └──────────────────┬───────────────────────────────────────────┘      │
│                     │                                                   │
│        ┌────────────┼────────────┬────────────┬────────────┐           │
│        ▼            ▼            ▼            ▼            ▼           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │Membership│ │Subscription│ │ Invoice  │ │AuditLog │ │FeatureFlag│   │
│  │ user_id  │ │org_id     │ │ org_id   │ │org_id   │ │ org_id    │    │
│  │ org_id   │ │plan       │ │ amount   │ │ action   │ │ key       │    │
│  │ role     │ │status     │ │ status   │ │ metadata │ │ enabled   │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│                                                                         │
│  Isolation: ALL queries filter by organization_id                       │
│  Users can belong to MULTIPLE orgs (Membership.is_current)              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                   Team Hierarchy & Permissions                           │
│                                                                         │
│  Organization                                                           │
│    ├── Owner (1)                                                        │
│    │   ├── Full billing access                                          │
│    │   ├── Delete organization                                          │
│    │   ├── Transfer ownership                                           │
│    │   ├── Manage all members & roles                                   │
│    │   └── All permissions below                                        │
│    │                                                                     │
│    ├── Admin (unlimited)                                                │
│    │   ├── Manage members (invite/remove)                               │
│    │   ├── Manage roles                                                 │
│    │   ├── Manage organization settings                                 │
│    │   ├── View billing                                                 │
│    │   └── All permissions below                                        │
│    │                                                                     │
│    └── Member (unlimited)                                               │
│        ├── View organization members                                    │
│        ├── View activity log                                            │
│        ├── Create/view API keys                                         │
│        └── View own notifications                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Background Job Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Job Lifecycle                                       │
│                                                                         │
│  ┌──────────────┐                                                       │
│  │  Application  │  JobScheduler.enqueue("name", fn, *args)            │
│  │  (Flask)      │                                                      │
│  └──────┬───────┘                                                       │
│         │                                                                │
│         │  1. Create JobRecord (status: queued)                         │
│         │  2. RQ enqueue to Redis                                       │
│         ▼                                                                │
│  ┌──────────────┐                                                       │
│  │    Redis     │  Queue: saasforge-jobs                                │
│  │  (saasforge- │                                                       │
│  │   jobs)      │                                                       │
│  └──────┬───────┘                                                       │
│         │                                                                │
│         │  RQ Worker picks up job                                       │
│         ▼                                                                │
│  ┌──────────────┐                                                       │
│  │  RQ Worker   │  3. Update JobRecord (status: started)                │
│  │              │  4. Execute the job function                          │
│  └──────┬───────┘                                                       │
│         │                                                                │
│    ┌────┴────┐                                                          │
│    │         │                                                          │
│    ▼         ▼                                                          │
│  Success    Failure                                                     │
│    │         │                                                          │
│    ▼         ▼                                                          │
│  JobRecord  JobRecord                                                   │
│  status:    status:                                                     │
│  finished   failed                                                      │
│             │                                                           │
│        ┌────┴────┐                                                     │
│        │         │                                                     │
│        ▼         ▼                                                     │
│     Retry     Dead Letter                                               │
│    (if < max) (if >= max)                                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   Scheduled Jobs                                  │  │
│  │                                                                   │  │
│  │  RQ Scheduler → Redis → Worker at specified times:               │  │
│  │    - Hourly:      process_analytics_job                           │  │
│  │    - Daily 02:00: cleanup_expired_data_job                        │  │
│  │    - Mon 09:00:  generate_weekly_report_job                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## API Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    API v1 Request Lifecycle                              │
│                                                                         │
│  Client → GET /api/v1/me                                                │
│              │                                                          │
│              ▼                                                          │
│  ┌─────────────────────────┐                                           │
│  │ 1. before_api_request   │  g.api_start_time = time.time()           │
│  └─────────────────────────┘                                           │
│              │                                                          │
│              ▼                                                          │
│  ┌─────────────────────────┐                                           │
│  │ 2. @api_auth_required   │  Check X-API-Key header                   │
│  │                         │  Lookup + verify key hash                 │
│  │                         │  Check expiry                             │
│  │                         │  Check daily usage limit                  │
│  │                         │  Update usage_count + last_used_at        │
│  │                         │  Set g.api_user, g.api_key                │
│  └─────────────────────────┘                                           │
│              │                                                          │
│              ▼                                                          │
│  ┌─────────────────────────┐                                           │
│  │ 3. @require_api_perm    │  Check API key permissions                │
│  │                         │  Verify scope (read:users, etc.)          │
│  └─────────────────────────┘                                           │
│              │                                                          │
│              ▼                                                          │
│  ┌─────────────────────────┐                                           │
│  │ 4. Route Handler        │  Parse params, call service               │
│  └─────────────────────────┘                                           │
│              │                                                          │
│              ▼                                                          │
│  ┌─────────────────────────┐                                           │
│  │ 5. Service Layer        │  Business logic, DB queries, caching      │
│  └─────────────────────────┘                                           │
│              │                                                          │
│              ▼                                                          │
│  ┌─────────────────────────┐                                           │
│  │ 6. log_api_request      │  Record ApiRequestLog (method, endpoint,  │
│  │ (after_request)         │  status_code, response_time_ms, IP)       │
│  └─────────────────────────┘                                           │
│              │                                                          │
│              ▼                                                          │
│  Client ← JSON Response (with correlation ID header)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Observability Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Observability Stack                                 │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                    Structured Logging                         │      │
│  │  JSON output, correlation_id, level, module, function, line  │      │
│  │  logger.info("event", extra={"structured_data": {...}})       │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                 Correlation IDs                              │      │
│  │  X-Correlation-ID → flows across all services                │      │
│  │  Browser → Flask → Service → DB → Job → Webhook             │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │              Prometheus Metrics (/metrics)                    │      │
│  │  http_request_duration_ms{method, endpoint}                  │      │
│  │  http_requests_total{method, endpoint, status}               │      │
│  │  http_errors_total{method, endpoint, status}                 │      │
│  │  db_query_duration_ms (histogram)                            │      │
│  │  cache_hits_total / cache_misses_total                       │      │
│  │  worker_job_duration_ms{job, status}                         │      │
│  │  queue_operations_total{operation, queue}                    │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                 Health Checks (/health, /health/detailed)     │      │
│  │  Database connectivity, Redis, Queue, Stripe, Email         │      │
│  │  Docker HEALTHCHECK every 30s                                │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │               Performance Monitoring                         │      │
│  │  Avg/P95/P99 response times                                  │      │
│  │  Slowest endpoints tracking                                  │      │
│  │  @monitor_query() decorator for service methods              │      │
│  │  pg_stat_statements for DB query analysis                    │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Webhook Delivery System

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Customer Webhook Delivery                             │
│                                                                         │
│  Internal Event Occurred:                                                │
│    - member.invited, subscription.updated, etc.                         │
│              │                                                          │
│              ▼                                                          │
│  CustomerWebhookService.deliver_event(event_type, payload, org_id)      │
│              │                                                          │
│              ▼                                                          │
│  Find all active endpoints for organization subscribed to this event    │
│              │                                                          │
│         ┌────┴────┐                                                    │
│         │         │                                                     │
│         ▼         ▼                                                     │
│   Endpoint 1  Endpoint 2  ...                                           │
│         │         │                                                     │
│         ▼         ▼                                                     │
│  WebhookDelivery created (status: pending)                              │
│              │                                                          │
│              ▼                                                          │
│  POST to endpoint URL with:                                             │
│    - JSON payload with event, id, timestamp, data                       │
│    - X-Webhook-Signature: sha256={hmac}                                 │
│    - X-Webhook-Event: {event_type}                                      │
│    - X-Webhook-Delivery-ID: {delivery_id}                               │
│              │                                                          │
│         ┌────┴────┐                                                    │
│         │         │                                                     │
│   2xx success   Non-2xx / timeout                                       │
│         │         │                                                     │
│         ▼         ▼                                                     │
│  status:       status: failed → retry (up to 5 attempts)              │
│  delivered     endpoint.last_delivered_at updated                       │
└─────────────────────────────────────────────────────────────────────────┘
```
