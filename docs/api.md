# API Reference

## REST API v1

Base URL: `/api/v1`

### Authentication

All endpoints (except root) require an API key sent via the `X-API-Key` header:

```bash
curl -H "X-API-Key: sf_your_api_key" http://localhost:5000/api/v1/me
```

### API Key Scopes

Keys are created with a permission scope that dictates which endpoints are accessible.

| Scope | Granted Permissions |
|-------|-------------------|
| `read` | `read:users`, `read:organizations`, `read:billing`, `webhooks:read`, `audit:read` |
| `write` | All `read` + `write:organizations`, `write:members`, `webhooks:write`, `api_keys:write` |
| `admin` | `admin:analytics`, `admin:users` |
| `full` | All 12 scopes |

Permission enforcement uses the `@require_api_permission` decorator:

```python
@api_bp.route("/admin/stats")
@api_auth_required
@require_api_permission(APIPermission.ADMIN_ANALYTICS)
def admin_stats():
    ...
```

### Usage Limits

| Plan | Daily Request Limit | Rate Limit |
|------|-------------------|------------|
| Free | 1,000 | 10/min |
| Pro | 10,000 | 60/min |
| Business | 100,000 | 300/min |

Exceeded daily limit returns `429 Too Many Requests` with reset info.

### Endpoints

#### `GET /api/v1/`
API status and version. Public.

```json
{"status": "ok", "version": "1.0"}
```

#### `GET /api/v1/me`
Current user profile. Requires `read:users`.

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "avatar_url": null,
  "organizations": [{"id": "uuid", "name": "Org", "role": "owner"}]
}
```

#### `GET /api/v1/organizations`
List user's organizations. Requires `read:organizations`.

#### `GET /api/v1/organizations/:id`
Organization details. Requires `read:organizations`.

#### `GET /api/v1/organizations/:id/members`
Organization members. Requires `read:organizations` and org membership.

#### `GET /api/v1/keys`
List user's API keys. Session auth (not API key).

#### `POST /api/v1/keys`
Create API key. Session auth. Body: `name`, `key_type` (test/live), `scope` (read/write/admin/full).

Returns the raw key once (shown at creation only).

#### `POST /api/v1/keys/:id/revoke`
Revoke API key. Session auth.

#### `GET /api/v1/admin/stats`
Admin dashboard statistics. Requires `admin:analytics` scope.

### Error Format

```json
{
  "error": "insufficient_permissions",
  "message": "Requires 'admin:analytics' permission",
  "required": "admin:analytics",
  "correlation_id": "a1b2c3d4e5f6a7b8"
}
```

Standard HTTP codes: 400 (validation), 401 (auth), 403 (permissions), 404 (not found), 429 (rate limit).

## Customer Webhook Management API

Base URL: `/webhooks` (session-auth, requires login)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/webhooks/` | List endpoints + event type selection |
| POST | `/webhooks/create` | Create endpoint (url, events[], description) |
| POST | `/webhooks/<id>/update` | Update endpoint (url, events[], description) |
| POST | `/webhooks/<id>/toggle` | Activate/deactivate endpoint |
| POST | `/webhooks/<id>/delete` | Delete endpoint |
| POST | `/webhooks/<id>/test` | Send test event |
| GET | `/webhooks/<id>/deliveries` | Delivery history for endpoint |
| POST | `/webhooks/deliveries/<id>/retry` | Retry failed delivery |

### Event Types

Available for subscription:
- `subscription.updated`, `subscription.created`, `subscription.canceled`
- `member.invited`, `member.removed`, `member.role_changed`
- `invoice.paid`, `invoice.payment_failed`
- `org.updated`, `org.settings_changed`

### Delivery Format

Webhook payloads are POSTed to endpoint URLs with:

**Headers:**
- `Content-Type: application/json`
- `X-Webhook-Signature: sha256=<HMAC-SHA256 of body>`
- `X-Webhook-Event: <event_type>`
- `X-Webhook-Delivery-ID: <delivery_uuid>`

**Body:**
```json
{
  "id": "evt_uuid",
  "event": "subscription.updated",
  "created_at": "2026-06-22T20:00:00Z",
  "data": {
    "organization_id": "org_uuid",
    "plan": "pro",
    "status": "active"
  }
}
```

### Retry Policy

- Up to 5 delivery attempts
- Exponential backoff between attempts
- Dead-letter after 5 failures
- Manual retry via admin UI or delivery history page

## Admin API (HTML)

Base URL: `/admin` (session-auth, requires admin role)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/` | Dashboard overview |
| GET | `/admin/performance` | P95/P99 response times, slow queries, cache stats |
| GET | `/admin/business-metrics` | MRR, ARR, churn, LTV, trial conversion, growth, revenue trend |
| GET | `/admin/webhooks` | Dead-letter queue with retry button |
| POST | `/admin/webhooks/retry` | Retry all failed Stripe webhook events |
| POST | `/admin/reset-demo` | Reset all demo data to clean state |

## Health & Monitoring

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Basic health (DB, cache, queue, webhook events) |
| GET | `/health/detailed` | Component-level health (DB, Redis, Queue, Stripe, Email) |
| GET | `/metrics` | Prometheus text format metrics |

## Interactive Documentation

Open http://localhost:5000/apidocs/ for Swagger UI (when running).
