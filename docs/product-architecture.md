# SaaSForge Product Architecture

## Overview

SaaSForge is a production-ready multi-tenant SaaS platform that powers custom applications. This document describes both the platform architecture and the Knowledge Base product built on top of it.

---

## Diagram 1: SaaSForge Platform Architecture

```mermaid
graph TB
    subgraph Users["Users & Authentication"]
        U[User] --> REG[Registration]
        U --> LOG[Login]
        U --> OAU[OAuth]
        U --> _2FA[2FA TOTP]
        REG --> AUTH[Auth Service]
        LOG --> AUTH
        OAU --> AUTH
        _2FA --> AUTH
    end

    subgraph Organizations["Multi-Tenant"]
        AUTH --> ORG[Organization Service]
        ORG --> MEM[Membership/RBAC]
        ORG --> INV[Invitations]
        MEM --> ROL[Role Service]
        ROL --> PERM[Permissions]
    end

    subgraph Billing["Billing & Monetization"]
        SUB[Subscription] --> STR[Stripe Checkout]
        SUB --> POR[Customer Portal]
        STR --> WEB[Stripe Webhook]
        WEB --> ENT[Entitlement Service]
        WEB --> INV
    end

    subgraph Platform["Platform Services"]
        API[API Platform] --> KEY[API Keys]
        API --> SCOPE[Scoped Permissions]
        API --> RATE[Usage Limits]
        
        NOT[Notification Service]
        AUD[Audit Service]
        ANA[Analytics Service]
        CACHE[Cache Service]
        JOB[Background Jobs/RQ]
        
        WEBHOOK[Webhook Service]
        DEMO[Demo Environment]
        IMP[Impersonation Service]
    end

    subgraph Storage["Data Layer"]
        DB[(PostgreSQL)]
        REDIS[(Redis)]
        FS[File Storage]
    end

    ORG --> DB
    Billing --> DB
    Platform --> DB
    Platform --> REDIS
    Platform --> FS
    AUTH --> DB
```

---

## Diagram 2: Knowledge Base Product Architecture

```mermaid
graph TB
    subgraph Platform["SaaSForge Platform Services"]
        AUTH[Authentication]
        ORG[Organizations]
        BILL[Billing/Entitlements]
        NOT[Notifications]
        AUD[Audit Logging]
        API[API Platform]
        ANA[Analytics]
        JOB[Background Jobs]
    end

    subgraph Product["Knowledge Base Module"]
        DOC[Document Management]
        COL[Collections]
        CHUNK[Document Processing]
        EMB[Embeddings]
        SEARCH[Search Engine]
        CHAT[AI Chat]
        USAGE[Usage Tracking]
    end

    subgraph External["External Services"]
        AI[AI Provider<br/>OpenAI / Mock]
        FS2[File Storage]
    end

    Product --> AUTH
    Product --> ORG
    Product --> BILL
    Product --> NOT
    Product --> AUD
    Product --> API
    Product --> ANA
    Product --> JOB
    
    DOC --> FS2
    DOC --> CHUNK
    CHUNK --> EMB
    EMB --> AI
    SEARCH --> EMB
    SEARCH --> AI
    CHAT --> AI
    CHAT --> SEARCH

    USAGE --> ANA
    JOB --> CHUNK
```

---

## Diagram 3: Request Lifecycle

```mermaid
sequenceDiagram
    participant B as Browser
    participant F as Flask
    participant MW as Middleware
    participant S as Service Layer
    participant DB as Database
    participant AI as AI Provider
    participant RQ as Redis Queue

    B->>F: HTTP Request
    F->>MW: Before Request
    MW->>MW: Auth Check (login_required)
    MW->>MW: Org Context
    MW->>MW: CSRF Protection
    MW->>MW: Rate Limiting
    MW->>MW: Correlation ID
    
    alt Document Upload
        B->>F: POST /knowledge/documents/upload
        F->>S: KnowledgeService.upload_document()
        S->>DB: Save document metadata
        S->>S: Validate entitlements
        S->>S: Track usage
        S->>DB: Create audit log
        S->>S: Create notifications
        S->>RQ: Queue process_document_job
        RQ-->>RQ: Async document processing
        RQ->>AI: Generate embeddings
        AI-->>RQ: Embeddings stored
        S-->>F: Return success
        F-->>B: Redirect to documents list
    end

    alt Search
        B->>F: GET /knowledge/search?q=
        F->>S: KnowledgeService.search()
        S->>DB: Query chunks & embeddings
        S->>AI: Generate query embedding
        AI-->>S: Query vector
        S->>S: Cosine similarity search
        S-->>F: Ranked results
        F-->>B: Rendered HTML
    end

    alt AI Chat
        B->>F: POST /knowledge/chat/123/send
        F->>S: KnowledgeService.send_message()
        S->>DB: Save user message
        S->>S: Search relevant chunks
        S->>AI: Chat completion + context
        AI-->>S: AI response
        S->>DB: Save AI response + citations
        S->>DB: Track usage
        S-->>F: Conversation updated
        F-->>B: Chat view with new messages
    end
```

