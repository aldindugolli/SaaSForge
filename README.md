# SaaSForge 🚀

**A Production-Ready Multi-Tenant SaaS Platform + AI Knowledge Base Product**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black.svg)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen)](https://pre-commit.com/)

---

## Overview

SaaSForge is a complete, production-ready SaaS platform built with Flask. It handles the hard parts of SaaS — multi-tenancy, authentication, Stripe billing, RBAC, API keys, background jobs, caching — so you can build products on top of it instead of rebuilding infrastructure.

**The platform is feature-complete.** To prove its value, an **AI Knowledge Base** product has been built on top of it, demonstrating how SaaSForge accelerates real product development.

### What Makes This Different

Most SaaS boilerplates stop at infrastructure. SaaSForge goes further — it ships with a complete, working product that shows how to use every platform feature.

| Platform Feature | Knowledge Base Product Integration |
|-----------------|-----------------------------------|
| Authentication | Login, OAuth, 2FA protection |
| Organizations | Org-scoped documents and collections |
| Billing | Entitlements control document/search limits per plan |
| RBAC | Role-based document management |
| Notifications | Alerts on document uploads |
| API | REST API for all knowledge operations |
| Analytics | Usage tracking (documents, searches, tokens) |
| Background Jobs | Async document processing and embedding |
| Audit Logging | Complete document CRUD audit trail |

---

## Screenshots

> *Screenshots can be added to `docs/screenshots/` directory*

| | |
|---|---|
| **Knowledge Base Dashboard** | **Document Management** |
| Overview with stats, recent docs, conversations | Filter, search, upload, and manage documents |
| **AI Chat Interface** | **Usage Analytics** |
| Chat with documents, citation support | Track usage metrics per plan |

---

## Features

### Platform (23 Infrastructure Features)

| Category | Features |
|----------|---------|
| **Authentication** | Email/password, Google OAuth, TOTP 2FA, session management, password reset, email verification |
| **Multi-Tenancy** | Organizations, team members, role-based access (Owner/Admin/Member), invitations |
| **Billing** | Stripe Checkout, Customer Portal, webhooks (6 events), invoices, subscription lifecycle, plan entitlements |
| **API Platform** | Scoped API keys (14 permissions), usage limits, rate limiting, request logging, Swagger docs |
| **Infrastructure** | PostgreSQL, Redis caching, RQ background jobs, Docker, Nginx, Gunicorn+Gevent |
| **Observability** | Structured JSON logging, correlation IDs, Prometheus metrics, health checks, Sentry |
| **Admin** | User management, org management, subscription oversight, audit logs, performance monitoring, impersonation |
| **Business Metrics** | MRR, ARR, churn rate, LTV, trial conversion, revenue trends, user growth |
| **Security** | 2FA, audit trails, session tracking, API key auth, CSRF protection, rate limiting |

### Product: AI Knowledge Base (10 Features)

| Feature | Description |
|---------|-------------|
| **Document Upload** | PDF, DOCX, TXT, Markdown — org-scoped storage |
| **Collections** | Organize documents into themed collections |
| **Text Extraction** | Automatic text extraction and chunking |
| **Full-Text Search** | Search across all document content |
| **Semantic Search** | AI-powered embedding-based similarity search |
| **AI Chat** | Chat with documents (OpenAI or mock provider) |
| **Citation Support** | AI responses cite specific document sources |
| **Conversation History** | Persistent chat threads per document |
| **Usage Analytics** | Track documents, searches, messages, tokens |
| **Entitlement Gating** | Free (100 docs), Pro (5,000), Business (50,000) |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.13, Flask 3.x, SQLAlchemy 2.x, Alembic |
| **Database** | PostgreSQL 16 (prod), SQLite (dev) |
| **Cache/Queue** | Redis 7, Flask-RQ2, RQ Scheduler |
| **Frontend** | Jinja2, TailwindCSS 3.x, HTMX 2.x, Alpine.js 3.x, Chart.js 4.x |
| **Payments** | Stripe (Checkout, Customer Portal, Webhooks, Invoices) |
| **Auth** | bcrypt, pyotp (TOTP), Authlib (Google OAuth) |
| **AI** | OpenAI API (configurable, mock fallback) |
| **Infrastructure** | Docker, docker-compose, Nginx, Gunicorn + Gevent |
| **Monitoring** | Prometheus, Sentry, structured logging |
| **Dev Tools** | ruff, mypy, pre-commit, pytest, coverage |

---

## Quick Start

### Prerequisites

- Python 3.13+
- Docker & Docker Compose (recommended)
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)

### Clone & Setup

