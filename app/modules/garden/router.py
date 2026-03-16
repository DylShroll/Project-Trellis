from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user
from app.modules.auth.models import User
from app.modules.garden.schemas import (
    CuriosityCreate,
    CuriosityRead,
    DetailCreate,
    DetailRead,
    DetailUpdate,
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    PlotCreate,
    PlotListItem,
    PlotRead,
    PlotUpdate,
    StoryCreate,
    StoryRead,
)
from app.modules.garden.service import GardenService

router = APIRouter(prefix="/api/v1/garden", tags=["garden"])

_svc = GardenService()


# ── Plots ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[PlotListItem])
async def list_plots(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    return await _svc.list_plots(db, current_user.id)


@router.post("/", response_model=PlotRead, status_code=status.HTTP_201_CREATED)
async def create_plot(
    data: PlotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.create_plot(db, current_user.id, data)


@router.get("/{plot_id}", response_model=PlotRead)
async def get_plot(
    plot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.get_plot(db, plot_id, current_user.id)


@router.patch("/{plot_id}", response_model=PlotRead)
async def update_plot(
    plot_id: UUID,
    data: PlotUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.update_plot(db, plot_id, current_user.id, data)


@router.delete("/{plot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plot(
    plot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _svc.delete_plot(db, plot_id, current_user.id)


# ── Stories ────────────────────────────────────────────────────────────────────

@router.post("/{plot_id}/stories", response_model=StoryRead, status_code=status.HTTP_201_CREATED)
async def add_story(
    plot_id: UUID,
    data: StoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.add_story(db, plot_id, current_user.id, data)


@router.delete("/{plot_id}/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(
    plot_id: UUID,
    story_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _svc.delete_story(db, plot_id, story_id, current_user.id)


# ── Details ────────────────────────────────────────────────────────────────────

@router.post("/{plot_id}/details", response_model=DetailRead, status_code=status.HTTP_201_CREATED)
async def add_detail(
    plot_id: UUID,
    data: DetailCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.add_detail(db, plot_id, current_user.id, data)


@router.patch("/{plot_id}/details/{detail_id}", response_model=DetailRead)
async def update_detail(
    plot_id: UUID,
    detail_id: UUID,
    data: DetailUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.update_detail(db, plot_id, detail_id, current_user.id, data)


@router.delete("/{plot_id}/details/{detail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detail(
    plot_id: UUID,
    detail_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _svc.delete_detail(db, plot_id, detail_id, current_user.id)


# ── Curiosities ────────────────────────────────────────────────────────────────

@router.post(
    "/{plot_id}/curiosities",
    response_model=CuriosityRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_curiosity(
    plot_id: UUID,
    data: CuriosityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.add_curiosity(db, plot_id, current_user.id, data)


@router.post(
    "/{plot_id}/curiosities/{curiosity_id}/resolve",
    response_model=CuriosityRead,
)
async def resolve_curiosity(
    plot_id: UUID,
    curiosity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.resolve_curiosity(db, plot_id, curiosity_id, current_user.id)


@router.delete(
    "/{plot_id}/curiosities/{curiosity_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_curiosity(
    plot_id: UUID,
    curiosity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _svc.delete_curiosity(db, plot_id, curiosity_id, current_user.id)


# ── Milestones ─────────────────────────────────────────────────────────────────

@router.post(
    "/{plot_id}/milestones",
    response_model=MilestoneRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_milestone(
    plot_id: UUID,
    data: MilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.add_milestone(db, plot_id, current_user.id, data)


@router.patch("/{plot_id}/milestones/{milestone_id}", response_model=MilestoneRead)
async def update_milestone(
    plot_id: UUID,
    milestone_id: UUID,
    data: MilestoneUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.update_milestone(db, plot_id, milestone_id, current_user.id, data)


@router.delete(
    "/{plot_id}/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_milestone(
    plot_id: UUID,
    milestone_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _svc.delete_milestone(db, plot_id, milestone_id, current_user.id)
