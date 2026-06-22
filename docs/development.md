# Development Guide

## Getting Started

### Prerequisites
- Python 3.13+
- Redis 7+ (optional for local SQLite mode)

### Quick Start (SQLite)

```bash
git clone <url> && cd SaaSForge
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py
flask db upgrade    # Apply all 8 migration revisions
flask seed-data     # Create admin + demo users
```

Opens at http://localhost:5000 with admin@saasforge.com / Admin123!

### Quick Start (Full Stack)

```bash
docker-compose up -d
docker-compose exec web flask db upgrade
docker-compose exec web flask seed-data
```

## Demo Environment

Run with demo mode to prevent destructive actions:

```bash
DEMO_MODE=true python run.py
flask seed-demo-data
```

This creates 4 accounts:

| Email | Password | Role | Org | Plan |
|-------|----------|------|-----|------|
| admin@saasforge.com | Admin123! | Site Admin | SaaSForge Admin | Business |
| demo@saasforge.com | Demo123! | Org Owner | Demo Company | Pro |
| manager@saasforge.com | Manager123! | Org Admin | Demo Company | Pro |
| member@saasforge.com | Member123! | Member | Demo Company | Pro |

The demo banner appears on all pages. Admin can reset all demo data via the button in the banner or `/admin/reset-demo`.

## Observability (Local)

Structured JSON logging is active by default. To see logs in human-readable format:

```bash
LOG_FORMAT=text python run.py
```

Metrics are available at `http://localhost:5000/metrics`. Health checks at `/health` and `/health/detailed`.

## PostgreSQL Features

To use PostgreSQL-specific features (JSONB, GIN indexes, FTS, materialized views):

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/saasforge
flask db upgrade
python run.py
```

On SQLite, all PG features are gracefully skipped (no-op with INFO logs).

## Performance Monitoring

The `@monitor_query()` decorator tracks slow service methods. Add it to any service method:

```python
from app.services.performance_service import monitor_query

class MyService:
    @monitor_query(name="my_service.slow_thing", threshold_ms=200)
    def slow_thing(self):
        ...
```

View results at `/admin/performance`.

## Testing

```bash
pytest                        # All tests
pytest -v                     # Verbose
pytest -k "performance"       # Filter by keyword
pytest --cov=app --cov-report=html  # Coverage
```

Tests use SQLite in-memory. No external services required.

### Writing Tests

Fixtures available in `conftest.py`:
- `app` — Flask app with TestConfig
- `client` — test client
- `db` — clean DB per test (savepoint rollback)
- `registered_user` — pre-created user
- `organization` — pre-created org with owner

## Code Style

```bash
ruff check .                  # Lint
ruff format .                 # Format
mypy app --ignore-missing-imports  # Type check
```

## Architecture Decisions

See `docs/adr/index.md` for recorded decisions on service layer, multi-tenancy, and caching.