```bash
git clone https://github.com/aldindugolli/SaaSForge.git
cd SaaSForge
cp .env.example .env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run with Docker (Recommended)

```bash
docker compose up --build
```

This starts: web (Flask), worker (RQ), scheduler (RQ), PostgreSQL, Redis.

### Run Locally (SQLite)

```bash
flask run
```

The app auto-detects SQLite when no PostgreSQL `DATABASE_URL` is set.

### Seed Demo Data

```bash
flask seed-demo-data
```

### Create Admin User

```bash
flask create-admin
```

### Access

- **App**: http://localhost:5000
- **Demo Login**: `demo@saasforge.com` / `Demo123!`
- **Admin Login**: `admin@saasforge.com` / `Admin123!`

---

## Project Structure

```
app/
├── __init__.py              # Flask app factory
├── admin/                   # Admin dashboard (20+ routes)
├── analytics/               # Platform analytics
├── api/                     # REST API v1
├── auth/                    # Authentication (register, login, OAuth, 2FA)
├── billing/                 # Stripe billing integration
├── core/                    # Models, config, extensions, error handlers
├── db/                      # PostgreSQL optimizations
├── knowledge/               # 🔥 AI Knowledge Base Product Module
│   ├── models.py            #   Document, Collection, Chunk, Conversation, Message
│   ├── services.py          #   Upload, search, AI chat, usage tracking
│   ├── routes.py            #   Web UI (10 pages)
│   ├── api.py               #   REST API (9 endpoints)
│   ├── jobs.py              #   Background document processing
│   └── templates/           #   Jinja2 templates (9 files)
├── notifications/           # In-app notifications
├── organizations/           # Multi-tenant org management
├── security/                # Security center
├── services/                # 20 service classes
│   ├── auth_service.py      #   Authentication logic
│   ├── billing_service.py   #   Stripe integration
│   ├── entitlement_service.py # Plan-based feature gating
│   ├── api_platform.py      #   API key auth, scopes, rate limits
│   └── ...
├── static/                  # CSS, JS
├── templates/               # 55+ Jinja2 templates
└── webhooks/                # Customer webhook delivery
├── docs/                    # Architecture docs, diagrams, case study
├── migrations/              # Alembic database migrations
├── tests/                   # 13 test files, ~1,000 assertions
├── docker-compose.yml       # Development: 5 services
├── docker-compose.prod.yml  # Production: 6 services (adds Nginx)
├── Dockerfile               # Multi-stage build, Python 3.13-slim
├── wsgi.py                  # Production entry point
└── run.py                   # Development entry point
```

---

## API Documentation

The REST API is available at `/api/v1/` with scoped API key authentication.

### Endpoints

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| GET | `/api/v1/` | None | API status |
| GET | `/api/v1/me` | `read:users` | Current user |
| GET | `/api/v1/organizations` | `read:organizations` | List orgs |
| GET | `/api/v1/organizations/<id>` | `read:organizations` | Org details |
| GET | `/api/v1/organizations/<id>/members` | `read:organizations` | Org members |
| GET | `/api/v1/knowledge/documents` | `knowledge:read` | List documents |
| POST | `/api/v1/knowledge/documents` | `knowledge:write` | Upload document |
| GET | `/api/v1/knowledge/documents/<id>` | `knowledge:read` | Document detail |
| DELETE | `/api/v1/knowledge/documents/<id>` | `knowledge:write` | Delete document |
| GET | `/api/v1/knowledge/search` | `knowledge:read` | Search documents |
| POST | `/api/v1/knowledge/chat` | `knowledge:write` | Create chat |
| POST | `/api/v1/knowledge/chat/<id>/send` | `knowledge:write` | Send message |
| GET | `/api/v1/knowledge/collections` | `knowledge:read` | List collections |

### Authentication

```
X-API-Key: sf_your_api_key_here
```

Generate API keys from the web interface or via `POST /api/v1/keys`.

---

## Deployment

### Docker Production

```bash
docker compose -f docker-compose.prod.yml up --build
```

### Railway

1. Connect your GitHub repository
2. Set environment variables from `.env.example`
3. Deploy — `railway.json` is preconfigured

### Environment Variables

Key variables (see `.env.example` for full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `STRIPE_SECRET_KEY` | — | Stripe API key |
| `GOOGLE_OAUTH_CLIENT_ID` | — | Google OAuth |
| `SENDGRID_API_KEY` | — | Email delivery |
| `AI_PROVIDER` | `mock` | AI provider (`mock` or `openai`) |
| `OPENAI_API_KEY` | — | OpenAI API key (if using OpenAI) |
| `DEMO_MODE` | `false` | Enable demo safety middleware |

---

## Architecture

### Layered Design

```
Browser (HTMX + Tailwind + Alpine.js)
    │
    ▼
Nginx Reverse Proxy
    │
    ▼
Gunicorn (4 gevent workers)
    │
    ▼
Flask App (11 Blueprints)
    │
    ├── Route Layer (controllers)
    ├── Service Layer (business logic) — 20 services
    ├── Data Layer (SQLAlchemy models) — 24 tables
    └── Infrastructure (PostgreSQL + Redis + RQ)
```

### Architecture Diagrams

See [docs/product-architecture.md](docs/product-architecture.md) for Mermaid-based architecture diagrams covering:

- Platform architecture
- Product architecture
- Request lifecycle
- Authentication flow
- Billing flow

---

## Case Study

See [docs/case-study.md](docs/case-study.md) for the full engineering case study covering:

- Problem statement
- Architecture decisions
- Technical challenges
- Results and metrics
- Lessons learned

---

## Platform Reuse

See [docs/platform-reuse.md](docs/platform-reuse.md) for documentation on how the Knowledge Base product reuses every major platform service.

---

## License

MIT — see [LICENSE](LICENSE)

---

## About

Built by [Aldin Dugolli](https://github.com/aldindugolli). 

This project demonstrates senior-level Flask development, SaaS architecture, Stripe billing integration, security engineering, API platform design, DevOps deployment, and product engineering — all in one repository.
