# API Reference

The SaaSForge REST API provides programmatic access to user data, organizations, and administrative functions. All API endpoints are versioned under `/api/v1`.

---

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Errors](#errors)
- [Interactive Documentation](#interactive-documentation)
- [Endpoints](#endpoints)
  - [API Status](#api-status)
  - [User Profile](#user-profile)
  - [Organizations](#organizations)
  - [Organization Members](#organization-members)
  - [API Keys](#api-keys)
  - [Admin Stats](#admin-stats)
- [API Key Management](#api-key-management)
- [Request Logging](#request-logging)

---

## Base URL

```
http://localhost:5000/api/v1
```

In production, replace with your domain:

```
https://yourdomain.com/api/v1
```

---

## Authentication

### API Key Authentication

Most endpoints require authentication via an API key sent in the `X-API-Key` header:

```bash
curl -H "X-API-Key: sf_your_api_key" http://localhost:5000/api/v1/me
```

API keys:
- Are prefixed with `sf_` for easy identification
- Are hashed with SHA-256 before storage (never stored in plaintext)
- Support scoping to specific permissions
- Can be active or revoked (revoked keys are immediately rejected)

### Session Authentication

Some endpoints (API key management) require session-based authentication via cookies:

```bash
curl -b "session=your_session_cookie" http://localhost:5000/api/v1/keys
```

### Admin Authentication

The admin stats endpoint requires both an API key and admin privileges:

```bash
curl -H "X-API-Key: sf_admin_api_key" http://localhost:5000/api/v1/admin/stats
```

### Unauthenticated Endpoints

The root API endpoint (`GET /api/v1/`) requires no authentication and provides API metadata.

---

## Rate Limiting

Rate limits are enforced per API key:

| Tier | Default Limit |
|------|---------------|
| Default | 100 requests/hour |

Configure via environment variables:
- `RATELIMIT_DEFAULT` — default rate limit string (e.g., `100/hour`)
- `RATELIMIT_STORAGE_URL` — Redis URL for rate limit counters

When rate limited, the API returns:

```json
{
    "error": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again in X seconds."
}
```

Status code: `429 Too Many Requests`

---

## Errors

### Error Response Format

```json
{
    "error": "error_code",
    "message": "Human-readable error description"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 401 | Missing or invalid API key |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### Error Codes

| Code | Meaning |
|------|---------|
| `invalid_api_key` | API key is missing, invalid, or revoked |
| `forbidden` | Insufficient permissions for this resource |
| `not_found` | Requested resource does not exist |
| `validation_error` | Request data failed validation |
| `rate_limit_exceeded` | Too many requests |
| `internal_error` | Unexpected server error |

---

## Interactive Documentation

OpenAPI (Swagger) documentation is available at:

```
http://localhost:5000/apidocs/
```

The interactive UI provides:
- Request/response schemas for all 9 documented endpoints
- Try-it-out functionality with real API calls
- Authentication setup (API key and session)
- Code samples in multiple languages

---

## Endpoints

### API Status

```
GET /api/v1/
```

Returns API metadata. No authentication required.

**Response:**
```json
{
    "name": "SaaSForge API",
    "version": "1.0",
    "status": "operational"
}
```

---

### User Profile

```
GET /api/v1/me
```

Returns the authenticated user's profile and organization memberships. Requires API key authentication.

**Response:**
```json
{
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "name": "John Doe",
        "avatar_url": null,
        "created_at": "2026-01-15T10:30:00Z"
    },
    "organizations": [
        {
            "id": "uuid",
            "name": "Acme Corp",
            "role": "owner",
            "subscription_tier": "pro",
            "member_count": 5,
            "max_members": 10
        }
    ]
}
```

---

### Organizations

#### List Organizations

```
GET /api/v1/organizations
```

Returns all organizations the authenticated user belongs to.

**Response:**
```json
{
    "organizations": [
        {
            "id": "uuid",
            "name": "Acme Corp",
            "slug": "acme-corp",
            "role": "owner",
            "member_count": 5,
            "subscription_tier": "pro",
            "subscription_status": "active"
        }
    ]
}
```

#### Get Organization

```
GET /api/v1/organizations/:id
```

Returns details for a specific organization.

**Response:**
```json
{
    "organization": {
        "id": "uuid",
        "name": "Acme Corp",
        "slug": "acme-corp",
        "description": "A sample organization",
        "website": "https://acme.com",
        "member_count": 5,
        "subscription_tier": "pro",
        "subscription_status": "active",
        "created_at": "2026-01-15T10:30:00Z"
    }
}
```

---

### Organization Members

```
GET /api/v1/organizations/:id/members
```

Returns all members of the specified organization.

**Response:**
```json
{
    "members": [
        {
            "id": "uuid",
            "user_id": "uuid",
            "name": "John Doe",
            "email": "john@acme.com",
            "role": "owner",
            "joined_at": "2026-01-15T10:30:00Z"
        },
        {
            "id": "uuid",
            "user_id": "uuid",
            "name": "Jane Smith",
            "email": "jane@acme.com",
            "role": "member",
            "joined_at": "2026-02-20T14:00:00Z"
        }
    ]
}
```

---

### API Keys

API key management endpoints require session-based authentication (not API key).

#### List API Keys

```
GET /api/v1/keys
```

Returns all API keys for the authenticated user.

**Response:**
```json
{
    "keys": [
        {
            "id": "uuid",
            "name": "Development Key",
            "key_prefix": "sf_a1b2c3d4",
            "key_type": "test",
            "is_active": true,
            "last_used_at": "2026-06-21T15:00:00Z",
            "created_at": "2026-01-15T10:30:00Z"
        }
    ]
}
```

**Note:** The full API key value is only shown at creation time. The list endpoint shows only the prefix for identification.

#### Create API Key

```
POST /api/v1/keys
```

Creates a new API key.

**Request:**
```
Content-Type: application/x-www-form-urlencoded

name=My API Key&key_type=test
```

**Response:**
```json
{
    "key": {
        "id": "uuid",
        "name": "My API Key",
        "key": "sf_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p",
        "key_prefix": "sf_a1b2c3d4",
        "key_type": "test",
        "is_active": true,
        "created_at": "2026-06-22T12:00:00Z"
    }
}
```

**Important:** The full API key value is returned only in this response. Store it securely — it cannot be retrieved later.

#### Revoke API Key

```
POST /api/v1/keys/:id/revoke
```

Revokes an API key, immediately invalidating it.

**Response:**
```json
{
    "message": "API key revoked"
}
```

---

### Admin Stats

```
GET /api/v1/admin/stats
```

Returns admin dashboard statistics. Requires API key authentication AND admin privileges.

**Response:**
```json
{
    "stats": {
        "total_users": 150,
        "total_organizations": 45,
        "total_subscriptions": 30,
        "monthly_revenue": 2999.00,
        "active_users_last_30_days": 85,
        "new_users_this_month": 12
    }
}
```

---

## API Key Management

### How API Keys Work

1. **Creation:** A new key is generated with the prefix `sf_` followed by a random hex string
2. **Storage:** The full key is SHA-256 hashed before storage. The hash is what's compared on authentication
3. **Prefix:** The first 8 characters after `sf_` are stored as `key_prefix` for identification in the UI
4. **Reveal:** The full key is shown exactly once, at creation time
5. **Revocation:** Revoked keys are immediately rejected. They remain in the database for audit purposes but marked as inactive

### Creating an API Key

You can create API keys through:
- **API:** `POST /api/v1/keys` (session auth required)
- **UI:** Navigate to your security dashboard at `/security/`

### Using an API Key

```bash
# Set your key
API_KEY="sf_your_full_api_key"

# Make authenticated requests
curl -H "X-API-Key: $API_KEY" http://localhost:5000/api/v1/me
curl -H "X-API-Key: $API_KEY" http://localhost:5000/api/v1/organizations
```

### Example: Full Workflow

```bash
# 1. Create an API key (needs session cookie)
curl -X POST http://localhost:5000/api/v1/keys \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=Production Key&key_type=live" \
  -b "session=your_session_cookie"

# Response includes the full key:
# {"key": "sf_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p"}

# 2. Use the key
export SF_API_KEY="sf_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p"

curl -H "X-API-Key: $SF_API_KEY" http://localhost:5000/api/v1/me
curl -H "X-API-Key: $SF_API_KEY" http://localhost:5000/api/v1/organizations
curl -H "X-API-Key: $SF_API_KEY" http://localhost:5000/api/v1/organizations/uuid/members

# 3. Revoke when no longer needed
curl -X POST http://localhost:5000/api/v1/keys/uuid/revoke \
  -b "session=your_session_cookie"
```

---

## Request Logging

All API requests are automatically logged to the `api_request_logs` table:

| Field | Description |
|-------|-------------|
| `method` | HTTP method (GET, POST) |
| `endpoint` | Requested path |
| `status_code` | Response status code |
| `response_time_ms` | Request duration in milliseconds |
| `ip_address` | Client IP address |
| `user_agent` | Client user agent string |
| `api_key_id` | API key used (if applicable) |
| `organization_id` | Organization context (if applicable) |

Logs are viewable in the admin dashboard at `/admin/api-stats`.
