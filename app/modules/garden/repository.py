from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.garden.models import Curiosity, Detail, Milestone, Plot, Story
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


class PlotRepository:
    def _with_relations(self):
        return (
            selectinload(Plot.stories),
            selectinload(Plot.details),
            selectinload(Plot.curiosities),
            selectinload(Plot.milestones),
        )

    async def list_for_user(self, db: AsyncSession, user_id: UUID) -> list[Plot]:
        result = await db.execute(
            select(Plot)
            .where(Plot.user_id == user_id)
            .order_by(Plot.display_name.asc())
        )
        return list(result.scalars().all())

    async def get_by_id_for_user(
        self, db: AsyncSession, plot_id: UUID, user_id: UUID
    ) -> Plot | None:
        result = await db.execute(
            select(Plot)
            .options(*self._with_relations())
            .where(Plot.id == plot_id, Plot.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, user_id: UUID, data: PlotCreate) -> Plot:
        plot = Plot(user_id=user_id, **data.model_dump())
        db.add(plot)
        await db.commit()
        # Reload with relations
        return await self.get_by_id_for_user(db, plot.id, user_id)  # type: ignore[return-value]

    async def update(self, db: AsyncSession, plot: Plot, data: PlotUpdate) -> Plot:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(plot, key, value)
        await db.commit()
        return await self.get_by_id_for_user(db, plot.id, plot.user_id)  # type: ignore[return-value]

    async def delete(self, db: AsyncSession, plot: Plot) -> None:
        await db.delete(plot)
        await db.commit()


class StoryRepository:
    async def create(self, db: AsyncSession, plot_id: UUID, data: StoryCreate) -> Story:
        story = Story(plot_id=plot_id, content=data.content)
        db.add(story)
        await db.commit()
        await db.refresh(story)
        return story

    async def get_by_id_for_plot(
        self, db: AsyncSession, story_id: UUID, plot_id: UUID
    ) -> Story | None:
        result = await db.execute(
            select(Story).where(Story.id == story_id, Story.plot_id == plot_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, db: AsyncSession, story: Story) -> None:
        await db.delete(story)
        await db.commit()


class DetailRepository:
    async def create(self, db: AsyncSession, plot_id: UUID, data: DetailCreate) -> Detail:
        detail = Detail(plot_id=plot_id, **data.model_dump())
        db.add(detail)
        await db.commit()
        await db.refresh(detail)
        return detail

    async def get_by_id_for_plot(
        self, db: AsyncSession, detail_id: UUID, plot_id: UUID
    ) -> Detail | None:
        result = await db.execute(
            select(Detail).where(Detail.id == detail_id, Detail.plot_id == plot_id)
        )
        return result.scalar_one_or_none()

    async def update(self, db: AsyncSession, detail: Detail, data: DetailUpdate) -> Detail:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(detail, key, value)
        await db.commit()
        await db.refresh(detail)
        return detail

    async def delete(self, db: AsyncSession, detail: Detail) -> None:
        await db.delete(detail)
        await db.commit()


class CuriosityRepository:
    async def create(self, db: AsyncSession, plot_id: UUID, data: CuriosityCreate) -> Curiosity:
        curiosity = Curiosity(plot_id=plot_id, question=data.question)
        db.add(curiosity)
        await db.commit()
        await db.refresh(curiosity)
        return curiosity

    async def get_by_id_for_plot(
        self, db: AsyncSession, curiosity_id: UUID, plot_id: UUID
    ) -> Curiosity | None:
        result = await db.execute(
            select(Curiosity).where(Curiosity.id == curiosity_id, Curiosity.plot_id == plot_id)
        )
        return result.scalar_one_or_none()

    async def resolve(self, db: AsyncSession, curiosity: Curiosity) -> Curiosity:
        curiosity.is_resolved = True
        await db.commit()
        await db.refresh(curiosity)
        return curiosity

    async def delete(self, db: AsyncSession, curiosity: Curiosity) -> None:
        await db.delete(curiosity)
        await db.commit()


class MilestoneRepository:
    async def create(self, db: AsyncSession, plot_id: UUID, data: MilestoneCreate) -> Milestone:
        milestone = Milestone(plot_id=plot_id, **data.model_dump())
        db.add(milestone)
        await db.commit()
        await db.refresh(milestone)
        return milestone

    async def get_by_id_for_plot(
        self, db: AsyncSession, milestone_id: UUID, plot_id: UUID
    ) -> Milestone | None:
        result = await db.execute(
            select(Milestone).where(Milestone.id == milestone_id, Milestone.plot_id == plot_id)
        )
        return result.scalar_one_or_none()

    async def update(self, db: AsyncSession, milestone: Milestone, data: MilestoneUpdate) -> Milestone:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(milestone, key, value)
        await db.commit()
        await db.refresh(milestone)
        return milestone

    async def delete(self, db: AsyncSession, milestone: Milestone) -> None:
        await db.delete(milestone)
        await db.commit()
