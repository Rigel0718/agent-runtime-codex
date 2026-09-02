from dataclasses import dataclass, field, replace
from typing import Any
from uuid import UUID

from agents import FunctionTool
from agents.tool_context import ToolContext

from agent_harness.context import AgentContext
from agent_harness.tracing import TraceEventType, TraceRecorder


class ToolNotRegisteredError(LookupError):
    """Raised when execution is requested for an unknown tool."""

    def __init__(self, name: str) -> None:
        super().__init__(f"tool is not registered: {name}")
        self.name = name


@dataclass(slots=True)
class ToolGateway:
    """Register and execute SDK function tools through a harness boundary."""

    trace_recorder: TraceRecorder | None = None
    _tools: dict[str, FunctionTool] = field(default_factory=dict, init=False, repr=False)

    def register(self, tool: FunctionTool) -> None:
        self._tools[tool.name] = tool

    def resolve(self, name: str) -> FunctionTool:
        try:
            return self._tools[name]
        except KeyError as error:
            raise ToolNotRegisteredError(name) from error

    async def execute(
        self,
        name: str,
        context: ToolContext[Any],
        arguments: str,
    ) -> Any:
        tool = self.resolve(name)
        run_id = self._run_id(context)
        if self.trace_recorder is not None and run_id is not None:
            self.trace_recorder.record(run_id, TraceEventType.TOOL_STARTED)
        try:
            result = await tool.on_invoke_tool(context, arguments)
        except Exception:
            if self.trace_recorder is not None and run_id is not None:
                self.trace_recorder.record(run_id, TraceEventType.TOOL_FAILED)
            raise
        if self.trace_recorder is not None and run_id is not None:
            self.trace_recorder.record(run_id, TraceEventType.TOOL_COMPLETED)
        return result

    def sdk_tool(self, name: str) -> FunctionTool:
        """Return an SDK-compatible tool whose execution passes through the gateway."""
        tool = self.resolve(name)

        async def invoke(context: ToolContext[Any], arguments: str) -> Any:
            return await self.execute(name, context, arguments)

        return replace(tool, on_invoke_tool=invoke)

    @staticmethod
    def _run_id(context: ToolContext[Any]) -> UUID | None:
        agent_context = context.context
        if isinstance(agent_context, AgentContext):
            return agent_context.run_id
        return None
