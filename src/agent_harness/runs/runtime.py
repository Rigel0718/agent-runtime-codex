from dataclasses import dataclass, field
from typing import Any

from agents import Agent, RunResult, Runner

from .lifecycle import AgentLifecycle
from .model import AgentRun


@dataclass(slots=True)
class AgentRuntime:
    """Run an SDK Agent while keeping its harness lifecycle in sync."""

    run_record: AgentRun
    _lifecycle: AgentLifecycle = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._lifecycle = AgentLifecycle(self.run_record)

    async def run(self, agent: Agent[Any]) -> RunResult:
        self._lifecycle.start()

        try:
            result = await Runner.run(agent, self.run_record.input)
        except Exception:
            self._lifecycle.fail()
            raise

        self._lifecycle.complete()
        return result
