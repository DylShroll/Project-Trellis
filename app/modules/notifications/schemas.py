from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.notifications.models import NotificationType


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    type: NotificationType
    payload: dict
    is_read: bool
    scheduled_at: datetime | None
    sent_at: datetime | None
    created_at: datetime


class NotificationUpdate(BaseModel):
    is_read: bool
