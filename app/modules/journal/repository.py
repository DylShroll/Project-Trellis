from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.journal.models import JournalEntry
from app.modules.journal.schemas import JournalEntryCreate, JournalEntryFilters, JournalEntryUpdate


class JournalRepository:
    async def create(
        self, db: AsyncSession, user_id: UUID, data: JournalEntryCreate
    ) -> JournalEntry:
        entry = JournalEntry(
            user_id=user_id,
            plot_id=data.plot_id,
            content=data.content,
            mood_tag=data.mood_tag,
            media_urls=data.media_urls,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    async def get_by_id_for_user(
        self, db: AsyncSession, entry_id: UUID, user_id: UUID
    ) -> JournalEntry | None:
        result = await db.execute(
            select(JournalEntry).where(
                JournalEntry.id == entry_id, JournalEntry.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        filters: JournalEntryFilters,
        limit: int = 20,
        offset: int = 0,
    ) -> list[JournalEntry]:
        query = (
            select(JournalEntry)
            .where(JournalEntry.user_id == user_id)
            .order_by(JournalEntry.created_at.desc())
        )
        if filters.plot_id:
            query = query.where(JournalEntry.plot_id == filters.plot_id)
        if filters.mood_tag:
            query = query.where(JournalEntry.mood_tag == filters.mood_tag)
        if filters.after:
            query = query.where(JournalEntry.created_at >= filters.after)
        if filters.before:
            query = query.where(JournalEntry.created_at <= filters.before)
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, db: AsyncSession, entry: JournalEntry, data: JournalEntryUpdate
    ) -> JournalEntry:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(entry, key, value)
        await db.commit()
        await db.refresh(entry)
        return entry

    async def delete(self, db: AsyncSession, entry: JournalEntry) -> None:
        await db.delete(entry)
        await db.commit()
