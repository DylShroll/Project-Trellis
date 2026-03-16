# 🌿 TRELLIS
## Cultivate Curiosity. Nurture Connection.

**Architecture & Design Specification**
Version 1.0 · March 2026 · Dylan Shroll

---

## Table of Contents

1. [Vision & Philosophy](#1-vision--philosophy)
2. [Feature Specification](#2-feature-specification)
3. [Technical Architecture](#3-technical-architecture)
4. [Prompt Engine Design](#4-prompt-engine-design)
5. [Brand & Design System](#5-brand--design-system)
6. [Mobile-First Responsive Design](#6-mobile-first-responsive-design)
7. [Security & Privacy Architecture](#7-security--privacy-architecture)
8. [Infrastructure & Deployment](#8-infrastructure--deployment)
9. [Development Roadmap](#9-development-roadmap)
10. [Closing Thoughts](#10-closing-thoughts)

---

## 1. Vision & Philosophy

Trellis is a web application designed to help people cultivate deeper, more meaningful relationships with the humans in their lives. It operates on a simple premise: the quality of our connections is shaped by the quality of our attention, and attention is a skill we can practice.

The application serves two complementary purposes. First, it acts as a living knowledge base — a warm, private garden where users can record and recall the rich details of the people they care about: stories, preferences, milestones, and the questions left unasked. Second, it serves as a gentle prompt engine — surfacing thoughtful conversation starters and reconnection nudges based on what the user already knows and what they might want to explore next.

Trellis is not a CRM. It is not a contact manager. It is a practice tool for the art of paying attention to other people.

### Core Principles

- **Curiosity Over Compliance** — The app should inspire exploration, not guilt. Nudges are invitations, never obligations.
- **Warmth Over Efficiency** — Every interaction with Trellis should feel like opening a handwritten letter, not filing a report. The UI favors organic textures, thoughtful motion, and language that treats relationships as living things.
- **Privacy as Foundation** — The knowledge users entrust to Trellis about their loved ones is sacred. Data is encrypted at rest and in transit, never sold, never used for advertising, and never analyzed for anything beyond the user's own benefit.
- **Depth Over Breadth** — Trellis is designed for the inner circle — the 15–50 people who matter most. It is not built to scale to thousands of contacts.

---

## 2. Feature Specification

### 2.1 The Garden (People Profiles)

Each person in a user's life gets a rich, evolving profile called a "plot." Think of it as a living document that grows over time — not a static contact card, but a place where stories accumulate like rings in a tree.

#### Profile Fields

| Field | Type | Description |
|-------|------|-------------|
| Display Name | String | How the user thinks of this person (e.g., "Mom," "Carrie," "Jamie from woodworking") |
| Relationship Tag | Enum + Custom | Partner, Family, Close Friend, Friend, Colleague, Mentor, Community, Custom |
| Photo | Image (optional) | A photo that represents this person to the user |
| Stories | Rich Text[] | Freeform notes, memories, and anecdotes — timestamped and searchable |
| Details | Key-Value[] | Structured facts: birthday, favorite coffee order, allergies, love languages, etc. |
| Conversation Log | Entry[] | Brief notes after meaningful conversations: what was discussed, what surprised the user |
| Curiosities | String[] | Things the user wants to learn or ask about next time they see this person |
| Milestones | Date + Note[] | Important dates and life events worth remembering |
| Last Connected | DateTime | Auto-tracked or manually logged timestamp of last meaningful interaction |

### 2.2 The Prompt Engine (Conversation Encouragement)

The heart of Trellis. The prompt engine generates contextual, thoughtful conversation starters and nudges based on what the user already knows about someone — and, more importantly, what they don't yet know.

#### Prompt Categories

| Category | Trigger | Example |
|----------|---------|---------|
| Deepening Questions | User views a profile | "You know Jamie loves hiking. Have you ever asked what got them started?" |
| Milestone Reminders | Approaching date | "Carrie's work anniversary is next week. Maybe ask how she's feeling about the year." |
| Reconnection Nudges | Inactivity threshold | "It's been 3 weeks since you talked with Alex. Here's a low-pressure way to reach out." |
| Curiosity Seeds | Sparse profile data | "You don't know much about Sam's childhood yet. That's a whole world to explore." |
| Reflection Prompts | After logging a conversation | "What surprised you most about what they shared?" |
| Seasonal / Contextual | Calendar / weather / news | "First snow of the year — who would love to hear from you right now?" |

### 2.3 The Journal (Interaction History)

A private, chronological feed of meaningful moments. After a conversation, users can quickly capture what happened, how they felt, and what they learned. Over time, this becomes a rich tapestry — a record of a relationship growing.

Journal entries support freeform text, voice-to-text capture (for on-the-go logging), mood tags, and optional photo attachments. Entries link back to the relevant person's profile, building a cross-referenced record of each relationship.

### 2.4 The Dashboard (Home View)

The landing screen is designed to feel like a warm morning — not a task list. It surfaces three elements: a daily curiosity prompt (one thoughtful question to carry into the day), a gentle reminder about someone due for reconnection, and a brief glimpse at recent journal entries or upcoming milestones.

---

## 3. Technical Architecture

### 3.1 System Overview

Trellis follows a modular monolith pattern — a single deployable unit with clear internal boundaries. This keeps operational complexity low while allowing future extraction of services if scale demands it.

#### Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.12+ | Primary development language; rich ecosystem for AI/ML integration |
| Web Framework | FastAPI | Async-first, automatic OpenAPI docs, excellent typing support, high performance |
| Frontend Rendering | Jinja2 + HTMX | Server-rendered HTML with dynamic interactivity; keeps codebase Python-centric, avoids heavy JS framework overhead |
| Styling | Tailwind CSS | Utility-first CSS with custom earth-tone theme; mobile-first responsive design out of the box |
| Database | PostgreSQL 16 | Robust relational storage with JSONB for flexible profile fields; full-text search built-in |
| ORM | SQLAlchemy 2.0 + Alembic | Async ORM with migration support; type-safe query building |
| Caching | Redis | Session management, prompt engine cache, rate limiting |
| Task Queue | Celery + Redis | Background processing for nudge scheduling, milestone reminders, and prompt generation |
| AI Integration | Anthropic Claude API | Powers the prompt engine with contextual, empathetic conversation suggestions |
| Auth | OAuth2 + JWT (via Authlib) | Secure, standards-based authentication; supports social login expansion |
| File Storage | AWS S3 | Profile photos and media attachments with presigned URL access |
| Infrastructure | AWS (Terraform) | ECS Fargate for compute, RDS for database, ElastiCache for Redis, CloudFront CDN |
| CI/CD | GitHub Actions | Automated testing, security scanning (SAST/DAST), and deployment pipeline |
| Monitoring | CloudWatch + Sentry | Application performance monitoring, error tracking, and alerting |

### 3.2 Architecture Diagram (Logical)

The system is organized into four logical layers, each with clearly defined responsibilities:

| Layer | Components | Responsibility |
|-------|-----------|----------------|
| Presentation | HTMX views, Jinja2 templates, Tailwind CSS, Service Worker | Mobile-first responsive UI, offline-capable PWA shell, push notifications |
| API | FastAPI routers, Pydantic models, middleware | Request validation, authentication, rate limiting, CORS, API versioning |
| Domain | Profile service, Prompt engine, Journal service, Notification scheduler | Core business logic, AI prompt generation, relationship analytics |
| Data | SQLAlchemy models, Redis cache, S3 client, Alembic migrations | Persistence, caching, file storage, schema evolution |

### 3.3 Data Model

The data model is designed around the concept of a user's garden — each user has plots (people) that contain stories (freeform), details (structured), and entries (journal interactions). The schema uses PostgreSQL JSONB for flexible fields while keeping relational integrity for structured queries.

#### Core Entities

| Entity | Key Fields | Relationships |
|--------|-----------|---------------|
| User | id, email, display_name, preferences, created_at | Has many Plots, Entries, Notifications |
| Plot (Person) | id, user_id, display_name, relationship_tag, photo_url, last_connected | Belongs to User; has many Stories, Details, Curiosities, Milestones |
| Story | id, plot_id, content (rich text), created_at | Belongs to Plot |
| Detail | id, plot_id, key, value, category | Belongs to Plot |
| Curiosity | id, plot_id, question, is_resolved, created_at | Belongs to Plot |
| Milestone | id, plot_id, date, title, notes, is_recurring | Belongs to Plot |
| JournalEntry | id, user_id, plot_id, content, mood_tag, media_urls, created_at | Belongs to User and Plot |
| Notification | id, user_id, type, payload, scheduled_at, sent_at | Belongs to User |

### 3.4 API Design

The API follows RESTful conventions with a versioned prefix (`/api/v1`). All endpoints return JSON for HTMX consumption and support standard HTTP methods. Authentication is handled via Bearer tokens with short-lived JWTs.

#### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/garden | List all plots (people) for the authenticated user |
| POST | /api/v1/garden | Create a new plot |
| GET | /api/v1/garden/{plot_id} | Get full profile for a person |
| PATCH | /api/v1/garden/{plot_id} | Update profile fields |
| POST | /api/v1/garden/{plot_id}/stories | Add a story/memory to a person |
| POST | /api/v1/garden/{plot_id}/curiosities | Add a question to explore |
| GET | /api/v1/prompts/daily | Get the daily curiosity prompt |
| GET | /api/v1/prompts/for/{plot_id} | Get contextual conversation starters for a person |
| POST | /api/v1/journal | Log a journal entry after a conversation |
| GET | /api/v1/journal | List journal entries (filterable by person, date, mood) |
| GET | /api/v1/dashboard | Get the aggregated home view data |

---

## 4. Prompt Engine Design

The prompt engine is the soul of Trellis. It uses the Anthropic Claude API to generate conversation prompts that feel like they came from a thoughtful friend, not a notification algorithm. The key insight is that the best conversation starters aren't generic — they're rooted in what you already know and point toward what you don't.

### 4.1 How It Works

When a user requests prompts for a specific person, the engine assembles a context bundle: the person's profile data (stories, details, curiosities, milestones), the user's recent journal entries about them, and any approaching dates or inactivity signals. This bundle is passed to Claude with a carefully crafted system prompt.

The system prompt instructs Claude to act as a gentle encourager — someone who notices the gaps in what we know about people we love and frames those gaps as invitations, not deficiencies. Prompts are generated in batches of 3–5, ranked by relevance, and cached for 24 hours to avoid redundant API calls.

### 4.2 Prompt Generation Pipeline

| Stage | Input | Output |
|-------|-------|--------|
| 1. Context Assembly | Plot profile + recent entries + date | Structured context bundle (JSON) |
| 2. Gap Analysis | Context bundle | Identified knowledge gaps and conversation threads |
| 3. Prompt Generation | Gaps + context + tone guidelines | 3–5 ranked conversation prompts with rationale |
| 4. Caching & Delivery | Generated prompts | Cached result served to user; TTL-based refresh |

### 4.3 Tone Calibration

The prompt engine's voice is deliberately calibrated to feel like a wise, warm friend — not a productivity coach, not a therapist, and definitely not a push notification. The system prompt includes explicit tone guidelines: prompts should feel like gentle observations, use second-person naturally, avoid urgency language, and always leave the user feeling curious rather than obligated.

---

## 5. Brand & Design System

The Trellis brand is rooted in the natural world. If the app were a physical object, it would be a well-worn leather journal sitting next to a cup of tea on a windowsill — inviting, tactile, and quietly beautiful.

### 5.1 Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| Deep Moss | #2D3A2E | Primary dark — headers, nav bar, primary buttons |
| Warm Clay | #B5694D | Accent terracotta — CTAs, active states, highlights |
| Sage Green | #7A8B6F | Secondary — tags, borders, subtle accents |
| Cream | #F5F0E8 | Background — page background, card backgrounds |
| Bark | #5C4A3A | Headings — section headers, important labels |
| Loam | #3E3229 | Body text — readable, warm alternative to pure black |
| Light Sage | #D4DDD0 | Surface — card hover states, dividers, secondary backgrounds |
| Sandstone | #E8DFD0 | Muted surface — input backgrounds, secondary cards |
| Golden Hour | #C9973E | Highlight — milestone badges, achievement moments, stars |

### 5.2 Typography

| Role | Font | Weight | Notes |
|------|------|--------|-------|
| Headings | Fraunces (variable) | 600–800 | Warm optical-size serif with organic character; feels handcrafted |
| Body Text | Inter (variable) | 400–500 | Clean, highly legible sans-serif optimized for screens; excellent at small sizes |
| Accent / Quotes | Caveat | 400 | Handwritten feel for personal touches: pull quotes, prompt text, empty states |
| Monospace | JetBrains Mono | 400 | Developer-facing only: API docs, code snippets |

### 5.3 Visual Texture & Aesthetic

Trellis uses subtle organic textures to create warmth without clutter. The overall aesthetic references natural materials: handmade paper, pressed flowers, weathered wood, woven linen. These textures appear as background patterns, card surfaces, and decorative elements — never as dominant visual features.

#### Texture Guidelines

- **Background:** A subtle paper grain texture (low-opacity noise overlay on the cream base) gives the app a tactile, analog quality.
- **Cards:** Profile cards and journal entries use a soft shadow with slightly rounded corners (12px radius) and a faint linen texture on hover.
- **Illustrations:** Line-art botanical illustrations (ferns, vines, small blooms) serve as decorative accents in empty states, onboarding, and loading screens. Style: single-weight line art in Sage Green, never photorealistic.
- **Icons:** Rounded, organic icon set — avoid sharp geometric icons. Phosphor Icons (light weight) or a custom set derived from botanical forms.
- **Motion:** Animations are slow and natural: gentle fades (300ms ease), subtle parallax on scroll, cards that breathe slightly on hover. Nothing should feel mechanical or instant.

#### Dark Mode

Dark mode inverts to a deep forest palette: Deep Moss becomes the background, Cream becomes the text color, and Warm Clay remains the accent. The paper grain texture inverts to a subtle wood grain. Dark mode should feel like reading by candlelight in a cabin, not like a code editor.

---

## 6. Mobile-First Responsive Design

Trellis is designed mobile-first. The primary use case is quick, on-the-go capture: a user just had a great conversation and wants to jot down what they learned before the details fade. The mobile experience must be fast, thumb-friendly, and frictionless.

### 6.1 Responsive Breakpoints

| Breakpoint | Width | Layout | Key Adaptations |
|------------|-------|--------|-----------------|
| Mobile (default) | < 640px | Single column, bottom nav | Full-width cards, swipe gestures, large touch targets (48px min), voice input prominent |
| Tablet | 640–1024px | Single column + sidebar drawer | Collapsible sidebar for garden navigation, split view for profile + journal |
| Desktop | > 1024px | Two-column with persistent sidebar | Garden sidebar always visible, expanded profile view, keyboard shortcuts |

### 6.2 Progressive Web App (PWA)

Trellis ships as a PWA with a service worker for offline capability. Users can install it to their home screen on iOS and Android, receiving an app-like experience without the app store overhead. Push notifications (via Web Push API) deliver milestone reminders and reconnection nudges.

#### PWA Features

- **Offline Journal:** Users can write journal entries offline; entries sync when connectivity returns via a background sync queue.
- **App Shell Caching:** The UI shell (nav, layout, core CSS/JS) is cached aggressively so the app loads instantly.
- **Push Notifications:** Opt-in push for milestone reminders and gentle reconnection nudges. Users control frequency (daily, weekly, or off).
- **Home Screen Install:** Custom install prompt with Trellis branding, splash screen with the botanical logo.

### 6.3 Touch & Gesture Design

All interactive elements are designed for thumb reachability on mobile. The bottom navigation bar places the four primary actions (Dashboard, Garden, Journal, Prompts) within easy reach. Swipe-right on a profile card opens quick-add actions (new story, new curiosity). Long-press on a prompt copies it to clipboard for easy sharing in a messaging app.

---

## 7. Security & Privacy Architecture

Trellis handles deeply personal information about people's relationships. The security posture reflects this: we treat every piece of data as if it were a handwritten letter someone entrusted to us.

### 7.1 Encryption

- **At Rest:** All database fields containing personal content (stories, details, journal entries) are encrypted using AES-256-GCM with per-user encryption keys derived from AWS KMS. S3 objects use SSE-KMS.
- **In Transit:** TLS 1.3 enforced on all connections. HSTS enabled with a minimum 1-year max-age.
- **Key Management:** AWS KMS with automatic key rotation. User-specific data encryption keys (DEKs) are wrapped by a master key and stored alongside the encrypted data.

### 7.2 Authentication & Authorization

- **Auth Flow:** OAuth 2.0 authorization code flow with PKCE for initial authentication. JWTs with short-lived access tokens (15 min) and rotating refresh tokens (7 days).
- **Session Management:** Redis-backed sessions with automatic invalidation on password change or suspicious activity. Concurrent session limits configurable per user.
- **Authorization Model:** Simple RBAC: users can only access their own data. No sharing features in v1 — this is intentional. Sharing relationship data introduces complex consent dynamics that require careful design.

### 7.3 Data Governance

- **Data Minimization:** Trellis collects only what is needed for functionality. No analytics tracking beyond anonymized usage metrics. No third-party tracking pixels.
- **Right to Deletion:** Full account deletion with cryptographic erasure of all user data within 72 hours. Deletion is irreversible and includes all backups within the retention window.
- **AI Data Handling:** Data sent to the Claude API for prompt generation is not stored or used for training. API calls use ephemeral sessions and the minimum context required for quality prompts.
- **Audit Logging:** All data access events are logged to CloudWatch with tamper-evident logging. Sensitive field access triggers additional logging.

---

## 8. Infrastructure & Deployment

### 8.1 AWS Architecture

| Service | Usage | Configuration |
|---------|-------|---------------|
| ECS Fargate | Application compute | 2 tasks min, auto-scaling to 8 based on CPU/memory; ARM64 for cost efficiency |
| RDS PostgreSQL | Primary database | db.t4g.medium, Multi-AZ, encrypted storage, automated backups (7-day retention) |
| ElastiCache Redis | Caching + sessions + task broker | cache.t4g.small, single node (cluster mode for production scale) |
| S3 | Media storage + static assets | Versioned bucket, lifecycle policies, presigned URLs for access |
| CloudFront | CDN + HTTPS termination | Edge caching for static assets, custom domain with ACM certificate |
| KMS | Encryption key management | Customer-managed key with auto-rotation |
| ECR | Container registry | Lifecycle policies for image retention |
| Route 53 | DNS management | Health checks, failover routing |

### 8.2 Terraform Organization

Infrastructure is defined in Terraform with modular composition. State is stored in S3 with DynamoDB locking. The codebase is organized into environment-specific workspaces (dev, staging, prod) with shared modules for common patterns.

| Module | Resources |
|--------|-----------|
| networking | VPC, subnets, security groups, NAT gateway |
| compute | ECS cluster, task definitions, service, ALB, auto-scaling |
| data | RDS instance, ElastiCache, S3 buckets, KMS keys |
| cdn | CloudFront distribution, Route 53 records, ACM certificates |
| monitoring | CloudWatch dashboards, alarms, SNS topics, Sentry integration |
| ci-cd | IAM roles for GitHub Actions, ECR repository, deployment policies |

### 8.3 CI/CD Pipeline

The deployment pipeline runs through GitHub Actions with the following stages: lint and type-check (ruff + mypy), unit and integration tests (pytest), SAST scanning (GitHub Advanced Security + Bandit), container build and push to ECR, Terraform plan (on PR) or apply (on merge to main), and ECS rolling deployment with automatic rollback on health check failure.

---

## 9. Development Roadmap

### Phase 1: Foundation (Weeks 1–4)

Project scaffolding, FastAPI application structure, database schema and migrations, user authentication, and basic Garden CRUD operations. Deploy to dev environment on AWS. The goal is a working skeleton that can store profiles and render them in a mobile-friendly view.

### Phase 2: Heart (Weeks 5–8)

Journal functionality, the Prompt Engine with Claude API integration, daily dashboard, and push notification infrastructure. This phase brings the soul of the application online — the moment it stops being a database and starts being a companion.

### Phase 3: Polish (Weeks 9–12)

Design system implementation (full earth-tone theme, textures, animations), PWA setup with offline support, voice-to-text journal capture, dark mode, and comprehensive accessibility audit (WCAG 2.1 AA). This is where the experience goes from functional to delightful.

### Phase 4: Cultivate (Ongoing)

User feedback integration, prompt engine refinement, potential features like relationship timeline visualization, shared milestones (with consent), and natural language search across all stored knowledge. Each addition should be evaluated against the core principle: does this help someone be more curious about the people they love?

---

## 10. Closing Thoughts

Technology is at its best when it makes us more human, not less. Trellis exists because the most valuable things in our lives — the people we love and the conversations that shape us — deserve the same intentionality we bring to everything else we care about.

This is not an app for tracking contacts or optimizing social capital. It is a quiet, private practice tool for the art of paying attention — a trellis for the relationships that make life worth living.

🌿
