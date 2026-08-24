import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from agents import Agent, RunState, Runner

from agent_harness import (
    AgentContext,
    AgentRun,
    AgentRunRepository,
    AgentRuntime,
    ApprovalDecision,
    RunStateRepository,
    RunStatus,
)


def make_runtime(repository: AgentRunRepository | None = None) -> AgentRuntime:
    return AgentRuntime(
        AgentRun(user_id=uuid4(), input="Summarize this document"),
        repository or AsyncMock(spec=AgentRunRepository),
    )


def test_run_executes_sdk_agent_and_completes_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = Agent(name="summarizer")
    expected_result = MagicMock()
    expected_result.interruptions = []
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


def test_run_passes_context_to_sdk_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = make_runtime()
    agent = Agent(name="summarizer")
    context = AgentContext(
        run_id=runtime.run_record.run_id,
        user_id=runtime.run_record.user_id,
    )
    expected_result = MagicMock(interruptions=[])

    async def fake_run(
        starting_agent: Agent[Any],
        input: str,
        **kwargs: Any,
    ) -> Any:
        assert starting_agent is agent
        assert input == runtime.run_record.input
        assert kwargs["context"] is context
        return expected_result

    monkeypatch.setattr(Runner, "run", fake_run)

    result = asyncio.run(runtime.run(agent, context))

    assert result is expected_result


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


def test_run_persists_interruption_and_waits_for_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved_statuses: list[RunStatus] = []

    async def save(run: AgentRun) -> None:
        saved_statuses.append(run.status)

    repository = AsyncMock(spec=AgentRunRepository)
    repository.save.side_effect = save
    state_repository = AsyncMock(spec=RunStateRepository)
    runtime = AgentRuntime(
        AgentRun(user_id=uuid4(), input="Delete the file"),
        repository,
        state_repository,
    )
    state = MagicMock(spec=RunState)
    result = MagicMock()
    result.interruptions = [object()]
    result.to_state.return_value = state

    async def fake_run(*args: Any, **kwargs: Any) -> Any:
        return result

    monkeypatch.setattr(Runner, "run", fake_run)

    actual = asyncio.run(runtime.run(Agent(name="operator")))

    assert actual is result
    assert runtime.run_record.status is RunStatus.WAITING_APPROVAL
    assert saved_statuses == [RunStatus.RUNNING, RunStatus.WAITING_APPROVAL]
    state_repository.save.assert_awaited_once_with(runtime.run_record.run_id, state)


@pytest.mark.parametrize(
    "decision",
    [ApprovalDecision.APPROVE, ApprovalDecision.REJECT],
)
def test_resume_applies_decision_and_completes(
    monkeypatch: pytest.MonkeyPatch,
    decision: ApprovalDecision,
) -> None:
    saved_statuses: list[RunStatus] = []

    async def save(run: AgentRun) -> None:
        saved_statuses.append(run.status)

    repository = AsyncMock(spec=AgentRunRepository)
    repository.save.side_effect = save
    state_repository = AsyncMock(spec=RunStateRepository)
    run_record = AgentRun(
        user_id=uuid4(),
        input="Delete the file",
        status=RunStatus.WAITING_APPROVAL,
    )
    runtime = AgentRuntime(run_record, repository, state_repository)
    interruption = object()
    state = MagicMock(spec=RunState)
    state.get_interruptions.return_value = [interruption]
    state_repository.get.return_value = state
    result = MagicMock()
    result.interruptions = []
    agent = Agent(name="operator")

    async def fake_run(
        starting_agent: Agent[Any], input: Any, **kwargs: Any
    ) -> Any:
        assert starting_agent is agent
        assert input is state
        assert runtime.run_record.status is RunStatus.RUNNING
        return result

    monkeypatch.setattr(Runner, "run", fake_run)

    actual = asyncio.run(runtime.resume(agent, decision))

    assert actual is result
    assert runtime.run_record.status is RunStatus.COMPLETED
    assert saved_statuses == [RunStatus.RUNNING, RunStatus.COMPLETED]
    if decision is ApprovalDecision.APPROVE:
        state.approve.assert_called_once_with(interruption)
    else:
        state.reject.assert_called_once_with(
            interruption,
            rejection_message=None,
        )


def test_resume_passes_context_to_sdk_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = AsyncMock(spec=AgentRunRepository)
    state_repository = AsyncMock(spec=RunStateRepository)
    run_record = AgentRun(
        user_id=uuid4(),
        input="Delete the file",
        status=RunStatus.WAITING_APPROVAL,
    )
    runtime = AgentRuntime(run_record, repository, state_repository)
    agent = Agent(name="operator")
    context = AgentContext(run_id=run_record.run_id, user_id=run_record.user_id)
    interruption = object()
    state = MagicMock(spec=RunState)
    state.get_interruptions.return_value = [interruption]
    state_repository.get.return_value = state
    expected_result = MagicMock(interruptions=[])

    async def fake_run(
        starting_agent: Agent[Any], input: Any, **kwargs: Any
    ) -> Any:
        assert starting_agent is agent
        assert input is state
        assert kwargs["context"] is context
        return expected_result

    monkeypatch.setattr(Runner, "run", fake_run)

    result = asyncio.run(
        runtime.resume(agent, ApprovalDecision.APPROVE, context=context)
    )

    assert result is expected_result
