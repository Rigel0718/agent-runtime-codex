from dataclasses import dataclass, field
from typing import Any

from agents import Agent, RunResult, Runner, RunState

from agent_harness.hitl import ApprovalDecision, ApprovalHandler
from agent_harness.persistence.repository import AgentRunRepository
from agent_harness.persistence.run_state_repository import RunStateRepository

from .lifecycle import AgentLifecycle
from .model import AgentRun


@dataclass(slots=True)
class AgentRuntime:
    """Run an SDK Agent while keeping its harness lifecycle in sync."""

    run_record: AgentRun
    repository: AgentRunRepository
    run_state_repository: RunStateRepository | None = None
    _lifecycle: AgentLifecycle = field(init=False, repr=False)
    _approval_handler: ApprovalHandler = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._lifecycle = AgentLifecycle(self.run_record)
        self._approval_handler = ApprovalHandler()

    async def run(self, agent: Agent[Any]) -> RunResult:
        self._lifecycle.start()
        await self.repository.save(self.run_record)

        try:
            result = await Runner.run(agent, self.run_record.input)
        except Exception:
            self._lifecycle.fail()
            await self.repository.save(self.run_record)
            raise

        return await self._handle_result(result)

    async def resume(
        self,
        agent: Agent[Any],
        decision: ApprovalDecision,
        *,
        approval_index: int = 0,
        rejection_message: str | None = None,
    ) -> RunResult:
        if self.run_state_repository is None:
            raise RuntimeError("RunState persistence is required to resume an AgentRun")

        state = await self.run_state_repository.get(self.run_record.run_id, agent)
        if state is None:
            raise LookupError(f"RunState does not exist for run {self.run_record.run_id}")

        self._approval_handler.apply(
            state,
            decision,
            approval_index=approval_index,
            rejection_message=rejection_message,
        )
        self._lifecycle.resume()
        await self.repository.save(self.run_record)

        try:
            result = await Runner.run(agent, state)
        except Exception:
            self._lifecycle.fail()
            await self.repository.save(self.run_record)
            raise

        return await self._handle_result(result)

    async def _handle_result(self, result: RunResult) -> RunResult:
        if result.interruptions:
            if self.run_state_repository is None:
                raise RuntimeError(
                    "RunState persistence is required for approval interruption"
                )
            self._lifecycle.request_approval()
            await self.repository.save(self.run_record)
            state: RunState[Any] = result.to_state()
            await self.run_state_repository.save(self.run_record.run_id, state)
            return result

        self._lifecycle.complete()
        await self.repository.save(self.run_record)
        return result
