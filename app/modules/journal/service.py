from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.journal.models import JournalEntry
from app.modules.journal.repository import JournalRepository
from app.modules.journal.schemas import (
    JournalEntryCreate,
    JournalEntryFilters,
    JournalEntryUpdate,
)


class JournalService:
    """Thin service layer over JournalRepository.

    Ownership checks (user_id scoping) happen in the repository via
    `get_by_id_for_user`; this layer raises NotFoundError for callers to
    handle rather than returning None.
    """

    def __init__(self) -> None:
        self.repo = JournalRepository()

    async def create_entry(
        self, db: AsyncSession, user_id: UUID, data: JournalEntryCreate
    ) -> JournalEntry:
        return await self.repo.create(db, user_id, data)

    async def get_entry(
        self, db: AsyncSession, entry_id: UUID, user_id: UUID
    ) -> JournalEntry:
        entry = await self.repo.get_by_id_for_user(db, entry_id, user_id)
        if not entry:
            raise NotFoundError("Journal entry not found")
        return entry

    async def list_entries(
        self,
        db: AsyncSession,
        user_id: UUID,
        filters: JournalEntryFilters,
        limit: int = 20,
        offset: int = 0,
    ) -> list[JournalEntry]:
        return await self.repo.list_for_user(db, user_id, filters, limit, offset)

    async def update_entry(
        self,
        db: AsyncSession,
        entry_id: UUID,
        user_id: UUID,
        data: JournalEntryUpdate,
    ) -> JournalEntry:
        # get_entry raises NotFoundError if the entry doesn't belong to this user
        entry = await self.get_entry(db, entry_id, user_id)
        return await self.repo.update(db, entry, data)

    async def delete_entry(
        self, db: AsyncSession, entry_id: UUID, user_id: UUID
    ) -> None:
        entry = await self.get_entry(db, entry_id, user_id)
        await self.repo.delete(db, entry)
