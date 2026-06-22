# ADR-001: Service-Layer Architecture

**Status:** Accepted  
**Date:** 2026-06-22  
**Deciders:** Architecture Team  

## Context
The application needs a clean separation between HTTP controllers and business logic to support testability, reusability, and future API expansion.

## Decision
Use a thin-controller, fat-service pattern:
- **Blueprints/routes** handle HTTP concerns (parsing, validation, response format, flash messages).
- **Service classes** encapsulate all business logic, database operations, and cross-cutting concerns (caching, auditing, notifications).
- Services raise typed exceptions (`ValidationError`, `PermissionError`, `NotFoundError`, `ServiceError`) that controllers catch.

## Consequences
- Controllers remain ~30-50 lines; services contain the bulk of logic.
- New API endpoints (JSON) and existing HTML routes share the same service layer.
- Services are easily unit-testable without Flask request context.

---

# ADR-002: Multi-Tenant Organization Model

**Status:** Accepted  
**Date:** 2026-06-22  

## Context
The platform must support multiple organizations per user with isolated data.

## Decision
- `Organization` is the tenant boundary.
- `Membership` links `User` ↔ `Organization` with a `role` (owner/admin/member).
- All domain models (subscriptions, invoices, audit logs, feature flags) reference `organization_id`.
- Queries always filter by `organization_id` for tenant isolation.

## Consequences
- Simple, explicit tenant isolation at the query level.
- Users can belong to multiple orgs; `is_current` flag on membership tracks active org.
- No shared-nothing DB per tenant — simpler ops at the cost of slightly larger tables.

---

# ADR-003: Caching Strategy

**Status:** Accepted  
**Date:** 2026-06-22  

## Context
Dashboard and analytics queries are expensive; Redis is available in production but not always in local dev.

## Decision
- `RedisCache` class wraps Redis with automatic in-memory fallback.
- Analytics are cached with 5-minute TTL under the `analytics:*` namespace.
- Cache is invalidated on any data mutation (user registration, org changes, subscription updates).

## Consequences
- Analytics queries return instantly for 5 minutes after first computation.
- Local development works without Redis (in-memory fallback).
- Invalidation uses pattern deletion (`analytics:*`) — coarse but correct.
