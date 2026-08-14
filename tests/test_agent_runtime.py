import asyncio
from typing import Any
from uuid import uuid4

import pytest
from agents import Agent, Runner

from agent_harness import AgentRun, AgentRuntime, RunStatus


def make_runtime() -> AgentRuntime:
    return AgentRuntime(
        AgentRun(user_id=uuid4(), input="Summarize this document")
    )


def test_run_executes_sdk_agent_and_completes_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = make_runtime()
    agent = Agent(name="summarizer")
    expected_result = object()
    calls: list[tuple[Agent[Any], str]] = []

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


def test_run_fails_lifecycle_and_reraises_sdk_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = make_runtime()
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
