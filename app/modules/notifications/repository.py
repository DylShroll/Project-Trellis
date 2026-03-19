from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification, NotificationType


class NotificationRepository:
    async def create(
        self,
        db: AsyncSession,
        user_id: UUID,
        notification_type: NotificationType,
        payload: dict,
    ) -> Notification:
        notification = Notification(
            user_id=user_id, type=notification_type, payload=payload
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    async def get_by_id_for_user(
        self, db: AsyncSession, notification_id: UUID, user_id: UUID
    ) -> Notification | None:
        # user_id scope prevents one user from reading another's notification
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, db: AsyncSession, user_id: UUID, unread_only: bool = False, limit: int = 20, offset: int = 0
    ) -> list[Notification]:
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        if unread_only:
            # SQLAlchemy requires == False (not `is False`) for mapped boolean columns
            query = query.where(Notification.is_read == False)  # noqa: E712
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def mark_read(self, db: AsyncSession, notification: Notification) -> Notification:
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        return notification

    async def count_unread(self, db: AsyncSession, user_id: UUID) -> int:
        # Used by the nav badge — must be fast; user_id is indexed
        result = await db.execute(
            select(func.count()).where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
        )
        return result.scalar_one()

    async def mark_all_read(self, db: AsyncSession, user_id: UUID) -> int:
        from sqlalchemy import update
        # Bulk UPDATE avoids loading every notification into memory
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .values(is_read=True)
        )
        await db.commit()
        # rowcount lets the caller know how many rows were affected
        return result.rowcount
