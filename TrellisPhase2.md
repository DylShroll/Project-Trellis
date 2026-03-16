# Trellis — Phase 2 Build-Out Plan
**UI/UX Completion + Phase 2 "Heart" Engineering**

---

## Context

Phase 1 delivered working auth, full Garden CRUD, and a read-only Journal list with a hardcoded dashboard prompt. The application is functional but not yet the "companion" described in the README. Phase 2 brings the soul online: journal write UI, an AI-powered Prompt Engine via Claude API, wired Celery background tasks, and a complete nav (mobile + auth-aware + notifications).

---

## Critical Files

| File | Role |
|---|---|
| `app/modules/ui/router.py` | All new UI routes go here |
| `app/templates/partials/nav.html` | Full rewrite for auth, bell, dropdown, mobile |
| `app/templates/dashboard/index.html` | Replace hardcoded prompt |
| `app/templates/garden/plot_detail.html` | Add prompts + journal sections |
| `app/templates/journal/index.html` | Add "New entry" button + clickable cards |
| `app/workers/tasks/notifications.py` | Implement stubbed Celery tasks |
| `app/core/database.py` | Add `AsyncSessionLocal` for Celery |
| `app/modules/notifications/repository.py` | Add `count_unread()` |
| `pyproject.toml` / `requirements.txt` | Add `anthropic` dependency |

---

## Implementation Steps

### Step 1 — Journal Write UI

**Goal:** Users can create, view, and delete journal entries from the web UI.

**New UI routes** (add to `app/modules/ui/router.py`):
```
GET  /journal/new               → render entry_form.html (with plot select dropdown)
POST /journal/new               → call JournalService.create_entry(), redirect to /journal/{id}
GET  /journal/{entry_id}        → render entry_detail.html (with linked plot back-link)
POST /journal/{entry_id}/delete → call JournalService.delete_entry(), redirect to /journal
```

**New templates:**
- `app/templates/journal/entry_form.html` — textarea (content, required), `<select name="plot_id">` (optional, populated from `plots` list), `<select name="mood_tag">` (optional: reflective, grateful, curious, concerned, joyful). Visual style: matches `garden/plot_form.html` (white card, sandstone inputs, deep-moss submit button).
- `app/templates/journal/entry_detail.html` — date, mood badge, full content, linked-plot card (`/garden/{{ plot.id }}` back-link with initials avatar), HTMX delete button with `hx-confirm`.

**Modified templates:**
- `app/templates/journal/index.html` — add "+ New entry" button in header; make each entry card `<a href="/journal/{{ entry.id }}">` with linked plot name displayed if set.

**Modified routes:**
- `garden_detail()` in `ui/router.py` — additionally fetch the 3 most recent `JournalEntry` records filtered by `plot_id`, pass as `recent_journal` to the plot detail template.
- `app/templates/garden/plot_detail.html` — add "Conversations" section at the bottom: recent 3 journal entries + "+ Log conversation" link to `/journal/new?plot_id={{ plot.id }}`.

The `/journal/new` form should pre-select the linked plot if `?plot_id=` is in the query string.

---

### Step 2 — Prompt Engine Module

**Goal:** A self-contained module that assembles plot context and calls Claude API.

**Create:** `app/modules/prompts/` with the following files:

**`schemas.py`** — Pydantic models:
```python
class PlotContext(BaseModel):
    display_name: str
    relationship_tag: str
    last_connected: datetime | None
    days_since_contact: int | None
    stories: list[str]           # content only (latest 5)
    details: list[dict]          # {"key": ..., "value": ...}
    curiosities: list[str]       # unresolved questions only
    milestones: list[dict]       # {"title", "date", "days_until", "is_recurring"}
    recent_journal: list[str]    # last 3 entries, truncated to 300 chars

class PromptResult(BaseModel):
    prompts: list[str]           # 3–5 strings
    category: str                # "deepening" | "reconnection" | "curiosity_seed" | "milestone" | "daily"
    generated_at: datetime
    plot_id: UUID | None
    plot_name: str | None        # for dashboard display
    cache_hit: bool
```

**`cache.py`** — Redis key helpers:
```python
PROMPT_TTL = 86400  # 24 hours

def plot_prompt_key(user_id, plot_id) -> str:
    return f"prompts:plot:{user_id}:{plot_id}"

def daily_prompt_key(user_id) -> str:
    return f"prompts:daily:{user_id}:{date.today().isoformat()}"
    # date baked into key = natural daily expiry + 24hr safety TTL
```

**`context.py`** — `ContextAssembler`:
- `for_plot(db, plot_id, user_id) -> PlotContext` — fetches plot via `GardenService`, fetches last 3 journal entries via `JournalRepository` filtered by `plot_id`, computes `days_since_contact` and `days_until` for each milestone (projecting recurring ones to current/next year).
- `for_daily(db, user_id) -> tuple[PlotContext, str] | None` — lists all plots, prefers those with `last_connected > 14 days ago`, else random. Returns `(context, plot_name)` tuple. Returns `None` if garden is empty.

