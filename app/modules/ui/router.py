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
from app.modules.garden.categories import CATEGORY_ICONS, CATEGORY_ORDER, INTEREST_CATEGORIES
from app.modules.garden.models import RelationshipTag
from app.modules.garden.schemas import (
    CuriosityCreate,
    DetailCreate,
    MilestoneCreate,
    PlotCreate,
    PlotUpdate,
    StoryCreate,
)
from app.modules.garden.service import GardenService
from app.modules.journal.repository import JournalRepository
from app.modules.journal.schemas import JournalEntryCreate, JournalEntryFilters
from app.modules.notifications.repository import NotificationRepository
from app.modules.prompts.cache import plot_prompt_key
from app.modules.prompts.engine import PromptEngine
from app.storage.s3 import ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES, upload_image

router = APIRouter(tags=["ui"])


# ── Cookie auth helper ────────────────────────────────────────────────────────

async def _get_user(request: Request, db: AsyncSession) -> User | None:
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
    return Response(status_code=status_code, headers={"Location": url})


def _hx_redirect(url: str) -> Response:
    return Response(status_code=200, headers={"HX-Redirect": url})


def _get_redis_client() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_redis_pool())


async def _get_nav_context(user: User | None, db: AsyncSession) -> dict:
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

    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": user,
        "recent_plots": plots[:3],
        "recent_entries": recent_entries,
        "daily_prompt": daily_prompt,
        **nav_ctx,
    })


# ── Garden pages ──────────────────────────────────────────────────────────────

@router.get("/garden", response_class=HTMLResponse)
async def garden_index(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    plots = await GardenService().list_plots(db, user.id)
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("garden/index.html", {
        "request": request,
        "user": user,
        "plots": plots,
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
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("garden/timeline.html", {
        "request": request,
        "user": user,
        "plot": plot,
        "entries": entries,
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
            "error": True,
        })
    await redis.aclose()
    return templates.TemplateResponse("partials/prompts_panel.html", {
        "request": request,
        "prompts": result.prompts,
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
        url = upload_image(content, photo.content_type or "image/jpeg", str(user.id), scope="plots")
    except Exception:
        return _redirect(f"/garden/{plot_id}?photo_error=upload")

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
    return templates.TemplateResponse("partials/milestone_form.html", {
        "request": request,
        "plot_id": plot_id,
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
    nav_ctx = await _get_nav_context(user, db)
    return templates.TemplateResponse("journal/entry_form.html", {
        "request": request,
        "user": user,
        "plots": plots,
        "selected_plot_id": selected_plot_id,
        **nav_ctx,
    })


@router.post("/journal/new")
async def journal_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    content: str = Form(...),
    plot_id: str = Form(""),
    mood_tag: str = Form(""),
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

    entry = await JournalRepository().create(
        db, user.id,
        JournalEntryCreate(
            content=content,
            plot_id=parsed_plot_id,
            mood_tag=mood_tag or None,
        ),
    )
    return _hx_redirect(f"/journal/{entry.id}")


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
        url = upload_image(content, avatar.content_type or "image/jpeg", str(user.id), scope="avatars")
    except Exception:
        return _redirect("/profile?avatar_error=upload")

    redis = _get_redis_client()
    service = AuthService(user_repo=UserRepository(), redis=redis)
    try:
        await service.update_profile(db, user, UserUpdate(avatar_url=url))
    finally:
        await redis.aclose()
    return _redirect("/profile")
