from dataclasses import dataclass, field, replace
from typing import Any

from agents import FunctionTool
from agents.tool_context import ToolContext


class ToolNotRegisteredError(LookupError):
    """Raised when execution is requested for an unknown tool."""

    def __init__(self, name: str) -> None:
        super().__init__(f"tool is not registered: {name}")
        self.name = name


@dataclass(slots=True)
class ToolGateway:
    """Register and execute SDK function tools through a harness boundary."""

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
        return await tool.on_invoke_tool(context, arguments)

    def sdk_tool(self, name: str) -> FunctionTool:
        """Return an SDK-compatible tool whose execution passes through the gateway."""
        tool = self.resolve(name)

        async def invoke(context: ToolContext[Any], arguments: str) -> Any:
            return await self.execute(name, context, arguments)

        return replace(tool, on_invoke_tool=invoke)
