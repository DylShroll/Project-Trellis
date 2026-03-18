# TRELLIS
## Cultivate Curiosity. Nurture Connection.

**Architecture & Design Specification**
Version 2.0 · March 2026 · Dylan Shroll

---

## Table of Contents

1. [Vision & Philosophy](#1-vision--philosophy)
2. [Current State](#2-current-state)
3. [Feature Specification](#3-feature-specification)
4. [Technical Architecture](#4-technical-architecture)
5. [Prompt Engine Design](#5-prompt-engine-design)
6. [Brand & Design System](#6-brand--design-system)
7. [Mobile-First Responsive Design](#7-mobile-first-responsive-design)
8. [Security & Privacy Architecture](#8-security--privacy-architecture)
9. [Infrastructure & Deployment](#9-infrastructure--deployment)
10. [Development Roadmap](#10-development-roadmap)
11. [Closing Thoughts](#11-closing-thoughts)

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

## 2. Current State

### Phase 1 — Complete
Full authentication (register/login/logout), Garden CRUD (plots with stories, details, curiosities, milestones), read-only Journal list, Docker-based local development (FastAPI + PostgreSQL + Redis + Celery), and a hardcoded dashboard prompt card.

### Phase 2 — Complete
Journal write UI (new entry form, detail view, delete), the Claude-powered Prompt Engine (contextual conversation starters per plot + daily dashboard prompt), Celery background tasks for reconnection nudges and milestone reminders, auth-aware nav with notification bell and mobile bottom bar, user profile page, and full notification UI (inbox, mark-read, polling badge).

### Phase 3 — In Progress
Per-garden-entry connection timeline, photo uploads for garden entries and user profiles, interest-group panels on garden entry profiles (Music, Film, Books, etc.), expanded conversation prompt library with structured categories, and a full Art Nouveau aesthetic overhaul with a plum and rose gold color system.

---

## 3. Feature Specification

### 3.1 The Garden (People Profiles)

Each person in a user's life gets a rich, evolving profile called a "plot." Think of it as a living document that grows over time — not a static contact card, but a place where stories accumulate like rings in a tree.

#### Profile Fields

| Field | Type | Description |
|-------|------|-------------|
| Display Name | String | How the user thinks of this person (e.g., "Mom," "Carrie," "Jamie from woodworking") |
| Relationship Tag | Enum + Custom | Partner, Family, Close Friend, Friend, Colleague, Mentor, Community, Custom |
| Photo | Image (optional) | A small uploaded photo representing this person to the user |
| Stories | Rich Text[] | Freeform notes, memories, and anecdotes — timestamped and searchable |
| Details | Key-Value[] | Structured facts: birthday, favorite coffee order, allergies, love languages, etc. |
| Conversation Log | Entry[] | Brief notes after meaningful conversations: what was discussed, what surprised the user |
| Curiosities | String[] | Things the user wants to learn or ask about next time they see this person |
| Milestones | Date + Note[] | Important dates and life events worth remembering |
| Interest Groups | Group[] | Shared interest panels — Music, Film, Books, Food, Travel, etc. (see §3.4) |
| Last Connected | DateTime | Auto-tracked or manually logged timestamp of last meaningful interaction |

### 3.2 Connection Timeline

Each garden entry has a dedicated, scrollable timeline of all logged connections — journal entries linked to this person, milestone events, and reconnection notes. The timeline is accessible as an independent view under the garden entry profile (`/garden/{plot_id}/timeline`) and shows:

- Date and duration of each connection
- Brief content excerpt with a link to the full journal entry
- Any milestones that fell on or near that date
- A visual "gap" indicator for long silences between connections
- Prompt cards surfaced at the moment of each connection

This gives users a longitudinal view of a relationship's rhythm — not just static facts about a person, but the living history of how the connection has grown (or needs tending).

### 3.3 Photo Uploads

Users can upload a small photo (max 2 MB, JPEG/PNG/WebP) for:

1. **Garden entry profiles** — A portrait or image that represents this person to the user. Displayed as a rounded thumbnail in the plot card and profile header.
2. **User profile** — The user's own avatar, shown in the nav dropdown and profile page.

Files are stored in S3 with presigned URL access. Uploaded images are resized server-side to a 400×400 px maximum to keep storage and load times minimal. The UI uses a simple file input with a preview before submission — no third-party upload widget.

### 3.4 Interest Groups

Each garden entry profile can hold one or more interest group panels. Groups organize shared knowledge around a person's interests using like-with-like categorization:

| Group | Example Fields |
|-------|---------------|
| Music | Favorite artists, favorite albums, genres, live performances attended, songs that matter to them |
| Film & TV | Favorite films, directors, actors, genres, themes, TV shows, content creators/YouTubers |
| Books | Favorite authors, genres, titles, formative reads, currently reading |
| Food & Drink | Favorite cuisines, restaurants, dietary notes, things they love to cook, coffee/tea order |
| Travel | Places they've lived, places they want to go, meaningful trips, travel style |
| Work & Craft | Current role, past careers, side projects, skills they're building, proudest work |
| Sports & Movement | Sports they play or follow, teams, fitness habits, outdoor activities |
| Custom | User-defined label + freeform key-value fields |

Interest groups are optional and additive — a user adds groups that are relevant and ignores the rest. Each group is a collapsible panel on the plot detail page, collapsed by default when empty.

### 3.5 Conversation Prompt Library

The prompt engine now draws from a structured library of conversation categories, making prompts more contextually precise:

| Category | Trigger | Example |
|----------|---------|---------|
| Deepening Questions | User views a profile | "You know Jamie loves hiking. Have you ever asked what got them started?" |
| Interest Threads | Interest group data present | "You both love Coltrane — have you asked what record they'd take to a desert island?" |
| Milestone Reminders | Approaching date | "Carrie's work anniversary is next week. Maybe ask how she's feeling about the year." |
| Reconnection Nudges | Inactivity threshold | "It's been 3 weeks since you talked with Alex. Here's a low-pressure way to reach out." |
| Curiosity Seeds | Sparse profile data | "You don't know much about Sam's childhood yet. That's a whole world to explore." |
| Reflection Prompts | After logging a conversation | "What surprised you most about what they shared?" |
| Seasonal / Contextual | Calendar / weather / news | "First snow of the year — who would love to hear from you right now?" |

### 3.6 The Journal (Interaction History)

A private, chronological feed of meaningful moments. After a conversation, users can quickly capture what happened, how they felt, and what they learned. Over time, this becomes a rich tapestry — a record of a relationship growing.

Journal entries support freeform text, mood tags, an optional linked garden entry, and optional photo attachments. Entries link back to the relevant person's profile, building a cross-referenced record of each relationship.

### 3.7 The Dashboard (Home View)

The landing screen is designed to feel like a warm morning — not a task list. It surfaces three elements: a daily curiosity prompt (one thoughtful question to carry into the day), a gentle reminder about someone due for reconnection, and a brief glimpse at recent journal entries or upcoming milestones.

---

## 4. Technical Architecture

### 4.1 System Overview

Trellis follows a modular monolith pattern — a single deployable unit with clear internal boundaries. This keeps operational complexity low while allowing future extraction of services if scale demands it.

#### Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.13 | Primary development language; rich ecosystem for AI/ML integration |
| Web Framework | FastAPI | Async-first, automatic OpenAPI docs, excellent typing support, high performance |
| Frontend Rendering | Jinja2 + HTMX | Server-rendered HTML with dynamic interactivity; keeps codebase Python-centric, avoids heavy JS framework overhead |
| Styling | Tailwind CSS (CDN) | Utility-first CSS with custom Art Nouveau plum/rose-gold theme; mobile-first responsive design |
| Database | PostgreSQL 16 | Robust relational storage with JSONB for flexible profile fields; full-text search built-in |
| ORM | SQLAlchemy 2.0 + Alembic | Async ORM with migration support; type-safe query building |
| Caching | Redis | Session management, prompt engine cache, rate limiting |
| Task Queue | Celery + Redis | Background processing for nudge scheduling, milestone reminders, and prompt generation |
| AI Integration | Anthropic Claude API | Powers the prompt engine with contextual, empathetic conversation suggestions |
| Auth | Session-based (httpOnly cookies) | Secure server-side sessions; bcrypt password hashing |
| File Storage | AWS S3 | Profile photos and media attachments with presigned URL access |
| Infrastructure | Docker Compose (local) → AWS (prod) | ECS Fargate, RDS, ElastiCache, CloudFront |
| CI/CD | GitHub Actions | Automated testing, security scanning, and deployment pipeline |
| Monitoring | CloudWatch + Sentry | Application performance monitoring, error tracking, and alerting |

### 4.2 Data Model

The data model is designed around the concept of a user's garden — each user has plots (people) that contain stories (freeform), details (structured), and entries (journal interactions). The schema uses PostgreSQL JSONB for flexible fields while keeping relational integrity for structured queries.

#### Core Entities

| Entity | Key Fields | Relationships |
|--------|-----------|---------------|
| User | id, email, display_name, photo_url, preferences, created_at | Has many Plots, Entries, Notifications |
| Plot (Person) | id, user_id, display_name, relationship_tag, photo_url, last_connected | Belongs to User; has many Stories, Details, Curiosities, Milestones, Connections, InterestGroups |
| Story | id, plot_id, content (rich text), created_at | Belongs to Plot |
| Detail | id, plot_id, key, value, category | Belongs to Plot |
| Curiosity | id, plot_id, question, is_resolved, created_at | Belongs to Plot |
| Milestone | id, plot_id, date, title, notes, is_recurring | Belongs to Plot |
| Connection | id, plot_id, journal_entry_id, connected_at, notes | Belongs to Plot; optionally links to JournalEntry |
| InterestGroup | id, plot_id, group_type, fields (JSONB) | Belongs to Plot |
| JournalEntry | id, user_id, plot_id, content, mood_tag, media_urls, created_at | Belongs to User and optionally Plot |
| Notification | id, user_id, type, payload, scheduled_at, sent_at, is_read | Belongs to User |

### 4.3 API Design

The API follows RESTful conventions with a versioned prefix (`/api/v1`). All endpoints return JSON for HTMX consumption and support standard HTTP methods.

#### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/garden | List all plots for the authenticated user |
| POST | /api/v1/garden | Create a new plot |
| GET | /api/v1/garden/{plot_id} | Get full profile for a person |
| PATCH | /api/v1/garden/{plot_id} | Update profile fields |
| GET | /api/v1/garden/{plot_id}/timeline | Get the connection timeline for a person |
| POST | /api/v1/garden/{plot_id}/connections | Log a new connection |
| POST | /api/v1/garden/{plot_id}/stories | Add a story/memory |
| POST | /api/v1/garden/{plot_id}/curiosities | Add a question to explore |
| POST | /api/v1/garden/{plot_id}/interest-groups | Add or update an interest group |
| POST | /api/v1/garden/{plot_id}/photo | Upload a photo for a garden entry |
| GET | /api/v1/prompts/daily | Get the daily curiosity prompt |
| GET | /api/v1/prompts/for/{plot_id} | Get contextual conversation starters |
| POST | /api/v1/journal | Log a journal entry |
| GET | /api/v1/journal | List journal entries |
| POST | /api/v1/profile/photo | Upload user avatar |
| GET | /api/v1/dashboard | Get the aggregated home view data |

---

## 5. Prompt Engine Design

The prompt engine is the soul of Trellis. It uses the Anthropic Claude API to generate conversation prompts that feel like they came from a thoughtful friend, not a notification algorithm.

### 5.1 How It Works

When a user requests prompts for a specific person, the engine assembles a context bundle: the person's profile data (stories, details, curiosities, milestones, interest groups), the user's recent journal entries about them, and any approaching dates or inactivity signals. This bundle is passed to Claude with a carefully crafted system prompt.

Prompts are generated in batches of 3–5, ranked by relevance, and cached for 24 hours to avoid redundant API calls. Cache is invalidated whenever the user adds new data to that person's profile.

### 5.2 Prompt Generation Pipeline

| Stage | Input | Output |
|-------|-------|--------|
| 1. Context Assembly | Plot profile + interest groups + recent entries + date | Structured context bundle |
| 2. Gap Analysis | Context bundle | Identified knowledge gaps and conversation threads |
| 3. Prompt Generation | Gaps + context + tone guidelines | 3–5 ranked conversation prompts |
| 4. Caching & Delivery | Generated prompts | Cached result served; TTL-based refresh |

### 5.3 Tone Calibration

The prompt engine's voice is deliberately calibrated to feel like a wise, warm friend — not a productivity coach, not a therapist, and definitely not a push notification. Prompts are specific (referencing what you already know), gentle (never urgent), and oriented toward curiosity rather than obligation.

---

## 6. Brand & Design System

### 6.1 Aesthetic Direction

The Trellis aesthetic is rooted in Art Nouveau — an organic, nature-inspired visual language defined by flowing curves, botanical motifs, and the integration of ornament into structure. This direction evolved from the original "natural materials" foundation (leather, paper, pressed flowers) into something more deliberate: sinuous vine lattices, stylized blossoms, classical typography, and a jewel-toned palette that feels both intimate and elegant.

If the app were a physical object in Version 1, it was a well-worn leather journal. In Version 2, it is a hand-illuminated manuscript — the same warmth, but with intention and artistry made visible.

### 6.2 Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `deep-moss` | `#3B1F4A` | Deep royal plum — nav, hero cards, dark buttons |
| `warm-clay` | `#AB6B55` | Warm rose-terracotta — CTAs, links, active states |
| `sage-green` | `#8B6A96` | Dusty plum — secondary badges, tags, relationship labels |
| `cream` | `#F7EDE6` | Warm parchment — page background |
| `bark` | `#2C1A35` | Darkest plum — headings, strong text |
| `loam` | `#4A3050` | Dark plum — body text |
| `light-sage` | `#DFC8D8` | Blush / rose mist — borders, badge backgrounds, skeletons |
| `sandstone` | `#EDE0DC` | Warm vellum — input backgrounds, subtle fills |
| `golden-hour` | `#C09448` | Antique gold — milestone icons, achievement highlights |
| `gilt` | `#C49A78` | Soft rose gold — SVG ornaments, nav accents, decorative rules |
| `plum-mid` | `#7A5C85` | Medium plum — hover states, active nav |

### 6.3 Typography

| Role | Font | Weight | Notes |
|------|------|--------|-------|
| Headings | Fraunces (variable) | 400–800 | Organic optical-size serif; warm and handcrafted. Primary heading font throughout the app. |
| Display / Wordmark | Cormorant Garamond | 400–600 (roman + italic) | Classical Italian serif with strong Art Nouveau character. Used for the Trellis wordmark, page titles on auth screens, and decorative italic flourishes. |
| Body Text | Inter (variable) | 400–500 | Clean, legible sans-serif. The contrast between Inter's precision and the ornate display fonts is an intentional Art Nouveau tension. |
| Accent / Quotes | Caveat | 400 | Handwritten feel for personal touches: prompt text, pull quotes, empty state copy. |

### 6.4 Art Nouveau Texture System

Trellis implements Art Nouveau ornamentation through four tightly scoped mechanisms — each adds visual character without competing with content.

#### Body Texture Pattern
A repeating 80×80 px SVG tile overlaid at ~7% opacity on the parchment background. The tile contains:
- Four bezier-curve vine segments flowing in/out at each edge midpoint (creating a continuous lattice when tiled)
- Small leaf ellipses along each vine arm, rotated to follow the curve direction
- Rose-gold (`gilt`) dots at tile corners (merging into intersection nodes when tiled)

The result is a living, organic grid — visible enough to feel tactile, subtle enough to disappear when content is present.

#### Ornamental Nav Border
The nav replaces the standard drop shadow with a `box-shadow` tuned to the deep plum (`#3B1F4A`) and a 1 px bottom border with a gradient: `transparent → rgba(196,154,120,0.28) → transparent`. The nav wordmark uses Cormorant Garamond with a custom SVG leaf mark — a stylized water droplet / leaf form rendered in gilt strokes.

#### Card Elevation (`nouveau-card`)
Cards receive a two-layer shadow: a 1 px rose-gold halo (`rgba(196,154,120,0.12)`) and a soft plum diffusion shadow. On hover, the border transitions toward `gilt/40`. This replaces the flat `shadow-sm` convention from Phase 1.

#### Auth Ornamental Frame
Auth pages (login, register) feature:
1. A botanical garland SVG ornament (central multi-petal blossom, two flowing vine branches with leaf ellipses, secondary blooms, and ruled end lines in gilt)
2. An inner ornamental rule via `.nouveau-auth-card::before` — an absolutely-positioned `inset: 7px` border at 18% opacity, creating a subtle secondary frame inside the card

#### CSS Utility Classes

| Class | Description |
|-------|-------------|
| `.trellis-nav` | Nav shadow + gold bottom border |
| `.nouveau-card` | Rose-gold halo + soft plum elevation |
| `.nouveau-auth-card` | Inner ornamental rule via `::before` |
| `.nouveau-divider` | Flex divider with gold gradient rules via `::before`/`::after` |
| `font-display` | Cormorant Garamond stack (italic display use) |

#### Dark Mode

Dark mode inverts to a deep plum palette: `deep-moss` becomes the background, `cream` becomes the text color, and `warm-clay` remains the primary accent. The botanical vine texture inverts to a faint gilt lattice on dark plum. Dark mode should feel like reading by candlelight in a private library, not like a code editor.

---

## 7. Mobile-First Responsive Design

Trellis is designed mobile-first. The primary use case is quick, on-the-go capture: a user just had a great conversation and wants to jot down what they learned before the details fade.

### 7.1 Responsive Breakpoints

| Breakpoint | Width | Layout | Key Adaptations |
|------------|-------|--------|-----------------|
| Mobile (default) | < 640px | Single column, bottom nav | Full-width cards, large touch targets (48px min), voice input prominent |
| Tablet | 640–1024px | Single column + sidebar drawer | Collapsible sidebar for garden navigation |
| Desktop | > 1024px | Two-column with persistent sidebar | Garden sidebar always visible, expanded profile view, keyboard shortcuts |

### 7.2 Progressive Web App (PWA)

Trellis ships as a PWA with a service worker for offline capability. Users can install it to their home screen on iOS and Android. Push notifications (via Web Push API) deliver milestone reminders and reconnection nudges.

#### PWA Features

- **Offline Journal:** Users can write journal entries offline; entries sync when connectivity returns.
- **App Shell Caching:** The UI shell (nav, layout, core CSS/JS) is cached aggressively so the app loads instantly.
- **Push Notifications:** Opt-in push for milestone reminders and gentle reconnection nudges.
- **Home Screen Install:** Custom install prompt with Trellis branding and botanical splash screen.

### 7.3 Navigation

The mobile bottom nav (fixed, `md:hidden`) uses SVG icon set instead of emoji for crisp rendering at all densities. Icons: Home, Garden (leaf), Journal (document), Alerts (bell with badge). Active items are highlighted in `gilt`; inactive items use `cream/50`.

---

## 8. Security & Privacy Architecture

Trellis handles deeply personal information about people's relationships. The security posture reflects this: we treat every piece of data as if it were a handwritten letter someone entrusted to us.

### 8.1 Encryption

- **At Rest:** All database fields containing personal content are encrypted using AES-256-GCM with per-user encryption keys derived from AWS KMS. S3 objects use SSE-KMS.
- **In Transit:** TLS 1.3 enforced on all connections. HSTS enabled with a minimum 1-year max-age.

### 8.2 Authentication

- **Auth Flow:** Session-based authentication with httpOnly cookies. bcrypt (via passlib) for password hashing. Short-lived sessions backed by Redis.
- **Authorization:** Users can only access their own data. No sharing features in v1.

### 8.3 Data Governance

- **Data Minimization:** Trellis collects only what is needed for functionality. No third-party tracking pixels.
- **Right to Deletion:** Full account deletion with cryptographic erasure of all user data within 72 hours.
- **AI Data Handling:** Data sent to the Claude API is not stored or used for training. API calls use ephemeral sessions and the minimum context required for quality prompts.
- **Photo Storage:** Uploaded images are stored in S3 with presigned URLs. Server-side resizing prevents oversized uploads. No image is ever used for advertising or shared outside the user's own session.

---

## 9. Infrastructure & Deployment

### 9.1 Local Development

```bash
# Start all services (app, postgres, redis, celery worker, celery beat)
docker compose up

# Run database migrations
docker compose exec app alembic upgrade head

# Access the app
open http://localhost:8000
```
---

## 10. Development Roadmap

### Phase 1 — Foundation ✓ Complete
Project scaffolding, FastAPI application structure, database schema and migrations, user authentication (register/login/logout), and full Garden CRUD. Docker-based local development stack. Deployed to dev environment.

### Phase 2 — Heart ✓ Complete
Journal write UI (new entry form, detail view, delete, plot linkage), Claude API-powered Prompt Engine (per-plot + daily dashboard), Celery background tasks (reconnection nudges, milestone reminders), auth-aware nav with notification bell and mobile bottom bar, user profile page, and full notification inbox with polling badge.

### Phase 3 — Depth (Current)
- **Connection Timeline** — Per-garden-entry chronological view of all logged connections, accessible at `/garden/{plot_id}/timeline`
- **Photo Uploads** — User avatar and garden entry portrait upload (2 MB max, S3-backed, server-side resize)
- **Interest Groups** — Structured panels for shared interests (Music, Film, Books, Food, Travel, Work, Sports, Custom) on garden entry profiles
- **Expanded Prompt Library** — Interest-group-aware conversation prompts that draw from structured shared interests
- **Art Nouveau Aesthetic** — Plum + rose gold color system, botanical vine body texture, Cormorant Garamond display font, SVG ornamental elements

### Phase 4 — Polish (Planned)
Full design system build (replace Tailwind CDN with compiled build), dark mode, PWA setup with offline journal and push notifications, voice-to-text capture on mobile, comprehensive accessibility audit (WCAG 2.1 AA), and natural language search across all stored knowledge.

### Phase 5 — Cultivate (Future)
Relationship timeline visualization, AI-generated memory summaries, recurring insight reports ("This year with Jamie"), and carefully designed sharing features (with full consent architecture). Each addition evaluated against the core question: does this help someone be more curious about the people they love?

---

## 11. Closing Thoughts

Technology is at its best when it makes us more human, not less. Trellis exists because the most valuable things in our lives — the people we love and the conversations that shape us — deserve the same intentionality we bring to everything else we care about.

This is not an app for tracking contacts or optimizing social capital. It is a quiet, private practice tool for the art of paying attention — a trellis for the relationships that make life worth living.

Version 2 adds depth to that premise: richer profiles, a chronological memory of how each relationship has grown, the ability to capture what you share with someone (their music, their films, their passions), and an aesthetic that matches the seriousness of that intention. Art Nouveau was chosen not as decoration but as philosophy — organic form that grows from function, beauty that emerges from structure, ornamentation that honors rather than obscures.

The vine grows where the trellis guides it.
