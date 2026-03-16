from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.security import decode_access_token
from app.core.templates import templates
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
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
from app.modules.journal.schemas import JournalEntryFilters

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
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": user,
        "recent_plots": plots[:3],
        "recent_entries": recent_entries,
    })


# ── Garden pages ──────────────────────────────────────────────────────────────

@router.get("/garden", response_class=HTMLResponse)
async def garden_index(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    plots = await GardenService().list_plots(db, user.id)
    return templates.TemplateResponse("garden/index.html", {
        "request": request,
        "user": user,
        "plots": plots,
    })


@router.get("/garden/new", response_class=HTMLResponse)
async def garden_new(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")
    return templates.TemplateResponse("garden/plot_form.html", {
        "request": request,
        "user": user,
        "plot": None,
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
    return templates.TemplateResponse("garden/plot_form.html", {
        "request": request,
        "user": user,
        "plot": plot,
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
    return templates.TemplateResponse("garden/plot_detail.html", {
        "request": request,
        "user": user,
        "plot": plot,
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


# ── Journal page ──────────────────────────────────────────────────────────────

@router.get("/journal", response_class=HTMLResponse)
async def journal_index(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    user = await _get_user(request, db)
    if not user:
        return _redirect("/auth/login")

    entries = await JournalRepository().list_for_user(
        db, user.id, JournalEntryFilters(), limit=50
    )
    return templates.TemplateResponse("journal/index.html", {
        "request": request,
        "user": user,
        "entries": entries,
    })
