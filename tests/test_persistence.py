import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from unittest.mock import MagicMock

from agents import Agent, RunState

from agent_harness import AgentRun, AgentRunRepository, RunStateRepository, RunStatus
from agent_harness.persistence import (
    Base,
    create_database_engine,
    create_session_factory,
)


def test_agent_run_repository_round_trip_and_update(tmp_path: Path) -> None:
    async def scenario() -> None:
        engine = create_database_engine(
            f"sqlite+aiosqlite:///{tmp_path / 'agent-runs.db'}"
        )
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

            repository = AgentRunRepository(create_session_factory(engine))
            created_at = datetime(2026, 8, 19, 1, 2, 3, tzinfo=timezone.utc)
            updated_at = datetime(2026, 8, 19, 4, 5, 6, tzinfo=timezone.utc)
            run = AgentRun(
                run_id=uuid4(),
                user_id=uuid4(),
                input="Persist every field",
                status=RunStatus.RUNNING,
                created_at=created_at,
                updated_at=updated_at,
            )

            await repository.save(run)

            assert await repository.get(run.run_id) == run

            run.input = "Persist the current state"
            run.status = RunStatus.WAITING_APPROVAL
            run.updated_at = datetime(
                2026, 8, 19, 7, 8, 9, tzinfo=timezone.utc
            )
            await repository.save(run)

            assert await repository.get(run.run_id) == run
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_agent_run_repository_returns_none_for_unknown_run(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        engine = create_database_engine(
            f"sqlite+aiosqlite:///{tmp_path / 'agent-runs.db'}"
        )
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

            repository = AgentRunRepository(create_session_factory(engine))

            assert await repository.get(uuid4()) is None
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_run_state_repository_round_trip(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def scenario() -> None:
        engine = create_database_engine(
            f"sqlite+aiosqlite:///{tmp_path / 'run-states.db'}"
        )
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

            session_factory = create_session_factory(engine)
            run = AgentRun(user_id=uuid4(), input="Needs approval")
            await AgentRunRepository(session_factory).save(run)
            repository = RunStateRepository(session_factory)
            state = MagicMock(spec=RunState)
            state.to_string.return_value = '{"saved": true}'
            restored_state = object()
            from_string = AsyncMock(return_value=restored_state)
            monkeypatch.setattr(RunState, "from_string", from_string)
            agent = Agent(name="operator")

            await repository.save(run.run_id, state)

            assert await repository.get(run.run_id, agent) is restored_state
            from_string.assert_awaited_once_with(agent, '{"saved": true}')
        finally:
            await engine.dispose()

    from unittest.mock import AsyncMock

    asyncio.run(scenario())
