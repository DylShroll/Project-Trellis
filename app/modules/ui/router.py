from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.redis import get_redis_pool
from app.core.security import decode_access_token
from app.core.templates import templates
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import UserUpdate
from app.modules.auth.service import AuthService
from app.modules.garden.categories import CATEGORY_ICONS, CATEGORY_ORDER, INTEREST_CATEGORIES, MILESTONE_SUGGESTIONS
from app.modules.garden.models import RelationshipTag
from app.modules.garden.schemas import (
    CuriosityCreate,
    DetailCreate,
    InterestGroupAddField,
    InterestGroupCreate,
    MilestoneCreate,
    PlotCreate,
    PlotUpdate,
    StoryCreate,
    StoryUpdate,
)
from app.modules.garden.service import GardenService
from app.modules.journal.repository import JournalRepository
from app.modules.journal.schemas import JournalEntryCreate, JournalEntryFilters
from app.modules.notifications.repository import NotificationRepository
from app.modules.prompts.cache import plot_prompt_key
from app.modules.prompts.engine import PromptEngine
from app.storage.s3 import ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES, delete_object, resize_image, upload_image

router = APIRouter(tags=["ui"])


# ── Cookie auth helper ────────────────────────────────────────────────────────

async def _get_user(request: Request, db: AsyncSession) -> User | None:
    """Decode the httponly `access_token` cookie and return the active user, or None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            return None
    except JWTError:
        return None
    user = await UserRepository().get_by_id(db, UUID(user_id))
    if not user or not user.is_active:
        return None
    return user


def _redirect(url: str, status_code: int = 303) -> Response:
    # 303 See Other is correct for POST→redirect flows (PRG pattern)
    return Response(status_code=status_code, headers={"Location": url})


def _hx_redirect(url: str) -> Response:
    # HTMX uses the HX-Redirect header to navigate the full page after a successful mutation
    return Response(status_code=200, headers={"HX-Redirect": url})


def _get_redis_client() -> aioredis.Redis:
    # Each request creates its own client from the shared pool — always aclose() when done
    return aioredis.Redis(connection_pool=get_redis_pool())


async def _get_nav_context(user: User | None, db: AsyncSession) -> dict:
    """Return template variables needed by the nav bar (unread notification count)."""
    count = await NotificationRepository().count_unread(db, user.id) if user else 0
    return {"unread_count": count}


# ── Auth pages ────────────────────────────────────────────────────────────────

@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    if await _get_user(request, db):
        return _redirect("/")
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    if await _get_user(request, db):
        return _redirect("/")
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/auth/logout")
async def logout() -> Response:
    response = _redirect("/auth/login")
    response.delete_cookie("access_token")
    return response


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    from datetime import date as _date, timezone as _tz

    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    garden = GardenService()
    plots = await garden.list_plots(db, user.id)
    recent_entries = await JournalRepository().list_for_user(
        db, user.id, JournalEntryFilters(), limit=3
    )

    redis = _get_redis_client()
    engine = PromptEngine(redis=redis)
    try:
        daily_prompt = await engine.get_daily_prompt(db, user.id)
    except Exception:
        daily_prompt = None
    finally:
        await redis.aclose()

    # ── Needs Attention: active plots not contacted in 14+ days ──────────────
    now = datetime.now(timezone.utc)
    def _days_since_contact(plot) -> int:
        if plot.last_connected is None:
            return 9999
        dt = plot.last_connected
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).days

    needs_attention = sorted(
        [p for p in plots if not p.is_archived and _days_since_contact(p) > 14],
        key=_days_since_contact,
        reverse=True,
    )[:4]

    # ── Upcoming Milestones: any milestone within the next 30 days ────────────
    today = _date.today()
    upcoming: list[dict] = []
    for plot in plots:
        if plot.is_archived:
            continue
        for m in plot.milestones:
            if m.is_recurring:
                projected = m.date.replace(year=today.year)
                if projected < today:
                    try:
                        projected = m.date.replace(year=today.year + 1)
                    except ValueError:
                        projected = projected.replace(day=28)
            else:
                projected = m.date
            days_until = (projected - today).days
            if 0 <= days_until <= 30:
                upcoming.append({
                    "plot": plot,
                    "title": m.title,
                    "date": projected,
                    "days_until": days_until,
                })
    upcoming.sort(key=lambda x: x["days_until"])

    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": user,
        "recent_plots": plots[:3],
        "recent_entries": recent_entries,
        "daily_prompt": daily_prompt,
        "needs_attention": needs_attention,
        "upcoming_milestones": upcoming[:5],
        **nav_ctx,
    })


# ── Garden pages ──────────────────────────────────────────────────────────────

@router.get("/garden", response_class=HTMLResponse)
async def garden_index(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    all_plots = await GardenService().list_plots(db, user.id)

    # Build a count map of tags present so the filter UI knows which tabs to show
    tag_counts: dict[str, int] = {}
    for p in all_plots:
        tag = p.relationship_tag.value
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Optional single-tag filter via ?tag=
    active_tag = request.query_params.get("tag", "")
    if active_tag and active_tag in tag_counts:
        plots = [p for p in all_plots if p.relationship_tag.value == active_tag]
    else:
        active_tag = ""
        plots = all_plots

    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("garden/index.html", {
        "request": request,
        "user": user,
        "plots": plots,
        "all_plots_count": len(all_plots),
        "tag_counts": tag_counts,
        "active_tag": active_tag,
        **nav_ctx,
    })


@router.get("/garden/new", response_class=HTMLResponse)
async def garden_new(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("garden/plot_form.html", {
        "request": request,
        "user": user,
        "plot": None,
        **nav_ctx,
    })


@router.get("/garden/{plot_id}/edit", response_class=HTMLResponse)
async def garden_edit(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
    except NotFoundError:
        return _redirect("/garden")
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("garden/plot_form.html", {
        "request": request,
        "user": user,
        "plot": plot,
        **nav_ctx,
    })


@router.get("/garden/{plot_id}/timeline", response_class=HTMLResponse)
async def garden_timeline(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    import json as _json
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
    except NotFoundError:
        return _redirect("/garden")

    entries = await JournalRepository().list_for_user(
        db, user.id,
        JournalEntryFilters(plot_id=plot_id),
        limit=500,
    )

    # Build a unified timeline merging journal entries and milestones
    from datetime import timezone as _tz
    timeline_items: list[dict] = []
    for entry in entries:
        dt = entry.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_tz.utc)
        timeline_items.append({"type": "entry", "date": dt.date(), "dt": dt, "data": entry})
    for m in plot.milestones:
        timeline_items.append({"type": "milestone", "date": m.date, "dt": None, "data": m})
    timeline_items.sort(key=lambda x: x["date"], reverse=True)

    # Annotate gap_days relative to the previous (earlier) item
    for i, item in enumerate(timeline_items):
        next_item = timeline_items[i + 1] if i + 1 < len(timeline_items) else None
        if next_item:
            item["gap_days"] = (item["date"] - next_item["date"]).days
        else:
            item["gap_days"] = 0

    # Pull one cached prompt for the top of the timeline (no API call)
    timeline_prompt: str | None = None
    redis = _get_redis_client()
    try:
        cached = await redis.get(plot_prompt_key(str(user.id), str(plot_id)))
        if cached:
            data = _json.loads(cached)
            prompts = data.get("prompts", [])
            timeline_prompt = prompts[0] if prompts else None
    except Exception:
        pass
    finally:
        await redis.aclose()

    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("garden/timeline.html", {
        "request": request,
        "user": user,
        "plot": plot,
        "timeline_items": timeline_items,
        "timeline_prompt": timeline_prompt,
        **nav_ctx,
    })


@router.get("/garden/{plot_id}/prompts", response_class=HTMLResponse)
async def plot_prompts(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)

    redis = _get_redis_client()
    engine = PromptEngine(redis=redis)
    try:
        result = await engine.get_plot_prompts(db, plot_id, user.id)
    except Exception:
        await redis.aclose()
        return templates.TemplateResponse("partials/prompts_panel.html", {
            "request": request,
            "prompts": [],
            "plot_id": plot_id,
            "error": True,
        })
    await redis.aclose()
    return templates.TemplateResponse("partials/prompts_panel.html", {
        "request": request,
        "prompts": result.prompts,
        "plot_id": plot_id,
        "error": False,
    })


@router.get("/garden/{plot_id}", response_class=HTMLResponse)
async def garden_detail(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
    except NotFoundError:
        return _redirect("/garden")

    recent_journal = await JournalRepository().list_for_user(
        db, user.id,
        JournalEntryFilters(plot_id=plot_id),
        limit=3,
    )
    journal_total = await JournalRepository().count_for_plot(db, user.id, plot_id)
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("garden/plot_detail.html", {
        "request": request,
        "user": user,
        "plot": plot,
        "recent_journal": recent_journal,
        "journal_total": journal_total,
        "category_order": CATEGORY_ORDER,
        "category_icons": CATEGORY_ICONS,
        **nav_ctx,
    })


# ── Garden mutations ──────────────────────────────────────────────────────────

@router.post("/garden/new")
async def garden_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    display_name: str = Form(...),
    relationship_tag: str = Form("friend"),
    custom_tag: str = Form(""),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    try:
        data = PlotCreate(
            display_name=display_name,
            relationship_tag=RelationshipTag(relationship_tag),
            custom_tag=custom_tag or None,
        )
    except ValueError:
        return HTMLResponse('<span class="text-warm-clay text-sm">Invalid relationship type.</span>')
    plot = await GardenService().create_plot(db, user.id, data)
    return _hx_redirect(f"/garden/{plot.id}")


@router.post("/garden/{plot_id}/edit")
async def garden_update(
    plot_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    display_name: str = Form(...),
    relationship_tag: str = Form("friend"),
    custom_tag: str = Form(""),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    try:
        data = PlotUpdate(
            display_name=display_name,
            relationship_tag=RelationshipTag(relationship_tag),
            custom_tag=custom_tag or None,
        )
    except ValueError:
        return HTMLResponse('<span class="text-warm-clay text-sm">Invalid relationship type.</span>')
    try:
        plot = await GardenService().update_plot(db, plot_id, user.id, data)
    except NotFoundError:
        return _redirect("/garden")
    return _hx_redirect(f"/garden/{plot.id}")


@router.delete("/garden/{plot_id}")
async def garden_delete(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().delete_plot(db, plot_id, user.id)
    except NotFoundError:
        pass
    return Response(status_code=200)


@router.post("/garden/{plot_id}/connect")
async def garden_connect(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().update_plot(
            db, plot_id, user.id,
            PlotUpdate(last_connected=datetime.now(timezone.utc)),
        )
    except NotFoundError:
        pass
    return Response(status_code=200)


@router.post("/garden/{plot_id}/photo")
async def garden_photo_upload(
    plot_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    photo: UploadFile = File(...),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    if photo.content_type not in ALLOWED_IMAGE_TYPES:
        return _redirect(f"/garden/{plot_id}?photo_error=type")

    content = await photo.read()
    if len(content) > MAX_IMAGE_BYTES:
        return _redirect(f"/garden/{plot_id}?photo_error=size")

    try:
        resized, resized_ct = resize_image(content)
    except Exception:
        return _redirect(f"/garden/{plot_id}?photo_error=upload")

    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
    except NotFoundError:
        return _redirect("/garden")

    old_url = plot.photo_url
    try:
        url = upload_image(resized, resized_ct, str(user.id), scope="plots")
    except Exception:
        return _redirect(f"/garden/{plot_id}?photo_error=upload")

    if old_url:
        try:
            old_key = old_url.split(".amazonaws.com/")[-1]
            delete_object(old_key)
        except Exception:
            pass

    try:
        await GardenService().update_plot(db, plot_id, user.id, PlotUpdate(photo_url=url))
    except NotFoundError:
        return _redirect("/garden")
    return _redirect(f"/garden/{plot_id}")


# ── Stories ───────────────────────────────────────────────────────────────────

@router.get("/garden/{plot_id}/stories/new", response_class=HTMLResponse)
async def story_form(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    return templates.TemplateResponse("partials/story_form.html", {
        "request": request,
        "plot_id": plot_id,
    })


@router.post("/garden/{plot_id}/stories/new")
async def story_create(
    plot_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    content: str = Form(...),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    await GardenService().add_story(db, plot_id, user.id, StoryCreate(content=content))
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()
    return _hx_redirect(f"/garden/{plot_id}")


@router.get("/garden/{plot_id}/stories/{story_id}/edit", response_class=HTMLResponse)
async def story_edit_form(
    plot_id: UUID, story_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    """Return an inline edit form for a single story."""
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
    except NotFoundError:
        return HTMLResponse("", status_code=404)
    story = next((s for s in plot.stories if s.id == story_id), None)
    if not story:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse("partials/story_edit_form.html", {
        "request": request,
        "plot_id": plot_id,
        "story": story,
    })


@router.post("/garden/{plot_id}/stories/{story_id}/edit")
async def story_edit_save(
    plot_id: UUID,
    story_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    content: str = Form(...),
    tags: str = Form(""),
) -> Response:
    """Persist edited story content and tags; returns the updated story card HTML."""
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    # Parse comma-separated tag string into a clean list
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    try:
        story = await GardenService().update_story(
            db, plot_id, story_id, user.id, StoryUpdate(content=content, tags=tag_list)
        )
    except NotFoundError:
        return _redirect("/garden")
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()
    # Return the updated story card HTML to replace the old one in-place
    return templates.TemplateResponse("partials/story_card.html", {
        "request": request,
        "plot_id": plot_id,
        "story": story,
    })


@router.delete("/garden/{plot_id}/stories/{story_id}")
async def story_delete(
    plot_id: UUID, story_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().delete_story(db, plot_id, story_id, user.id)
    except NotFoundError:
        pass
    return Response(status_code=200)


# ── Details ───────────────────────────────────────────────────────────────────

@router.get("/garden/{plot_id}/details/new", response_class=HTMLResponse)
async def detail_form(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    return templates.TemplateResponse("partials/detail_form.html", {
        "request": request,
        "plot_id": plot_id,
        "interest_categories": INTEREST_CATEGORIES,
        "category_order": CATEGORY_ORDER,
    })


@router.post("/garden/{plot_id}/details/new")
async def detail_create(
    plot_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    key: str = Form(...),
    value: str = Form(...),
    category: str = Form(""),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    await GardenService().add_detail(
        db, plot_id, user.id,
        DetailCreate(key=key, value=value, category=category or None),
    )
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()
    return _hx_redirect(f"/garden/{plot_id}")


@router.delete("/garden/{plot_id}/details/{detail_id}")
async def detail_delete(
    plot_id: UUID, detail_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().delete_detail(db, plot_id, detail_id, user.id)
    except NotFoundError:
        pass
    return Response(status_code=200)


# ── Curiosities ───────────────────────────────────────────────────────────────

@router.get("/garden/{plot_id}/curiosities/new", response_class=HTMLResponse)
async def curiosity_form(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    return templates.TemplateResponse("partials/curiosity_form.html", {
        "request": request,
        "plot_id": plot_id,
    })


@router.post("/garden/{plot_id}/curiosities/new")
async def curiosity_create(
    plot_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    question: str = Form(...),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    await GardenService().add_curiosity(
        db, plot_id, user.id, CuriosityCreate(question=question)
    )
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()
    return _hx_redirect(f"/garden/{plot_id}")


@router.post("/garden/{plot_id}/curiosities/{curiosity_id}/resolve")
async def curiosity_resolve(
    plot_id: UUID, curiosity_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().resolve_curiosity(db, plot_id, curiosity_id, user.id)
    except NotFoundError:
        pass
    return Response(status_code=200)


@router.delete("/garden/{plot_id}/curiosities/{curiosity_id}")
async def curiosity_delete(
    plot_id: UUID, curiosity_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().delete_curiosity(db, plot_id, curiosity_id, user.id)
    except NotFoundError:
        pass
    return Response(status_code=200)


# ── Milestones ────────────────────────────────────────────────────────────────

@router.get("/garden/{plot_id}/milestones/new", response_class=HTMLResponse)
async def milestone_form(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    # Fetch the plot so we can surface relationship-type-appropriate milestone suggestions
    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
        rel_tag = plot.relationship_tag.value
    except NotFoundError:
        rel_tag = "friend"
    suggestions = MILESTONE_SUGGESTIONS.get(rel_tag, MILESTONE_SUGGESTIONS.get("friend", []))
    return templates.TemplateResponse("partials/milestone_form.html", {
        "request": request,
        "plot_id": plot_id,
        "suggestions": suggestions,
    })


@router.post("/garden/{plot_id}/milestones/new")
async def milestone_create(
    plot_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
    is_recurring: str = Form(""),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    await GardenService().add_milestone(
        db, plot_id, user.id,
        MilestoneCreate(
            title=title,
            date=date,  # type: ignore[arg-type]
            notes=notes or None,
            is_recurring=is_recurring == "true",
        ),
    )
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()
    return _hx_redirect(f"/garden/{plot_id}")


@router.delete("/garden/{plot_id}/milestones/{milestone_id}")
async def milestone_delete(
    plot_id: UUID, milestone_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().delete_milestone(db, plot_id, milestone_id, user.id)
    except NotFoundError:
        pass
    return Response(status_code=200)


# ── Interest Groups ───────────────────────────────────────────────────────────

@router.get("/garden/{plot_id}/interest-groups/new", response_class=HTMLResponse)
async def interest_group_form(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    return templates.TemplateResponse("partials/interest_group_panel_form.html", {
        "request": request,
        "plot_id": plot_id,
        "interest_categories": INTEREST_CATEGORIES,
        "category_order": CATEGORY_ORDER,
        "category_icons": CATEGORY_ICONS,
    })


@router.post("/garden/{plot_id}/interest-groups/new")
async def interest_group_create(
    plot_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    group_type: str = Form(...),
    custom_label: str = Form(""),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    await GardenService().create_interest_group(
        db, plot_id, user.id,
        InterestGroupCreate(group_type=group_type, custom_label=custom_label or None),
    )
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()
    return _hx_redirect(f"/garden/{plot_id}")


@router.get("/garden/{plot_id}/interest-groups/{group_id}/fields/new", response_class=HTMLResponse)
async def interest_group_field_form(
    plot_id: UUID, group_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    return templates.TemplateResponse("partials/interest_group_field_form.html", {
        "request": request,
        "plot_id": plot_id,
        "group_id": group_id,
    })


@router.post("/garden/{plot_id}/interest-groups/{group_id}/fields/new")
async def interest_group_field_create(
    plot_id: UUID,
    group_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    key: str = Form(...),
    value: str = Form(...),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    try:
        await GardenService().add_field_to_group(
            db, plot_id, group_id, user.id, InterestGroupAddField(key=key, value=value)
        )
    except NotFoundError:
        return _redirect("/garden")
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()
    return _hx_redirect(f"/garden/{plot_id}")


@router.get("/garden/{plot_id}/interest-groups/{group_id}/fields/{field_index}/edit", response_class=HTMLResponse)
async def interest_group_field_edit_form(
    plot_id: UUID, group_id: UUID, field_index: int,
    request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    """Return an inline edit form for a single interest-group field."""
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)
    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
    except NotFoundError:
        return HTMLResponse("", status_code=404)
    group = next((g for g in plot.interest_groups if g.id == group_id), None)
    if not group or not (0 <= field_index < len(group.fields)):
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse("partials/ig_field_edit_form.html", {
        "request": request,
        "plot_id": plot_id,
        "group_id": group_id,
        "field_index": field_index,
        "field": group.fields[field_index],
    })


@router.post("/garden/{plot_id}/interest-groups/{group_id}/fields/{field_index}/edit")
async def interest_group_field_edit_save(
    plot_id: UUID, group_id: UUID, field_index: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    key: str = Form(...),
    value: str = Form(...),
) -> Response:
    """Persist an edited interest-group field."""
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().update_interest_group_field(
            db, plot_id, group_id, user.id, field_index, key, value
        )
    except NotFoundError:
        return _redirect("/garden")
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()
    return Response(status_code=200)


@router.delete("/garden/{plot_id}/interest-groups/{group_id}/fields/{field_index}")
async def interest_group_field_delete(
    plot_id: UUID, group_id: UUID, field_index: int,
    request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().remove_field_from_group(db, plot_id, group_id, user.id, field_index)
    except NotFoundError:
        pass
    return Response(status_code=200)


@router.delete("/garden/{plot_id}/interest-groups/{group_id}")
async def interest_group_delete(
    plot_id: UUID, group_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    try:
        await GardenService().delete_interest_group(db, plot_id, group_id, user.id)
    except NotFoundError:
        pass
    return Response(status_code=200)


# ── JSON import ───────────────────────────────────────────────────────────────

@router.get("/garden/{plot_id}/import", response_class=HTMLResponse)
async def garden_import_form(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    """Show the JSON bulk-import form for a plot."""
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
    except NotFoundError:
        return _redirect("/garden")
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("garden/import_json.html", {
        "request": request,
        "user": user,
        "plot": plot,
        **nav_ctx,
    })


@router.post("/garden/{plot_id}/import")
async def garden_import_submit(
    plot_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    payload: str = Form(...),
) -> Response:
    """Process a JSON import payload and bulk-create knowledge items for a plot."""
    import json as _json

    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    try:
        plot = await GardenService().get_plot(db, plot_id, user.id)
    except NotFoundError:
        return _redirect("/garden")

    nav_ctx = await _get_nav_context(user, db)
    errors: list[str] = []
    imported = {"details": 0, "curiosities": 0, "stories": 0, "milestones": 0}

    # Parse JSON
    try:
        data = _json.loads(payload)
    except _json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON: {exc}")
        return templates.TemplateResponse("garden/import_json.html", {
            "request": request, "user": user, "plot": plot,
            "errors": errors, "payload": payload, **nav_ctx,
        })

    garden = GardenService()

    # Import details
    for idx, item in enumerate(data.get("details", [])):
        try:
            await garden.add_detail(
                db, plot_id, user.id,
                DetailCreate(
                    key=str(item["key"]),
                    value=str(item["value"]),
                    category=str(item["category"]) if item.get("category") else None,
                ),
            )
            imported["details"] += 1
        except Exception as exc:
            errors.append(f"Detail #{idx + 1}: {exc}")

    # Import curiosities (list of strings or dicts with "question" key)
    for idx, item in enumerate(data.get("curiosities", [])):
        try:
            question = item if isinstance(item, str) else item["question"]
            await garden.add_curiosity(
                db, plot_id, user.id, CuriosityCreate(question=str(question))
            )
            imported["curiosities"] += 1
        except Exception as exc:
            errors.append(f"Curiosity #{idx + 1}: {exc}")

    # Import stories (list of strings or dicts with "content" key)
    for idx, item in enumerate(data.get("stories", [])):
        try:
            content = item if isinstance(item, str) else item["content"]
            await garden.add_story(
                db, plot_id, user.id, StoryCreate(content=str(content))
            )
            imported["stories"] += 1
        except Exception as exc:
            errors.append(f"Story #{idx + 1}: {exc}")

    # Import milestones
    for idx, item in enumerate(data.get("milestones", [])):
        try:
            await garden.add_milestone(
                db, plot_id, user.id,
                MilestoneCreate(
                    title=str(item["title"]),
                    date=item["date"],  # type: ignore[arg-type]
                    notes=str(item["notes"]) if item.get("notes") else None,
                    is_recurring=bool(item.get("is_recurring", False)),
                ),
            )
            imported["milestones"] += 1
        except Exception as exc:
            errors.append(f"Milestone #{idx + 1}: {exc}")

    # Invalidate prompt cache since context has changed
    redis = _get_redis_client()
    await redis.delete(plot_prompt_key(str(user.id), str(plot_id)))
    await redis.aclose()

    return templates.TemplateResponse("garden/import_json.html", {
        "request": request, "user": user, "plot": plot,
        "errors": errors, "imported": imported, **nav_ctx,
    })


# ── Journal pages ─────────────────────────────────────────────────────────────

@router.get("/journal", response_class=HTMLResponse)
async def journal_index(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    entries = await JournalRepository().list_for_user(
        db, user.id, JournalEntryFilters(), limit=50
    )
    plots = await GardenService().list_plots(db, user.id)
    plots_by_id = {str(p.id): p for p in plots}
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("journal/index.html", {
        "request": request,
        "user": user,
        "entries": entries,
        "plots_by_id": plots_by_id,
        **nav_ctx,
    })


@router.get("/journal/new", response_class=HTMLResponse)
async def journal_new(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    plots = await GardenService().list_plots(db, user.id)
    selected_plot_id = request.query_params.get("plot_id", "")
    # Pre-fill prompt context when arriving from a curiosity card or conversation starter
    prompt_context = request.query_params.get("prompt", "")
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("journal/entry_form.html", {
        "request": request,
        "user": user,
        "plots": plots,
        "selected_plot_id": selected_plot_id,
        "prompt_context": prompt_context,
        **nav_ctx,
    })


@router.post("/journal/new")
async def journal_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    content: str = Form(...),
    plot_id: str = Form(""),
    mood_tag: str = Form(""),
    photo: UploadFile = File(None),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    parsed_plot_id: UUID | None = None
    if plot_id:
        try:
            parsed_plot_id = UUID(plot_id)
        except ValueError:
            pass

    media_urls: list[str] = []
    if photo and photo.filename:
        photo_content = await photo.read()
        if photo.content_type in ALLOWED_IMAGE_TYPES and len(photo_content) <= MAX_IMAGE_BYTES:
            try:
                resized, resized_ct = resize_image(photo_content)
                url = upload_image(resized, resized_ct, str(user.id), scope="journal")
                media_urls = [url]
            except Exception:
                pass  # photo upload failure is non-blocking

    entry = await JournalRepository().create(
        db, user.id,
        JournalEntryCreate(
            content=content,
            plot_id=parsed_plot_id,
            mood_tag=mood_tag or None,
            media_urls=media_urls,
        ),
    )

    # Set a short-lived reflection key so the detail page can surface a prompt
    if parsed_plot_id:
        redis = _get_redis_client()
        await redis.set(
            f"prompts:reflect:{user.id}:{parsed_plot_id}",
            "1",
            ex=600,  # 10 minutes
        )
        await redis.aclose()

    return _redirect(f"/journal/{entry.id}")


@router.get("/garden/{plot_id}/reflection-prompt", response_class=HTMLResponse)
async def reflection_prompt(
    plot_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)

    redis = _get_redis_client()
    try:
        key = f"prompts:reflect:{user.id}:{plot_id}"
        flag = await redis.get(key)
        if not flag:
            return HTMLResponse("")

        engine = PromptEngine(redis=redis)
        try:
            context = await engine._assembler.for_plot(db, plot_id, user.id)
            context.reflection_mode = True
            prompts = await engine._call_claude(context, "reflection")
            prompt_text = prompts[0] if prompts else None
        except Exception:
            prompt_text = None

        await redis.delete(key)
    finally:
        await redis.aclose()

    if not prompt_text:
        return HTMLResponse("")

    return templates.TemplateResponse("partials/reflection_prompt.html", {
        "request": request,
        "prompt": prompt_text,
    })


@router.get("/journal/{entry_id}", response_class=HTMLResponse)
async def journal_detail(
    entry_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    entry = await JournalRepository().get_by_id_for_user(db, entry_id, user.id)
    if not entry:
        return _redirect("/journal")

    plot = None
    if entry.plot_id:
        try:
            plot = await GardenService().get_plot(db, entry.plot_id, user.id)
        except NotFoundError:
            pass

    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("journal/entry_detail.html", {
        "request": request,
        "user": user,
        "entry": entry,
        "plot": plot,
        **nav_ctx,
    })


@router.post("/journal/{entry_id}/delete")
async def journal_delete(
    entry_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)

    entry = await JournalRepository().get_by_id_for_user(db, entry_id, user.id)
    if entry:
        await JournalRepository().delete(db, entry)
    return Response(status_code=200)


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    repo = NotificationRepository()
    notifications = await repo.list_for_user(db, user.id, limit=50)
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("notifications/index.html", {
        "request": request,
        "user": user,
        "notifications": notifications,
        **nav_ctx,
    })


@router.get("/notifications/dropdown", response_class=HTMLResponse)
async def notifications_dropdown(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return HTMLResponse("", status_code=401)

    repo = NotificationRepository()
    notifications = await repo.list_for_user(db, user.id, unread_only=True, limit=10)
    return templates.TemplateResponse("partials/notifications_dropdown.html", {
        "request": request,
        "notifications": notifications,
    })


@router.get("/notifications/badge", response_class=HTMLResponse)
async def notifications_badge(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    count = await NotificationRepository().count_unread(db, user.id) if user else 0
    if count > 0:
        return HTMLResponse(
            f'<span id="notif-badge" class="absolute -top-1 -right-1 bg-warm-clay text-cream text-xs'
            f' w-4 h-4 rounded-full flex items-center justify-center font-medium">{count}</span>'
        )
    return HTMLResponse('<span id="notif-badge"></span>')


@router.post("/notifications/{notification_id}/read")
async def notification_mark_read_ui(
    notification_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    repo = NotificationRepository()
    notif = await repo.get_by_id_for_user(db, notification_id, user.id)
    if notif:
        await repo.mark_read(db, notif)
    return _hx_redirect("/notifications")


@router.post("/notifications/read-all")
async def notifications_mark_all_read_ui(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return Response(status_code=401)
    await NotificationRepository().mark_all_read(db, user.id)
    return _hx_redirect("/notifications")


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("profile/index.html", {
        "request": request,
        "user": user,
        **nav_ctx,
    })


@router.post("/profile")
async def profile_update(
    request: Request,
    db: AsyncSession = Depends(get_db),
    display_name: str = Form(...),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    redis = _get_redis_client()
    service = AuthService(user_repo=UserRepository(), redis=redis)
    try:
        await service.update_profile(db, user, UserUpdate(display_name=display_name))
    finally:
        await redis.aclose()
    return _redirect("/profile")


@router.post("/profile/avatar")
async def profile_avatar_upload(
    request: Request,
    db: AsyncSession = Depends(get_db),
    avatar: UploadFile = File(...),
) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    if avatar.content_type not in ALLOWED_IMAGE_TYPES:
        return _redirect("/profile?avatar_error=type")

    content = await avatar.read()
    if len(content) > MAX_IMAGE_BYTES:
        return _redirect("/profile?avatar_error=size")

    try:
        resized, resized_ct = resize_image(content)
    except Exception:
        return _redirect("/profile?avatar_error=upload")

    old_url = user.avatar_url
    try:
        url = upload_image(resized, resized_ct, str(user.id), scope="avatars")
    except Exception:
        return _redirect("/profile?avatar_error=upload")

    if old_url:
        try:
            old_key = old_url.split(".amazonaws.com/")[-1]
            delete_object(old_key)
        except Exception:
            pass

    redis = _get_redis_client()
    service = AuthService(user_repo=UserRepository(), redis=redis)
    try:
        await service.update_profile(db, user, UserUpdate(avatar_url=url))
    finally:
        await redis.aclose()
    return _redirect("/profile")
