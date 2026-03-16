from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.garden.models import Curiosity, Detail, Milestone, Plot, Story
from app.modules.garden.repository import (
    CuriosityRepository,
    DetailRepository,
    MilestoneRepository,
    PlotRepository,
    StoryRepository,
)
from app.modules.garden.schemas import (
    CuriosityCreate,
    DetailCreate,
    DetailUpdate,
    MilestoneCreate,
    MilestoneUpdate,
    PlotCreate,
    PlotUpdate,
    StoryCreate,
)


class GardenService:
    def __init__(self) -> None:
        self.plots = PlotRepository()
        self.stories = StoryRepository()
        self.details = DetailRepository()
        self.curiosities = CuriosityRepository()
        self.milestones = MilestoneRepository()

    # --- Plots ---

    async def list_plots(self, db: AsyncSession, user_id: UUID) -> list[Plot]:
        return await self.plots.list_for_user(db, user_id)

    async def get_plot(self, db: AsyncSession, plot_id: UUID, user_id: UUID) -> Plot:
        plot = await self.plots.get_by_id_for_user(db, plot_id, user_id)
        if not plot:
            raise NotFoundError("Plot not found")
        return plot

    async def create_plot(self, db: AsyncSession, user_id: UUID, data: PlotCreate) -> Plot:
        return await self.plots.create(db, user_id, data)

    async def update_plot(
        self, db: AsyncSession, plot_id: UUID, user_id: UUID, data: PlotUpdate
    ) -> Plot:
        plot = await self.get_plot(db, plot_id, user_id)
        return await self.plots.update(db, plot, data)

    async def delete_plot(self, db: AsyncSession, plot_id: UUID, user_id: UUID) -> None:
        plot = await self.get_plot(db, plot_id, user_id)
        await self.plots.delete(db, plot)

    # --- Stories ---

    async def add_story(
        self, db: AsyncSession, plot_id: UUID, user_id: UUID, data: StoryCreate
    ) -> Story:
        await self.get_plot(db, plot_id, user_id)  # ownership check
        return await self.stories.create(db, plot_id, data)

    async def delete_story(
        self, db: AsyncSession, plot_id: UUID, story_id: UUID, user_id: UUID
    ) -> None:
        await self.get_plot(db, plot_id, user_id)  # ownership check
        story = await self.stories.get_by_id_for_plot(db, story_id, plot_id)
        if not story:
            raise NotFoundError("Story not found")
        await self.stories.delete(db, story)

    # --- Details ---

    async def add_detail(
        self, db: AsyncSession, plot_id: UUID, user_id: UUID, data: DetailCreate
    ) -> Detail:
        await self.get_plot(db, plot_id, user_id)
        return await self.details.create(db, plot_id, data)

    async def update_detail(
        self,
        db: AsyncSession,
        plot_id: UUID,
        detail_id: UUID,
        user_id: UUID,
        data: DetailUpdate,
    ) -> Detail:
        await self.get_plot(db, plot_id, user_id)
        detail = await self.details.get_by_id_for_plot(db, detail_id, plot_id)
        if not detail:
            raise NotFoundError("Detail not found")
        return await self.details.update(db, detail, data)

    async def delete_detail(
        self, db: AsyncSession, plot_id: UUID, detail_id: UUID, user_id: UUID
    ) -> None:
        await self.get_plot(db, plot_id, user_id)
        detail = await self.details.get_by_id_for_plot(db, detail_id, plot_id)
        if not detail:
            raise NotFoundError("Detail not found")
        await self.details.delete(db, detail)

    # --- Curiosities ---

    async def add_curiosity(
        self, db: AsyncSession, plot_id: UUID, user_id: UUID, data: CuriosityCreate
    ) -> Curiosity:
        await self.get_plot(db, plot_id, user_id)
        return await self.curiosities.create(db, plot_id, data)

    async def resolve_curiosity(
        self, db: AsyncSession, plot_id: UUID, curiosity_id: UUID, user_id: UUID
    ) -> Curiosity:
        await self.get_plot(db, plot_id, user_id)
        curiosity = await self.curiosities.get_by_id_for_plot(db, curiosity_id, plot_id)
        if not curiosity:
            raise NotFoundError("Curiosity not found")
        return await self.curiosities.resolve(db, curiosity)

    async def delete_curiosity(
        self, db: AsyncSession, plot_id: UUID, curiosity_id: UUID, user_id: UUID
    ) -> None:
        await self.get_plot(db, plot_id, user_id)
        curiosity = await self.curiosities.get_by_id_for_plot(db, curiosity_id, plot_id)
        if not curiosity:
            raise NotFoundError("Curiosity not found")
        await self.curiosities.delete(db, curiosity)

    # --- Milestones ---

    async def add_milestone(
        self, db: AsyncSession, plot_id: UUID, user_id: UUID, data: MilestoneCreate
    ) -> Milestone:
        await self.get_plot(db, plot_id, user_id)
        return await self.milestones.create(db, plot_id, data)

    async def update_milestone(
        self,
        db: AsyncSession,
        plot_id: UUID,
        milestone_id: UUID,
        user_id: UUID,
        data: MilestoneUpdate,
    ) -> Milestone:
        await self.get_plot(db, plot_id, user_id)
        milestone = await self.milestones.get_by_id_for_plot(db, milestone_id, plot_id)
        if not milestone:
            raise NotFoundError("Milestone not found")
        return await self.milestones.update(db, milestone, data)

    async def delete_milestone(
        self, db: AsyncSession, plot_id: UUID, milestone_id: UUID, user_id: UUID
    ) -> None:
        await self.get_plot(db, plot_id, user_id)
        milestone = await self.milestones.get_by_id_for_plot(db, milestone_id, plot_id)
        if not milestone:
            raise NotFoundError("Milestone not found")
        await self.milestones.delete(db, milestone)
