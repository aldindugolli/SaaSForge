# Deployment Guide

## Docker Compose (Production)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Services: web (gunicorn), worker (RQ), scheduler (RQ Scheduler), db (PostgreSQL 16), redis (Redis 7), nginx.

Required environment variables in `.env.prod`:

```env
SECRET_KEY=<random-64-char-string>
DATABASE_URL=postgresql://postgres:postgres@db:5432/saasforge
REDIS_URL=redis://redis:6379/0
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_xxx
STRIPE_BUSINESS_PRICE_ID=price_xxx
APP_URL=https://yourdomain.com
APP_DOMAIN=yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
FLASK_ENV=production
SESSION_COOKIE_SECURE=True
SENDGRID_API_KEY=SG.xxx
SENTRY_DSN=https://xxx@xxx.ingest.us.sentry.io/xxx
DEMO_MODE=false
```

### Health Checks

Both Docker healthchecks and app-level endpoints are configured:

- Docker: `HEALTHCHECK --interval=30s CMD curl -f http://localhost:5000/ || exit 1`
- App: `GET /health` (DB + cache + queue), `GET /health/detailed` (5 components)
- Prometheus: `GET /metrics`

## Railway

```bash
railway login
railway up
```

A `railway.json` is included. Set environment variables in the Railway dashboard.

## Manual VPS

```bash
pip install -r requirements.txt
flask db upgrade
flask seed-data
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --timeout 120 wsgi:app
```

Recommended: use Nginx as reverse proxy with the config in `docker/nginx.conf`.

## Environment Variables Reference

| Variable | Required | Production Value |
|----------|----------|-----------------|
| `SECRET_KEY` | Yes | 64-char random string |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `STRIPE_SECRET_KEY` | Yes | Stripe live secret key |
| `STRIPE_PUBLISHABLE_KEY` | Yes | Stripe live publishable key |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | Yes | Price ID for Pro plan ($29/mo) |
| `STRIPE_BUSINESS_PRICE_ID` | Yes | Price ID for Business plan ($99/mo) |
| `APP_URL` | Yes | Full URL (https://...) |
| `APP_DOMAIN` | Yes | Domain name only |
| `SENDGRID_API_KEY` | Yes | For email delivery |
| `SENTRY_DSN` | No | Error tracking |
| `SESSION_COOKIE_SECURE` | Yes | Set to True |
| `DEMO_MODE` | No | Set to false in production |

## Database Migrations

```bash
flask db upgrade          # Apply all
flask db downgrade <rev>  # Rollback
```

The project has 8 migration revisions. Revisions `3a1b2c3d4e5f` (PostgreSQL optimizations) and `4b2c3d4e5f6a` (webhook tables) are pending and will be applied on `db upgrade`.
