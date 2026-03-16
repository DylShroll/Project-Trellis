import json
import re
from datetime import datetime, timezone
from uuid import UUID

import anthropic
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.prompts.cache import PROMPT_TTL, daily_prompt_key, plot_prompt_key
from app.modules.prompts.context import ContextAssembler
from app.modules.prompts.schemas import PlotContext, PromptResult

SYSTEM_PROMPT = """\
You are a thoughtful companion helping someone be more curious and present with the people they love.

You will receive structured information about a person in the user's life.

TONE: Warm and curious. Second-person, present tense. Specific — reference what you know. Never urgent
or guilt-inducing. Leave the user feeling invited, not obligated. Avoid: "reach out," "check in," "touch base."

FORMAT: Return exactly 3 prompts as a numbered list. No preamble, no explanation.
1. [prompt]
2. [prompt]
3. [prompt]

RULES:
- If a milestone is approaching: weave it naturally into a deeper question, don't just mention the date.
- If the user hasn't connected recently: at least one prompt should be a low-pressure, specific opening.
- If the profile is sparse: generate prompts that open doors, not deepen existing knowledge.
"""


def _build_user_message(context: PlotContext) -> str:
    lines = [
        f"Person: {context.display_name}",
        f"Relationship: {context.relationship_tag}",
    ]
    if context.days_since_contact is not None:
        lines.append(f"Days since last contact: {context.days_since_contact}")
    else:
        lines.append("Days since last contact: unknown")

    lines.append("")
    lines.append("What you know:")

    if context.stories:
        lines.append(f"- Stories: {', '.join(context.stories)}")
    if context.details:
        detail_strs = [f"{d['key']}: {d['value']}" for d in context.details]
        lines.append(f"- Details: {', '.join(detail_strs)}")
    if context.curiosities:
        lines.append(f"- Open questions: {'; '.join(context.curiosities)}")
    if context.milestones:
        ms_parts = []
        for m in context.milestones:
            days = m["days_until"]
            suffix = f"in {days} days" if days >= 0 else f"{abs(days)} days ago"
            ms_parts.append(f"{m['title']} ({suffix})")
        lines.append(f"- Milestones: {', '.join(ms_parts)}")
    if context.recent_journal:
        lines.append(f"- Recent journal: {'; '.join(f'\"{j}\"' for j in context.recent_journal)}")

    lines.append("")
    lines.append("Generate 3 conversation prompts.")
    return "\n".join(lines)


def _classify(context: PlotContext) -> str:
    if context.days_since_contact is not None and context.days_since_contact > 14:
        return "reconnection"
    for m in context.milestones:
        days = m.get("days_until")
        if days is not None and 0 <= days <= 7:
            return "milestone"
    if not context.stories and not context.details:
        return "curiosity_seed"
    return "deepening"


def _parse_prompts(text: str) -> list[str]:
    prompts = []
    for line in text.strip().splitlines():
        line = line.strip()
        match = re.match(r"^\d+\.\s+(.+)$", line)
        if match:
            prompts.append(match.group(1).strip())
    return prompts if prompts else [text.strip()]


class PromptEngine:
    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self._assembler = ContextAssembler()

    async def get_plot_prompts(
        self, db: AsyncSession, plot_id: UUID, user_id: UUID
    ) -> PromptResult:
        key = plot_prompt_key(str(user_id), str(plot_id))
        cached = await self.redis.get(key)
        if cached:
            data = json.loads(cached)
            data["cache_hit"] = True
            return PromptResult(**data)

        context = await self._assembler.for_plot(db, plot_id, user_id)
        prompts = await self._call_claude(context, "plot")
        category = _classify(context)

        result = PromptResult(
            prompts=prompts,
            category=category,
            generated_at=datetime.now(timezone.utc),
            plot_id=plot_id,
            plot_name=context.display_name,
            cache_hit=False,
        )
        await self.redis.set(key, result.model_dump_json(), ex=PROMPT_TTL)
        return result

    async def get_daily_prompt(
        self, db: AsyncSession, user_id: UUID
    ) -> PromptResult | None:
        key = daily_prompt_key(str(user_id))
        cached = await self.redis.get(key)
        if cached:
            data = json.loads(cached)
            data["cache_hit"] = True
            return PromptResult(**data)

        result_tuple = await self._assembler.for_daily(db, user_id)
        if result_tuple is None:
            return None

        context, plot_id, plot_name = result_tuple
        prompts = await self._call_claude(context, "daily")
        category = _classify(context)

        result = PromptResult(
            prompts=prompts[:1],  # daily card shows only 1
            category=category,
            generated_at=datetime.now(timezone.utc),
            plot_id=plot_id,
            plot_name=plot_name,
            cache_hit=False,
        )
        await self.redis.set(key, result.model_dump_json(), ex=PROMPT_TTL)
        return result

    async def _call_claude(self, context: PlotContext, mode: str) -> list[str]:
        client = anthropic.AsyncAnthropic()
        message = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            timeout=10,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _build_user_message(context)}
            ],
        )
        raw = message.content[0].text if message.content else ""
        return _parse_prompts(raw)
