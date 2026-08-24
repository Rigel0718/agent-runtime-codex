import asyncio
from typing import Any
from uuid import uuid4

import pytest
from agents import FunctionTool, RunContextWrapper, function_tool, set_tracing_disabled
from agents.tool_context import ToolContext

from agent_harness import AgentContext, ToolGateway, ToolNotRegisteredError


set_tracing_disabled(True)


def tool_context(name: str, arguments: str) -> ToolContext[Any]:
    return ToolContext(
        context=None,
        tool_name=name,
        tool_call_id="test-call",
        tool_arguments=arguments,
    )


def test_registered_tool_receives_arguments_and_returns_result() -> None:
    received: list[tuple[int, int]] = []

    @function_tool
    async def add(left: int, right: int) -> int:
        """Add two integers."""
        received.append((left, right))
        return left + right

    gateway = ToolGateway()
    gateway.register(add)

    result = asyncio.run(
        gateway.execute(
            "add",
            tool_context("add", '{"left": 2, "right": 3}'),
            '{"left": 2, "right": 3}',
        )
    )

    assert received == [(2, 3)]
    assert result == 5


def test_unregistered_tool_cannot_be_resolved_or_executed() -> None:
    gateway = ToolGateway()

    with pytest.raises(ToolNotRegisteredError, match="missing"):
        gateway.resolve("missing")

    with pytest.raises(ToolNotRegisteredError, match="missing"):
        asyncio.run(
            gateway.execute("missing", tool_context("missing", "{}"), "{}")
        )


def test_tool_error_is_propagated() -> None:
    tool_error = RuntimeError("tool failed")

    @function_tool(failure_error_function=None)
    async def fail() -> None:
        """Fail deliberately."""
        raise tool_error

    gateway = ToolGateway()
    gateway.register(fail)

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(gateway.execute("fail", tool_context("fail", "{}"), "{}"))

    assert exc_info.value is tool_error


def test_sdk_compatible_tool_preserves_definition_and_uses_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @function_tool
    async def echo(message: str) -> str:
        """Return the supplied message."""
        return message

    gateway = ToolGateway()
    gateway.register(echo)
    calls: list[tuple[str, str]] = []
    original_execute = ToolGateway.execute

    async def record_execute(
        self: ToolGateway,
        name: str,
        context: ToolContext[Any],
        arguments: str,
    ) -> Any:
        calls.append((name, arguments))
        return await original_execute(self, name, context, arguments)

    monkeypatch.setattr(ToolGateway, "execute", record_execute)

    sdk_tool = gateway.sdk_tool("echo")
    result = asyncio.run(
        sdk_tool.on_invoke_tool(
            tool_context("echo", '{"message": "hello"}'),
            '{"message": "hello"}',
        )
    )

    assert isinstance(sdk_tool, FunctionTool)
    assert sdk_tool.name == echo.name
    assert sdk_tool.description == echo.description
    assert sdk_tool.params_json_schema == echo.params_json_schema
    assert calls == [("echo", '{"message": "hello"}')]
    assert result == "hello"


def test_tool_can_access_agent_context() -> None:
    context = AgentContext(run_id=uuid4(), user_id=uuid4())
    received_contexts: list[AgentContext] = []

    @function_tool
    async def current_user(wrapper: RunContextWrapper[AgentContext]) -> str:
        """Return the current user identifier."""
        received_contexts.append(wrapper.context)
        return str(wrapper.context.user_id)

    gateway = ToolGateway()
    gateway.register(current_user)
    sdk_context = ToolContext(
        context=context,
        tool_name="current_user",
        tool_call_id="test-call",
        tool_arguments="{}",
    )

    result = asyncio.run(
        gateway.sdk_tool("current_user").on_invoke_tool(sdk_context, "{}")
    )

    assert received_contexts == [context]
    assert result == str(context.user_id)