**`engine.py`** — `PromptEngine`:
- Constructor takes `redis: aioredis.Redis`.
- `get_plot_prompts(db, plot_id, user_id) -> PromptResult` — check cache, else assemble context, call Claude, cache result, return.
- `get_daily_prompt(db, user_id) -> PromptResult | None` — same pattern; only returns 1 prompt (the daily card).
- `_call_claude(context, mode) -> list[str]` — uses `anthropic.AsyncAnthropic` with a 10-second timeout. Parses numbered list response.
- `_classify(context) -> str` — returns category string based on context signals (see logic below).
- `SYSTEM_PROMPT` — module-level constant (see Step 3).

**Cache invalidation:** When a user adds a story, detail, curiosity, or milestone to a plot, invalidate `plot_prompt_key(user.id, plot_id)` via `await redis.delete(key)` inside the POST handlers in `ui/router.py`. Four lines, four handlers.

**Dependency:** `anthropic` must be added to `requirements.txt` / `pyproject.toml`. Use `anthropic.AsyncAnthropic`.

**Redis dependency injection:**
```python
# app/core/redis.py (or in database.py)
async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)
```
Instantiate `PromptEngine(redis=await get_redis())` inside each route handler that needs it.

---

### Step 3 — Claude API System Prompt

Module-level constant `SYSTEM_PROMPT` in `engine.py`:

```
You are a thoughtful companion helping someone be more curious and present with the people they love.

You will receive structured information about a person in the user's life.

TONE: Warm and curious. Second-person, present tense. Specific — reference what you know. Never urgent
or guilt-inducing. Leave the user feeling invited, not obligated. Avoid: "reach out," "check in," "touch base."

FORMAT: Return exactly 3 prompts as a numbered list. No preamble, no explanation.
1. [prompt]
2. [prompt]
3. [prompt]

RULES:
- If a milestone is approaching: weave it naturally into a deeper question, don't just mention the date.
- If the user hasn't connected recently: at least one prompt should be a low-pressure, specific opening.
- If the profile is sparse: generate prompts that open doors, not deepen existing knowledge.
```

**User message format** (structured text, not JSON):
```
Person: Jamie
Relationship: close friend
Days since last contact: 23

What you know:
- Stories: [story1], [story2]
- Details: birthday: March 4 (in 5 days), coffee: oat milk flat white
- Open questions: What got them into woodworking?
- Recent journal: "Had a long call — excited but tired about new job."

Generate 3 conversation prompts.
```

**`_classify()` logic:**
- `days_since_contact > 14` → `"reconnection"`
- Any milestone with `days_until` between 0–7 → `"milestone"`
- No stories AND no details → `"curiosity_seed"`
- Else → `"deepening"`

---

### Step 4 — Dashboard Wired to Prompt Engine

**Modified route:** `dashboard()` in `ui/router.py`:
- Instantiate `PromptEngine`, call `get_daily_prompt(db, user.id)`.
- Pass `daily_prompt: PromptResult | None` to template.

**Modified template:** `app/templates/dashboard/index.html`:
- Replace hardcoded curiosity card with:
  ```html
  {% if daily_prompt %}
    <p class="font-accent text-xl">{{ daily_prompt.prompts[0] }}</p>
    <p class="text-xs text-light-sage/50">About {{ daily_prompt.plot_name }} · refreshes daily</p>
  {% else %}
    <p class="font-accent text-xl text-light-sage/70">
      Add someone to your garden to receive your first prompt.
    </p>
  {% endif %}
  ```

---

### Step 5 — Plot Detail Prompts (HTMX Lazy Load)

**New UI route:**
```
GET /garden/{plot_id}/prompts  → plot_prompts()  [HTMX partial only]
```
Calls `PromptEngine.get_plot_prompts()`. On error, returns a graceful fallback HTML fragment. Returns `partials/prompts_panel.html`.

**New template:** `app/templates/partials/prompts_panel.html` — three prompt cards with a left border in sage-green and font-accent text.

**Modified template:** `app/templates/garden/plot_detail.html` — add "Conversation starters" section with HTMX lazy load:
```html
<div id="prompts-panel"
     hx-get="/garden/{{ plot.id }}/prompts"
     hx-trigger="load"
     hx-swap="innerHTML">
  <!-- skeleton: 3 light-sage rounded rectangles -->
</div>
```

---

### Step 6 — Celery Tasks Implemented

**File:** `app/workers/tasks/notifications.py`

**Pattern:** Each task calls `asyncio.run(_async_impl())`. Uses `AsyncSessionLocal` from `app/core/database.py`.

