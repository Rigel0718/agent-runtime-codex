from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_harness.runs.model import AgentRun

from .models import AgentRunModel


class AgentRunRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_factory = session_factory

    async def save(self, run: AgentRun) -> None:
        async with self._session_factory() as session:
            model = await session.get(AgentRunModel, run.run_id)
            if model is None:
                session.add(_to_model(run))
            else:
                _update_model(model, run)
            await session.commit()

    async def get(self, run_id: UUID) -> AgentRun | None:
        async with self._session_factory() as session:
            model = await session.get(AgentRunModel, run_id)
            if model is None:
                return None
            return _to_domain(model)


def _to_model(run: AgentRun) -> AgentRunModel:
    return AgentRunModel(
        run_id=run.run_id,
        user_id=run.user_id,
        input=run.input,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _update_model(model: AgentRunModel, run: AgentRun) -> None:
    model.user_id = run.user_id
    model.input = run.input
    model.status = run.status
    model.created_at = run.created_at
    model.updated_at = run.updated_at


def _to_domain(model: AgentRunModel) -> AgentRun:
    return AgentRun(
        run_id=model.run_id,
        user_id=model.user_id,
        input=model.input,
        status=model.status,
        created_at=_as_aware_utc(model.created_at),
        updated_at=_as_aware_utc(model.updated_at),
    )


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
