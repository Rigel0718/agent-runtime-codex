from collections.abc import Mapping
from dataclasses import dataclass

from .model import AgentRun, RunStatus, utc_now


ALLOWED_TRANSITIONS: Mapping[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset(
        {
            RunStatus.RUNNING, 
            RunStatus.CANCELLED,
        }
        ),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.WAITING_APPROVAL,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.WAITING_APPROVAL: frozenset(
        {
            RunStatus.RUNNING, 
            RunStatus.FAILED,   # 중간에 오류날 수도 있으니까 일단 FAILED를 넣는다. -> 추후에 삭제할 수도
            RunStatus.CANCELLED
        }
    ),

    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}


class InvalidRunTransitionError(ValueError):
    def __init__(self, current: RunStatus, target: RunStatus) -> None:
        super().__init__(f"invalid AgentRun transition: {current.value} -> {target.value}")
        self.current = current
        self.target = target


@dataclass(slots=True)
class AgentRunStateMachine:
    """Apply deterministic lifecycle rules to an AgentRun."""

    run: AgentRun

    @property
    def available_transitions(self) -> frozenset[RunStatus]:
        return ALLOWED_TRANSITIONS[self.run.status]

    @property
    def is_terminal(self) -> bool:
        return not self.available_transitions

    def can_transition_to(self, target: RunStatus) -> bool:
        return target in self.available_transitions

    def transition_to(self, target: RunStatus) -> AgentRun:
        if not self.can_transition_to(target):
            raise InvalidRunTransitionError(self.run.status, target)

        self.run.status = target
        self.run.updated_at = utc_now()
        return self.run

    def advance_step(self) -> AgentRun:
        if self.run.status is not RunStatus.RUNNING:
            raise RuntimeError("AgentRun steps can only advance while running")

        self.run.current_step += 1
        self.run.updated_at = utc_now()
        return self.run