**Add to `app/core/database.py`:**
```python
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

**`check_reconnection_nudges`:**
- Threshold: `last_connected < now - 14 days` OR `last_connected IS NULL` AND `is_archived = False`
- Cooldown: skip if a `RECONNECTION_NUDGE` notification already exists in the last 7 days with `payload["plot_id"] == str(plot.id)` (uses SQLAlchemy JSONB path operator `.astext`)
- Payload: `{"plot_id", "plot_name", "days_since", "message"}`

**`check_milestone_reminders`:**
- Window: milestones within next 7 days
- Recurring: project `milestone.date` to current year (or next year if already passed)
- De-duplicate: skip if a `MILESTONE_REMINDER` notification already exists this calendar year with `payload["milestone_id"] == str(milestone.id)`
- Payload: `{"milestone_id", "plot_id", "plot_name", "milestone_title", "effective_date", "days_until", "message"}`

---

### Step 7 — Notification UI

**Add to `app/modules/notifications/repository.py`:**
```python
async def count_unread(self, db: AsyncSession, user_id: UUID) -> int
```
Simple `SELECT COUNT(*)` with indexed `user_id` + `is_read = False` filter.

**Helper in `ui/router.py`:**
```python
async def _get_nav_context(user, db) -> dict:
    count = await NotificationRepository().count_unread(db, user.id) if user else 0
    return {"unread_count": count}
```
Every full-page route merges `**await _get_nav_context(user, db)` into the template context.

**New UI routes:**
```
GET  /notifications                    → notifications_page()       [full page]
GET  /notifications/dropdown           → notifications_dropdown()   [HTMX partial]
GET  /notifications/badge             → notifications_badge()      [HTMX polling target]
POST /notifications/{id}/read         → notification_mark_read_ui()
POST /notifications/read-all          → notifications_mark_all_read_ui()
```

**New templates:**
- `app/templates/notifications/index.html` — full list (up to 50), "Mark all read" button
- `app/templates/partials/notifications_dropdown.html` — 10 most recent unread, compact

---

### Step 8 — Nav Rewrite

**File:** `app/templates/partials/nav.html` — **complete rewrite**

Key changes:
1. **Auth-aware:** `{% if user %}` shows bell + user dropdown; `{% else %}` shows "Sign in" link.
2. **Notification bell:** Button triggers `hx-get="/notifications/dropdown"` into a `#notif-dropdown` div. Badge shows `unread_count` from context, polls `/notifications/badge` every 60 seconds via `hx-trigger="every 60s"`.
3. **User dropdown:** `display_name` + chevron, hover reveals "Profile" link + HTMX logout form.
4. **Active state:** `request.url.path` checks on nav links for active styling.
5. **Mobile bottom nav:** `fixed bottom-0` bar with Home / Garden / Journal / Alerts (shown only if `unread_count > 0`). Uses emoji icons (🏠 🌱 📖 🔔).
6. **`base.html`:** Add `pb-16 md:pb-0` to `<main>` to prevent content obscured by bottom nav.

---

### Step 9 — User Profile Page

**New UI routes:**
```
GET  /profile  → profile_page()    [render profile/index.html]
POST /profile  → profile_update()  [calls AuthService.update_profile(), redirect to /profile]
```

**New template:** `app/templates/profile/index.html`
- Account section: `display_name`, `email` (read-only for now)
- Preferences section: placeholder text ("Notification preferences coming soon")
- Danger zone: "Delete account" link (navigates to a static confirm page; actual deletion Phase 3)
- Visual style: matches `plot_form.html`

---

## Verification

1. **Journal:** Navigate to `/journal` → click "New entry" → fill form with plot linked → submit → should land on `/journal/{id}` detail page showing entry + linked plot card. Navigate to linked plot's detail page and confirm entry appears in "Conversations" section.

2. **Prompt Engine:** With `ANTHROPIC_API_KEY` set in `.env`, navigate to `/garden/{plot_id}` — skeleton loader should appear then be replaced by 3 prompts within ~3 seconds. Refresh — prompts should return instantly (cache hit). Add a story and refresh — prompts should regenerate (cache invalidated).

3. **Dashboard prompt:** Navigate to `/` — "Today's curiosity" card should show an AI-generated prompt with a person's name below it. Reload page — same prompt (cached). Check next calendar day — new prompt generated.

4. **Celery tasks:** Manually invoke with `celery -A app.workers.celery_app call app.workers.tasks.notifications.check_reconnection_nudges`. Verify notifications are created in DB for plots with `last_connected` older than 14 days. Run again immediately — verify no duplicate notifications created (cooldown check working).

5. **Notification UI:** After Celery creates notifications, navigate to `/notifications` — list should appear. Click "Mark all read" — badge count in nav should disappear. Navigate to a detail page — badge polling should update count without page reload.

6. **Mobile nav:** Resize browser to <640px — bottom nav bar should appear with Home/Garden/Journal/Alerts tabs. Top nav links should be hidden.

7. **Profile page:** Navigate to `/profile` — form should show current display name. Edit name, submit — redirect back to `/profile` with updated name shown.

8. **Auth-aware nav:** Log out — nav should show "Sign in" link, no bell, no user dropdown. Log back in — bell and user dropdown should reappear.
