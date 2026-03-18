from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.notifications.models import Notification, NotificationType
from app.modules.notifications.repository import NotificationRepository


class NotificationService:
    def __init__(self) -> None:
        self.repo = NotificationRepository()

    async def create(
        self,
        db: AsyncSession,
        user_id: UUID,
        notification_type: NotificationType,
        payload: dict,
    ) -> Notification:
        return await self.repo.create(db, user_id, notification_type, payload)

    async def list_notifications(
        self,
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Notification]:
        return await self.repo.list_for_user(db, user_id, unread_only, limit, offset)

    async def mark_read(
        self, db: AsyncSession, notification_id: UUID, user_id: UUID
    ) -> Notification:
        # Fetch by both ID and user_id to prevent users from marking another user's notification read
        notification = await self.repo.get_by_id_for_user(db, notification_id, user_id)
        if not notification:
            raise NotFoundError("Notification not found")
        return await self.repo.mark_read(db, notification)

    async def mark_all_read(self, db: AsyncSession, user_id: UUID) -> int:
        # Returns the count of updated rows so the caller can report how many were affected
        return await self.repo.mark_all_read(db, user_id)
