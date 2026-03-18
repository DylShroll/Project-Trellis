from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes, selectinload

from app.modules.garden.models import Curiosity, Detail, InterestGroup, Milestone, Plot, Story
from app.modules.garden.schemas import (
    CuriosityCreate,
    DetailCreate,
    DetailUpdate,
    InterestGroupAddField,
    InterestGroupCreate,
    MilestoneCreate,
    MilestoneUpdate,
    PlotCreate,
    PlotUpdate,
    StoryCreate,
    StoryUpdate,
)


class PlotRepository:
    def _with_relations(self):
        # Eagerly load all child collections in a single round-trip (selectinload avoids N+1)
        return (
            selectinload(Plot.stories),
            selectinload(Plot.details),
            selectinload(Plot.curiosities),
            selectinload(Plot.milestones),
            selectinload(Plot.interest_groups),
        )

    async def list_for_user(self, db: AsyncSession, user_id: UUID) -> list[Plot]:
        result = await db.execute(
            select(Plot)
            .options(*self._with_relations())
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
        # Re-fetch with all relations so the returned object is fully populated
        return await self.get_by_id_for_user(db, plot.id, user_id)  # type: ignore[return-value]

    async def update(self, db: AsyncSession, plot: Plot, data: PlotUpdate) -> Plot:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(plot, key, value)
        await db.commit()
        # Re-fetch after commit so SQLAlchemy picks up server-side `updated_at` changes
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

    async def update(self, db: AsyncSession, story: Story, data: StoryUpdate) -> Story:
        """Persist content and/or tag changes to a story."""
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(story, key, value)
        await db.commit()
        await db.refresh(story)
        return story

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


class InterestGroupRepository:
    async def create(
        self, db: AsyncSession, plot_id: UUID, data: InterestGroupCreate
    ) -> InterestGroup:
        group = InterestGroup(
            plot_id=plot_id,
            group_type=data.group_type,
            custom_label=data.custom_label,
            fields=[],  # start with empty JSONB array
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)
        return group

    async def get_by_id_for_plot(
        self, db: AsyncSession, group_id: UUID, plot_id: UUID
    ) -> InterestGroup | None:
        result = await db.execute(
            select(InterestGroup).where(
                InterestGroup.id == group_id, InterestGroup.plot_id == plot_id
            )
        )
        return result.scalar_one_or_none()

    async def add_field(
        self, db: AsyncSession, group: InterestGroup, field: InterestGroupAddField
    ) -> InterestGroup:
        current = list(group.fields or [])
        current.append({"key": field.key, "value": field.value})
        group.fields = current
        # flag_modified is required to tell SQLAlchemy a JSONB column changed in-place
        attributes.flag_modified(group, "fields")
        await db.commit()
        await db.refresh(group)
        return group

    async def update_field(
        self, db: AsyncSession, group: InterestGroup, field_index: int, key: str, value: str
    ) -> InterestGroup:
        """Replace the key/value of a single field inside the JSONB array."""
        current = list(group.fields or [])
        if 0 <= field_index < len(current):
            current[field_index] = {"key": key, "value": value}
            group.fields = current
            # flag_modified is required to tell SQLAlchemy a JSONB column changed in-place
            attributes.flag_modified(group, "fields")
            await db.commit()
            await db.refresh(group)
        return group

    async def remove_field(
        self, db: AsyncSession, group: InterestGroup, field_index: int
    ) -> InterestGroup:
        current = list(group.fields or [])
        if 0 <= field_index < len(current):
            current.pop(field_index)
            group.fields = current
            attributes.flag_modified(group, "fields")
            await db.commit()
            await db.refresh(group)
        return group

    async def delete(self, db: AsyncSession, group: InterestGroup) -> None:
        await db.delete(group)
        await db.commit()
