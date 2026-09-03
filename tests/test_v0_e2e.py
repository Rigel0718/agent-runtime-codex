import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from agents import Agent, RunContextWrapper, RunState, Runner, function_tool
from agents.tool_context import ToolContext
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from agent_harness import (
    AgentContext,
    AgentRun,
    AgentRunRepository,
    AgentRuntime,
    ApprovalDecision,
    RunStateRepository,
    RunStatus,
    ToolGateway,
    TraceEventType,
    TraceRecorder,
)
from agent_harness.persistence import (
    Base,
    create_database_engine,
    create_session_factory,
)


class RecordingAgentRunRepository(AgentRunRepository):
    """Record persisted transitions while retaining real database behavior."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        super().__init__(session_factory)
        self.saved_statuses: list[RunStatus] = []

    async def save(self, run: AgentRun) -> None:
        self.saved_statuses.append(run.status)
        await super().save(run)


async def make_repositories(
    tmp_path: Path,
    database_name: str,
) -> tuple[AsyncEngine, RecordingAgentRunRepository, RunStateRepository]:
    engine = create_database_engine(
        f"sqlite+aiosqlite:///{tmp_path / database_name}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)
    return (
        engine,
        RecordingAgentRunRepository(session_factory),
        RunStateRepository(session_factory),
    )


def test_normal_run_connects_context_tool_trace_and_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        engine, repository, state_repository = await make_repositories(
            tmp_path, "normal-e2e.db"
        )
        try:
            run = AgentRun(user_id=uuid4(), input="Identify the current user")
            context = AgentContext(run_id=run.run_id, user_id=run.user_id)
            recorder = TraceRecorder()
            gateway = ToolGateway(trace_recorder=recorder)
            received_contexts: list[AgentContext] = []

            @function_tool
            async def current_user(wrapper: RunContextWrapper[AgentContext]) -> str:
                """Return the current user identifier."""
                received_contexts.append(wrapper.context)
                return str(wrapper.context.user_id)

            gateway.register(current_user)
            agent = Agent(name="operator", tools=[gateway.sdk_tool("current_user")])
            expected_result = MagicMock(interruptions=[])
            expected_result.final_output = str(context.user_id)

            async def sdk_run(
                starting_agent: Agent[Any],
                input: str,
                **kwargs: Any,
            ) -> Any:
                assert starting_agent is agent
                assert input == run.input
                assert kwargs["context"] is context
                tool = starting_agent.tools[0]
                output = await tool.on_invoke_tool(
                    ToolContext(
                        context=kwargs["context"],
                        tool_name=tool.name,
                        tool_call_id="normal-e2e-call",
                        tool_arguments="{}",
                    ),
                    "{}",
                )
                assert output == str(context.user_id)
                return expected_result

            monkeypatch.setattr(Runner, "run", sdk_run)
            runtime = AgentRuntime(
                run,
                repository,
                state_repository,
                trace_recorder=recorder,
            )

            result = await runtime.run(agent, context)
            persisted = await repository.get(run.run_id)

            assert result.final_output == str(context.user_id)
            assert received_contexts == [context]
            assert repository.saved_statuses == [
                RunStatus.RUNNING,
                RunStatus.COMPLETED,
            ]
            assert persisted is not None
            assert persisted.status is RunStatus.COMPLETED
            assert [(event.run_id, event.event_type) for event in recorder.events] == [
                (run.run_id, TraceEventType.RUN_STARTED),
                (run.run_id, TraceEventType.TOOL_STARTED),
                (run.run_id, TraceEventType.TOOL_COMPLETED),
                (run.run_id, TraceEventType.RUN_COMPLETED),
            ]
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "decision",
    [ApprovalDecision.APPROVE, ApprovalDecision.REJECT],
)
def test_hitl_persists_restores_and_resumes_sdk_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: ApprovalDecision,
) -> None:
    async def scenario() -> None:
        engine, repository, state_repository = await make_repositories(
            tmp_path, f"hitl-{decision.value}-e2e.db"
        )
        try:
            run = AgentRun(user_id=uuid4(), input="Perform a sensitive action")
            context = AgentContext(run_id=run.run_id, user_id=run.user_id)
            agent = Agent(name="operator")
            pending = object()
            saved_state = MagicMock(spec=RunState)
            saved_state.to_string.return_value = '{"pending": true}'
            interrupted_result = MagicMock(interruptions=[pending])
            interrupted_result.to_state.return_value = saved_state

            restored_state = MagicMock(spec=RunState)
            restored_state.get_interruptions.return_value = [pending]
            completed_result = MagicMock(interruptions=[])
            from_string_calls: list[tuple[Agent[Any], str]] = []

            async def from_string(
                restored_agent: Agent[Any], serialized_state: str
            ) -> Any:
                from_string_calls.append((restored_agent, serialized_state))
                return restored_state

            monkeypatch.setattr(RunState, "from_string", from_string)
            sdk_inputs: list[Any] = []

            async def sdk_run(
                starting_agent: Agent[Any], input: Any, **kwargs: Any
            ) -> Any:
                assert starting_agent is agent
                assert kwargs["context"] is context
                sdk_inputs.append(input)
                if len(sdk_inputs) == 1:
                    return interrupted_result
                assert input is restored_state
                return completed_result

            monkeypatch.setattr(Runner, "run", sdk_run)
            runtime = AgentRuntime(run, repository, state_repository)

            assert await runtime.run(agent, context) is interrupted_result
            waiting = await repository.get(run.run_id)
            assert waiting is not None
            assert waiting.status is RunStatus.WAITING_APPROVAL

            assert (
                await runtime.resume(agent, decision, context=context)
                is completed_result
            )
            persisted = await repository.get(run.run_id)

            assert sdk_inputs == [run.input, restored_state]
            assert from_string_calls == [(agent, '{"pending": true}')]
            assert repository.saved_statuses == [
                RunStatus.RUNNING,
                RunStatus.WAITING_APPROVAL,
                RunStatus.RUNNING,
                RunStatus.COMPLETED,
            ]
            assert persisted is not None
            assert persisted.status is RunStatus.COMPLETED
            if decision is ApprovalDecision.APPROVE:
                restored_state.approve.assert_called_once_with(pending)
                restored_state.reject.assert_not_called()
            else:
                restored_state.reject.assert_called_once_with(
                    pending, rejection_message=None
                )
                restored_state.approve.assert_not_called()
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_tool_failure_traces_propagates_and_persists_failed_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        engine, repository, state_repository = await make_repositories(
            tmp_path, "failure-e2e.db"
        )
        try:
            run = AgentRun(user_id=uuid4(), input="Call the failing tool")
            context = AgentContext(run_id=run.run_id, user_id=run.user_id)
            recorder = TraceRecorder()
            gateway = ToolGateway(trace_recorder=recorder)
            tool_error = RuntimeError("deliberate tool failure")

            @function_tool(failure_error_function=None)
            async def fail() -> None:
                """Fail deliberately."""
                raise tool_error

            gateway.register(fail)
            agent = Agent(name="operator", tools=[gateway.sdk_tool("fail")])

            async def sdk_run(
                starting_agent: Agent[Any], input: str, **kwargs: Any
            ) -> Any:
                tool = starting_agent.tools[0]
                return await tool.on_invoke_tool(
                    ToolContext(
                        context=kwargs["context"],
                        tool_name=tool.name,
                        tool_call_id="failure-e2e-call",
                        tool_arguments="{}",
                    ),
                    "{}",
                )

            monkeypatch.setattr(Runner, "run", sdk_run)
            runtime = AgentRuntime(
                run,
                repository,
                state_repository,
                trace_recorder=recorder,
            )

            with pytest.raises(RuntimeError) as exc_info:
                await runtime.run(agent, context)

            persisted = await repository.get(run.run_id)
            assert exc_info.value is tool_error
            assert repository.saved_statuses == [
                RunStatus.RUNNING,
                RunStatus.FAILED,
            ]
            assert persisted is not None
            assert persisted.status is RunStatus.FAILED
            assert [event.event_type for event in recorder.events] == [
                TraceEventType.RUN_STARTED,
                TraceEventType.TOOL_STARTED,
                TraceEventType.TOOL_FAILED,
                TraceEventType.RUN_FAILED,
            ]
            assert all(event.run_id == run.run_id for event in recorder.events)
        finally:
            await engine.dispose()

    asyncio.run(scenario())
