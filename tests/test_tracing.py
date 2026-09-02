import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from agents import Agent, Runner, function_tool
from agents.tool_context import ToolContext
from pydantic import ValidationError

from agent_harness import (
    AgentContext,
    AgentRun,
    AgentRunRepository,
    AgentRuntime,
    ToolGateway,
    TraceEvent,
    TraceEventType,
    TraceRecorder,
)


def test_trace_event_requires_an_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="timestamp must be timezone-aware"):
        TraceEvent(
            run_id=uuid4(),
            event_type=TraceEventType.RUN_STARTED,
            timestamp=datetime.now(),
        )


def test_recorder_records_events_in_order() -> None:
    run_id = uuid4()
    recorder = TraceRecorder()

    first = recorder.record(run_id, TraceEventType.RUN_STARTED)
    second = recorder.record(run_id, TraceEventType.RUN_COMPLETED)

    assert recorder.events == [first, second]
    assert all(event.run_id == run_id for event in recorder.events)
    assert all(event.timestamp.tzinfo is not None for event in recorder.events)


def test_runtime_records_successful_run_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_record = AgentRun(user_id=uuid4(), input="Summarize")
    recorder = TraceRecorder()
    runtime = AgentRuntime(
        run_record,
        AsyncMock(spec=AgentRunRepository),
        trace_recorder=recorder,
    )
    result = MagicMock(interruptions=[])
    monkeypatch.setattr(Runner, "run", AsyncMock(return_value=result))

    actual = asyncio.run(runtime.run(Agent(name="summarizer")))

    assert actual is result
    assert [(event.run_id, event.event_type) for event in recorder.events] == [
        (run_record.run_id, TraceEventType.RUN_STARTED),
        (run_record.run_id, TraceEventType.RUN_COMPLETED),
    ]


def test_runtime_records_failed_run_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_record = AgentRun(user_id=uuid4(), input="Summarize")
    recorder = TraceRecorder()
    runtime = AgentRuntime(
        run_record,
        AsyncMock(spec=AgentRunRepository),
        trace_recorder=recorder,
    )
    error = RuntimeError("SDK failed")
    monkeypatch.setattr(Runner, "run", AsyncMock(side_effect=error))

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(runtime.run(Agent(name="summarizer")))

    assert exc_info.value is error
    assert [event.event_type for event in recorder.events] == [
        TraceEventType.RUN_STARTED,
        TraceEventType.RUN_FAILED,
    ]


def traced_tool_context(context: AgentContext) -> ToolContext[Any]:
    return ToolContext(
        context=context,
        tool_name="tool",
        tool_call_id="test-call",
        tool_arguments="{}",
    )


def test_gateway_records_successful_tool_events() -> None:
    @function_tool
    async def answer() -> int:
        """Return an answer."""
        return 42

    context = AgentContext(run_id=uuid4(), user_id=uuid4())
    recorder = TraceRecorder()
    gateway = ToolGateway(trace_recorder=recorder)
    gateway.register(answer)

    result = asyncio.run(gateway.execute("answer", traced_tool_context(context), "{}"))

    assert result == 42
    assert [(event.run_id, event.event_type) for event in recorder.events] == [
        (context.run_id, TraceEventType.TOOL_STARTED),
        (context.run_id, TraceEventType.TOOL_COMPLETED),
    ]


def test_gateway_records_failed_tool_event() -> None:
    error = RuntimeError("tool failed")

    @function_tool(failure_error_function=None)
    async def fail() -> None:
        """Fail deliberately."""
        raise error

    context = AgentContext(run_id=uuid4(), user_id=uuid4())
    recorder = TraceRecorder()
    gateway = ToolGateway(trace_recorder=recorder)
    gateway.register(fail)

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(gateway.execute("fail", traced_tool_context(context), "{}"))

    assert exc_info.value is error
    assert [(event.run_id, event.event_type) for event in recorder.events] == [
        (context.run_id, TraceEventType.TOOL_STARTED),
        (context.run_id, TraceEventType.TOOL_FAILED),
    ]
