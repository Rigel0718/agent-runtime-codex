from dataclasses import dataclass, field

from .model import AgentRun, RunStatus
from .state_machine import AgentRunStateMachine


@dataclass(slots=True)
class AgentLifecycle:
    """Expose semantic lifecycle operations for an AgentRun."""

    run: AgentRun
    _state_machine: AgentRunStateMachine = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._state_machine = AgentRunStateMachine(self.run)

    def start(self) -> AgentRun:
        return self._state_machine.transition_to(RunStatus.RUNNING)

    def complete(self) -> AgentRun:
        return self._state_machine.transition_to(RunStatus.COMPLETED)

    def fail(self) -> AgentRun:
        return self._state_machine.transition_to(RunStatus.FAILED)

    def cancel(self) -> AgentRun:
        return self._state_machine.transition_to(RunStatus.CANCELLED)

    def request_approval(self) -> AgentRun:
        return self._state_machine.transition_to(RunStatus.WAITING_APPROVAL)

    def resume(self) -> AgentRun:
        return self._state_machine.transition_to(RunStatus.RUNNING)
