# Import all models here so Alembic can discover them via Base.metadata
from app.core.database import Base  # noqa: F401
from app.modules.auth.models import User  # noqa: F401
from app.modules.garden.models import Curiosity, Detail, InterestGroup, Milestone, Plot, Story  # noqa: F401
from app.modules.journal.models import JournalEntry  # noqa: F401
from app.modules.notifications.models import Notification  # noqa: F401

__all__ = ["Base", "User", "Plot", "Story", "Detail", "Curiosity", "Milestone", "InterestGroup", "JournalEntry", "Notification"]
