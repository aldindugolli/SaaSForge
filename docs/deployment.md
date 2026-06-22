# Deployment Guide

Guide for deploying SaaSForge to production environments including Railway, Docker-based VPS, and manual deployment.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Railway Deployment](#railway-deployment)
- [Docker VPS Deployment](#docker-vps-deployment)
- [Manual VPS Deployment](#manual-vps-deployment)
- [Production Architecture](#production-architecture)
- [Nginx Configuration](#nginx-configuration)
- [Health Checks](#health-checks)
- [Monitoring](#monitoring)
- [Database Backups](#database-backups)
- [Scaling](#scaling)

---

## Prerequisites

### Required Services

| Service | Purpose | Production Grade |
|---------|---------|-----------------|
| PostgreSQL 16+ | Primary database | RDS, Cloud SQL, Supabase, Railway |
| Redis 7+ | Cache, sessions, job queue | Upstash, Redis Cloud, Railway |
| Stripe account | Payment processing | Live mode keys |
| SendGrid account | Email delivery | Verified sender |
| Google OAuth credentials | Social login | (Optional) |

### Production Checklist

- [ ] Domain name pointed to your server
- [ ] SSL certificate (via Nginx/Caddy or platform)
- [ ] PostgreSQL database provisioned
- [ ] Redis instance provisioned
- [ ] Stripe live mode API keys
- [ ] SendGrid verified sender
- [ ] `SECRET_KEY` set to a secure random value
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] Database migrations applied
- [ ] Background workers running
- [ ] Health checks configured
- [ ] Error monitoring (Sentry) configured

---

## Environment Variables

### Required

| Variable | Example | Source |
|----------|---------|--------|
| `SECRET_KEY` | `openssl rand -hex 32` | Generate |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/saasforge` | DB provider |
| `REDIS_URL` | `redis://user:pass@host:6379/0` | Redis provider |
| `STRIPE_SECRET_KEY` | `sk_live_...` | Stripe dashboard |
| `STRIPE_PUBLISHABLE_KEY` | `pk_live_...` | Stripe dashboard |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Stripe webhook setup |
| `STRIPE_PRO_PRICE_ID` | `price_...` | Stripe product config |
| `STRIPE_BUSINESS_PRICE_ID` | `price_...` | Stripe product config |
| `MAIL_DEFAULT_SENDER` | `noreply@yourdomain.com` | SendGrid verified sender |

### Recommended

| Variable | Purpose | Default |
|----------|---------|---------|
| `SENTRY_DSN` | Error tracking | (none) |
| `GOOGLE_OAUTH_CLIENT_ID` | Social login | (none) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Social login | (none) |
| `SENDGRID_API_KEY` | Email delivery | (none) |
| `APP_NAME` | Branding in templates | SaaSForge |
| `APP_URL` | Base URL for links | http://localhost:5000 |
| `APP_DOMAIN` | Domain for cookies | localhost:5000 |
| `ADMIN_EMAIL` | Admin contact | admin@saasforge.com |
| `RATELIMIT_DEFAULT` | Default rate limit | 100/hour |
| `PERMANENT_SESSION_LIFETIME` | Session duration | 2592000 (30 days) |
| `SESSION_COOKIE_SECURE` | Secure cookies | False (set True in prod) |

---

## Railway Deployment

Railway is the recommended deployment platform with zero-config support.

### Steps

```bash
# 1. Install Railway CLI
curl -fsSL https://railway.app/install.sh | sh

# 2. Login
railway login

# 3. Initialize (if not already)
railway init

# 4. Deploy
railway up
```

### Configuration

The included `railway.json` configures:
- Dockerfile builder
- 1 replica
- Healthcheck on `/`

### Environment Setup

Set environment variables in the Railway dashboard:
1. Navigate to your project → Variables
2. Add all required environment variables
3. Railway auto-generates a `DATABASE_URL` and `REDIS_URL` if you add PostgreSQL and Redis plugins

### Domains

```bash
railway domain           # View domains
railway domain -d yourdomain.com  # Custom domain
```

### Stripe Webhook

1. In Stripe dashboard → Webhooks → Add endpoint
2. URL: `https://your-app.railway.app/billing/webhook`
3. Events to send:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
4. Copy the webhook signing secret and set as `STRIPE_WEBHOOK_SECRET`

---

## Docker VPS Deployment

### Production Docker Compose

```bash
# 1. Clone on server
git clone https://github.com/aldindugolli/SaaSForge.git
cd SaaSForge

# 2. Create production env file
cat > .env.prod << EOF
SECRET_KEY=<random-64-char-hex>
DATABASE_URL=postgresql://postgres:postgres@db:5432/saasforge
REDIS_URL=redis://redis:6379/0
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_BUSINESS_PRICE_ID=price_...
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
SENDGRID_API_KEY=...
APP_URL=https://yourdomain.com
APP_DOMAIN=yourdomain.com
SESSION_COOKIE_SECURE=True
SENTRY_DSN=https://...
EOF

# 3. Start all services
docker-compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# 5. Seed data (first time only)
docker-compose -f docker-compose.prod.yml exec web flask seed-data
```

### Production File

The `docker-compose.prod.yml` extends the dev compose with:
- Nginx reverse proxy (SSL termination, static files, gzip)
- Production env file (`.env.prod`)
- No volume mounts for code (uses built image)
- Restart policies

### Checking Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f worker
```

### Updating

```bash
git pull
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec web flask db upgrade
```

---

## Manual VPS Deployment

### Prerequisites

Ubuntu 22.04+ with:
- Python 3.13+
- PostgreSQL 16+
- Redis 7+
- Nginx
- Supervisor or systemd

### Steps

```bash
# 1. Install system dependencies
sudo apt update
sudo apt install -y python3.13 python3.13-venv postgresql redis-server nginx

# 2. Clone repository
git clone https://github.com/aldindugolli/SaaSForge.git /opt/saasforge
cd /opt/saasforge

# 3. Create virtual environment
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with production values

# 5. Set up PostgreSQL
sudo -u postgres createuser saasforge -P
sudo -u postgres createdb saasforge -O saasforge

# 6. Run migrations
flask db upgrade

# 7. Seed data
flask seed-data

# 8. Test the app
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent wsgi:app
```

### Supervisor Configuration

```ini
[program:saasforge-web]
command=/opt/saasforge/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --timeout 120 wsgi:app
directory=/opt/saasforge
user=www-data
autostart=true
autorestart=true
environment=PATH="/opt/saasforge/venv/bin"

[program:saasforge-worker]
command=/opt/saasforge/venv/bin/rq worker --url redis://localhost:6379/0 saasforge-jobs
directory=/opt/saasforge
user=www-data
autostart=true
autorestart=true

[program:saasforge-scheduler]
command=/opt/saasforge/venv/bin/rq scheduler
directory=/opt/saasforge
user=www-data
autostart=true
autorestart=true
```

---

## Production Architecture

```
                         Internet
                            │
                            ▼
                      ┌──────────┐
                      │  Nginx   │  Port 443 (HTTPS)
                      │  (SSL)   │  Static files, reverse proxy
                      └────┬─────┘
                           │
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
            ┌────────────┐  ┌────────┐
            │  Gunicorn  │  │ Static │
            │  (4 gevent │  │ Files  │
            │  workers)  │  └────────┘
            └─────┬──────┘
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
    ┌──────────┐    ┌──────────┐
    │PostgreSQL│    │  Redis   │
    │   (DB)   │    │(cache +  │
    └──────────┘    │  queue)  │
                    └──────────┘
                         │
                    ┌────┴────┐
                    │         │
                    ▼         ▼
              ┌────────┐ ┌──────────┐
              │ Worker │ │Scheduler │
              │  (RQ)  │ │ (RQ)     │
              └────────┘ └──────────┘
```

### Component Roles

| Component | Role | Scaling |
|-----------|------|---------|
| **Nginx** | SSL termination, static files, reverse proxy | Vertical |
| **Gunicorn** | WSGI server, 4 gevent workers | Horizontal |
| **Worker** | RQ job execution, 1+ instances | Horizontal |
| **Scheduler** | Recurring job scheduling, 1 instance | Single |
| **PostgreSQL** | Primary database | Vertical / Read replicas |
| **Redis** | Cache (sessions, analytics), job queue | Vertical / Cluster |

---

## Nginx Configuration

A minimal production Nginx config is included at `docker/nginx.conf`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://web:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Health Checks

### Application Health Endpoint

`GET /health` returns:

```json
{
    "status": "healthy",
    "database": "connected",
    "cache": "connected",
    "timestamp": "2026-06-22T12:00:00Z"
}
```

### Docker Healthcheck

The Dockerfile includes:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1
```

### Railway Healthcheck

The `railway.json` configures healthcheck on `/`.

---

## Monitoring

### Sentry Error Tracking

1. Create a project in [sentry.io](https://sentry.io)
2. Set `SENTRY_DSN` environment variable
3. Errors are automatically captured and reported

### Application Logs

Production logs are output to stdout/stderr (gunicorn access + error logs). In Docker:

```bash
docker-compose logs -f web
docker-compose logs -f worker
```

### Health Monitoring

- The `/health` endpoint checks DB + cache connectivity
- Docker HEALTHCHECK runs every 30 seconds
- Platform-level health checks (Railway, Docker)

---

## Database Backups

### PostgreSQL (Docker)

```bash
# Manual backup
docker exec -t saasforge_db_1 pg_dump -U postgres saasforge > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i saasforge_db_1 psql -U postgres saasforge < backup.sql
```

### Automated Backups

Add a cron job:

```bash
0 2 * * * docker exec -t saasforge_db_1 pg_dump -U postgres saasforge | gzip > /backups/saasforge_$(date +\%Y\%m\%d).sql.gz
```

### Railway Backups

Railway PostgreSQL automatically creates daily backups with 7-day retention.

---

## Scaling

### Web Workers

Increase gunicorn workers in `docker-compose.prod.yml`:

```yaml
command: gunicorn --bind 0.0.0.0:5000 --workers 8 --worker-class gevent --timeout 120 wsgi:app
```

General formula: `(2 × CPU cores) + 1`

### Background Workers

Add additional worker containers for high job volume:

```yaml
worker-2:
    build: .
    command: rq worker --url redis://redis:6379/0 saasforge-jobs
    # ...
```

### Database

- Vertical scaling: larger PostgreSQL instance
- Read replicas for analytics queries
- Connection pooling via PgBouncer for high connection counts

### Redis

- Vertical scaling for cache
- Redis Cluster for distributed caching
- Separate Redis instances for cache vs queue (different persistence needs)
