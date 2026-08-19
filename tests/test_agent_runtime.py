import asyncio
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from agents import Agent, Runner

from agent_harness import AgentRun, AgentRunRepository, AgentRuntime, RunStatus


def make_runtime(repository: AgentRunRepository | None = None) -> AgentRuntime:
    return AgentRuntime(
        AgentRun(user_id=uuid4(), input="Summarize this document"),
        repository or AsyncMock(spec=AgentRunRepository),
    )


def test_run_executes_sdk_agent_and_completes_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = Agent(name="summarizer")
    expected_result = object()
    calls: list[tuple[Agent[Any], str]] = []
    saved_statuses: list[RunStatus] = []

    async def save(run: AgentRun) -> None:
        saved_statuses.append(run.status)

    repository = AsyncMock(spec=AgentRunRepository)
    repository.save.side_effect = save
    runtime = make_runtime(repository)

    async def fake_run(
        starting_agent: Agent[Any],
        input: str,
        **kwargs: Any,
    ) -> Any:
        assert runtime.run_record.status is RunStatus.RUNNING
        calls.append((starting_agent, input))
        return expected_result

    monkeypatch.setattr(Runner, "run", fake_run)

    result = asyncio.run(runtime.run(agent))

    assert result is expected_result
    assert calls == [(agent, runtime.run_record.input)]
    assert runtime.run_record.status is RunStatus.COMPLETED
    assert saved_statuses == [RunStatus.RUNNING, RunStatus.COMPLETED]


def test_run_fails_lifecycle_and_reraises_sdk_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved_statuses: list[RunStatus] = []

    async def save(run: AgentRun) -> None:
        saved_statuses.append(run.status)

    repository = AsyncMock(spec=AgentRunRepository)
    repository.save.side_effect = save
    runtime = make_runtime(repository)
    agent = Agent(name="summarizer")
    sdk_error = RuntimeError("SDK execution failed")

    async def fake_run(*args: Any, **kwargs: Any) -> Any:
        assert runtime.run_record.status is RunStatus.RUNNING
        raise sdk_error

    monkeypatch.setattr(Runner, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(runtime.run(agent))

    assert exc_info.value is sdk_error
    assert runtime.run_record.status is RunStatus.FAILED
    assert saved_statuses == [RunStatus.RUNNING, RunStatus.FAILED]


def test_run_propagates_initial_persistence_error_without_executing_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = AsyncMock(spec=AgentRunRepository)
    persistence_error = RuntimeError("Persistence failed")
    repository.save.side_effect = persistence_error
    runtime = make_runtime(repository)
    sdk_run = AsyncMock()
    monkeypatch.setattr(Runner, "run", sdk_run)

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(runtime.run(Agent(name="summarizer")))

    assert exc_info.value is persistence_error
    assert runtime.run_record.status is RunStatus.RUNNING
    sdk_run.assert_not_awaited()
