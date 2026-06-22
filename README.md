# SaaSForge 🚀

A production-ready Flask SaaS boilerplate with authentication, team management, subscription billing, analytics, and more.

## Features

- **Authentication** — Email/password & Google OAuth with email verification, password reset
- **Multi-Tenant Organizations** — Teams with roles (Owner, Admin, Member) and invitations
- **Subscription Billing** — Stripe integration with checkout, customer portal, webhooks
- **Admin Dashboard** — User management, subscription overview, audit logs, analytics
- **Analytics** — User growth, revenue tracking, subscription distribution
- **Background Jobs** — Redis-backed workers for email, webhooks, data processing
- **REST API** — Versioned API with API keys, rate limiting, usage tracking
- **Notifications** — In-app and email notifications
- **Feature Flags** — Global, organization, and user-level flags
- **Audit Logging** — Track all critical actions with searchable logs
- **RBAC** — Role-based access control with reusable decorators
- **Dark Mode** — Full light/dark theme support
- **Responsive** — Mobile-first design with TailwindCSS

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.13+, Flask, SQLAlchemy |
| Frontend | HTMX, Alpine.js, TailwindCSS |
| Database | PostgreSQL |
| Cache | Redis |
| Payments | Stripe |
| Auth | bcrypt, Authlib |
| Tasks | RQ (Redis Queue) |
| Infrastructure | Docker, Docker Compose |
| CI/CD | GitHub Actions |

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 16+
- Redis 7+
- Stripe account (for billing features)

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/saasforge.git
cd saasforge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
flask db upgrade

# Seed demo data
flask seed-data

# Run the development server
flask run
```

### Docker Development

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec web flask db upgrade

# Seed data
docker-compose exec web flask seed-data

# View logs
docker-compose logs -f web
```

Access the application at http://localhost:5000

### Demo Credentials

After running `flask seed-data`:

| Email | Password | Role |
|-------|----------|------|
| admin@saasforge.com | Admin123! | Admin |
| demo@saasforge.com | Demo123! | User |

## Project Structure

```
saasforge/
├── app/
│   ├── admin/          # Admin dashboard
│   ├── analytics/      # Analytics module
│   ├── api/            # REST API
│   ├── auth/           # Authentication
│   ├── billing/        # Stripe billing
│   ├── core/           # Config, models, extensions
│   ├── notifications/  # Notification system
│   ├── organizations/  # Team management
│   ├── services/       # Business logic layer
│   ├── static/         # CSS, JS, images
│   └── templates/      # Jinja2 templates
├── tests/              # Unit & integration tests
├── migrations/         # Alembic migrations
├── docker/             # Docker assets
├── scripts/            # Utility scripts
├── docs/               # Documentation
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Architecture

### Service Layer Pattern

Business logic is isolated in the `app/services/` layer:

- **Presentation** — Flask routes & HTMX endpoints
- **Service** — Business logic, domain rules, billing, permissions
- **Data** — SQLAlchemy models & database access
- **Infrastructure** — Email, Redis, Stripe, external APIs

### Multi-Tenancy

Organizations provide data isolation:

```
Organization
├── Owner (full access)
├── Admin (management access)
└── Member (basic access)
```

## API Documentation

The REST API is available at `/api/v1/`.

### Authentication

Include your API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: sf_your_api_key" http://localhost:5000/api/v1/me
```

### Endpoints

- `GET /api/v1/me` — Current user info
- `GET /api/v1/organizations` — List organizations
- `GET /api/v1/organizations/:id` — Organization details
- `GET /api/v1/organizations/:id/members` — Organization members
- `GET/POST /api/v1/keys` — API key management

## Deployment

### Railway

```bash
railway login
railway up
```

Set environment variables in Railway dashboard.

### VPS (Docker)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables

See `.env.example` for all configuration options.

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth_service.py -v
```

## License

MIT
# SaaSForge