---

## Diagram 4: Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant F as Flask App
    participant S as Auth Service
    participant DB as Database
    participant R as Redis

    rect rgb(200, 230, 255)
        Note right of U: Registration
        U->>B: Submit register form
        B->>F: POST /auth/register
        F->>S: AuthService.register()
        S->>S: Validate email/password
        S->>DB: Create User
        S->>DB: Create personal Organization
        S->>DB: Create Membership (owner)
        S->>DB: Audit log
        S->>DB: Welcome notification
        S-->>F: Success
        F-->>B: Redirect to dashboard
    end

    rect rgb(230, 255, 230)
        Note right of U: Login
        U->>B: Submit login form
        B->>F: POST /auth/login
        F->>S: AuthService.login()
        S->>DB: Verify credentials
        alt 2FA Enabled
            S-->>F: Redirect to 2FA challenge
            F->>B: TOTP challenge page
            U->>B: Enter TOTP code
            B->>F: POST /auth/2fa-challenge
            F->>S: Verify TOTP
            S-->>F: Login success
        else No 2FA
            S-->>F: Login success
        end
        F->>DB: Create UserSession
        F->>DB: Update last_login
        F-->>B: Session cookie + redirect
    end

    rect rgb(255, 230, 230)
        Note right of U: OAuth (Google)
        U->>B: Click "Login with Google"
        B->>F: GET /auth/google/login
        F->>G: Redirect to Google
        G-->>B: Auth code
        B->>F: GET /auth/google/callback
        F->>G: Exchange code for token
        G-->>F: ID token
        F->>S: Find or create user
        S-->>F: Login success
        F-->>B: Redirect to dashboard
    end

    rect rgb(255, 255, 230)
        Note right of U: Authorization
        B->>F: Request protected resource
        F->>F: @login_required
        F->>F: @org_required
        F->>F: @require_permission
        F->>DB: Check Membership.role
        F-->>B: Resource or 403
    end
```

---

## Diagram 5: Billing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant F as Flask App
    participant S as Billing Service
    participant DB as Database
    participant ST as Stripe

    rect rgb(230, 230, 255)
        Note right of U: Subscription Checkout
        U->>B: Click "Upgrade to Pro"
        B->>F: POST /billing/create-checkout-session
        F->>S: BillingService.create_checkout_session()
        S->>ST: stripe.checkout.Session.create()
        ST-->>S: Checkout URL
        S-->>F: Redirect URL
        F-->>B: 303 See Other
        B->>ST: Stripe Checkout Page
        U->>ST: Enter payment details
        ST->>ST: Process payment
        ST-->>B: Redirect to /billing/success
        B->>F: GET /billing/success
    end

    rect rgb(230, 255, 255)
        Note right of U: Webhook Processing
        ST->>F: POST /billing/webhook
        F->>F: Verify signature
        F->>S: BillingService.handle_webhook()
        S->>S: Check idempotency (WebhookEventLog)
        alt checkout.session.completed
            S->>DB: Create/update Subscription
            S->>DB: Set org subscription_tier
            S->>DB: Create Invoice
            S->>DB: Audit log
            S->>DB: Notification
        end
        alt invoice.paid
            S->>DB: Update invoice status
        end
        alt customer.subscription.updated
            S->>DB: Update subscription status/period
        end
        alt customer.subscription.deleted
            S->>DB: Cancel subscription
            S->>DB: Revert org to Free
        end
        S-->>F: 200 OK
        F-->>ST: Stripe success response
    end

    rect rgb(255, 255, 255)
        Note right of U: Entitlement Check
        U->>B: Access premium feature
        B->>F: GET /knowledge/documents
        F->>S: EntitlementService.has_feature()
        S->>DB: Check org subscription_tier
        alt Free Plan
            S-->>F: Knowledge base: True
            S-->>F: Semantic search: False
            S-->>F: AI Chat: False
            F-->>B: Feature-limited interface
        else Pro/Business
            S-->>F: All features enabled
            F-->>B: Full interface
        end
    end
```
