from typing import Any
from uuid import UUID

from agents import Agent, RunState
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import RunStateModel


class RunStateRepository:
    """Store SDK resume state separately from the AgentRun domain model."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_factory = session_factory

    async def save(self, run_id: UUID, state: RunState[Any]) -> None:
        serialized_state = state.to_string()
        async with self._session_factory() as session:
            model = await session.get(RunStateModel, run_id)
            if model is None:
                session.add(RunStateModel(run_id=run_id, state=serialized_state))
            else:
                model.state = serialized_state
            await session.commit()

    async def get(
        self, run_id: UUID, agent: Agent[Any]
    ) -> RunState[Any] | None:
        async with self._session_factory() as session:
            model = await session.get(RunStateModel, run_id)
            if model is None:
                return None
            serialized_state = model.state

        return await RunState.from_string(agent, serialized_state)
