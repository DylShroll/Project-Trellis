from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.journal.schemas import (
    JournalEntryCreate,
    JournalEntryFilters,
    JournalEntryRead,
    JournalEntryUpdate,
)
from app.modules.journal.service import JournalService

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])

# Module-level singleton — JournalService holds no mutable state
_svc = JournalService()


@router.post("/", response_model=JournalEntryRead, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: JournalEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.create_entry(db, current_user.id, data)


@router.get("/", response_model=list[JournalEntryRead])
async def list_entries(
    # Query parameters map directly to JournalEntryFilters fields
    plot_id: UUID | None = Query(default=None),
    mood_tag: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    filters = JournalEntryFilters(plot_id=plot_id, mood_tag=mood_tag)
    return await _svc.list_entries(db, current_user.id, filters, limit, offset)


@router.get("/{entry_id}", response_model=JournalEntryRead)
async def get_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.get_entry(db, entry_id, current_user.id)


@router.patch("/{entry_id}", response_model=JournalEntryRead)
async def update_entry(
    entry_id: UUID,
    data: JournalEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    return await _svc.update_entry(db, entry_id, current_user.id, data)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _svc.delete_entry(db, entry_id, current_user.id)
