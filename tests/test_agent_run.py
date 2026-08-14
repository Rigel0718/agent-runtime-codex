from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agent_harness import (
    AgentRun,
    AgentRunStateMachine,
    InvalidRunTransitionError,
    RunStatus,
)



def make_run() -> AgentRun:
    return AgentRun(user_id=uuid4(), input="Summarize this document")


def test_agent_run_is_created_with_safe_defaults() -> None:
    run = make_run()

    assert run.status is RunStatus.CREATED
    assert run.current_step == 0
    assert run.run_id
    assert run.created_at.tzinfo is not None
    assert run.updated_at.tzinfo is not None


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_agent_run_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValidationError):
        AgentRun(user_id=uuid4(), input=value)


def test_agent_run_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError):
        AgentRun(
            user_id=uuid4(),
            input="hello",
            created_at=datetime.now(),
        )


def test_happy_path_reaches_completed() -> None:
    run = make_run()
    machine = AgentRunStateMachine(run)

    machine.transition_to(RunStatus.RUNNING)
    machine.advance_step()
    machine.transition_to(RunStatus.COMPLETED)

    assert run.status is RunStatus.COMPLETED
    assert run.current_step == 1
    assert machine.is_terminal


def test_approval_path_can_resume_running() -> None:
    machine = AgentRunStateMachine(make_run())

    machine.transition_to(RunStatus.RUNNING)
    machine.transition_to(RunStatus.WAITING_APPROVAL)
    assert machine.available_transitions == {
        RunStatus.RUNNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }

    machine.transition_to(RunStatus.RUNNING)
    assert machine.run.status is RunStatus.RUNNING


def test_invalid_transition_does_not_mutate_run() -> None:
    run = make_run()
    machine = AgentRunStateMachine(run)
    original_updated_at = run.updated_at

    with pytest.raises(InvalidRunTransitionError) as exc_info:
        machine.transition_to(RunStatus.COMPLETED)

    assert exc_info.value.current is RunStatus.CREATED
    assert exc_info.value.target is RunStatus.COMPLETED
    assert run.status is RunStatus.CREATED
    assert run.updated_at == original_updated_at


def test_terminal_state_cannot_transition() -> None:
    machine = AgentRunStateMachine(make_run())
    machine.transition_to(RunStatus.RUNNING)
    machine.transition_to(RunStatus.FAILED)

    with pytest.raises(InvalidRunTransitionError):
        machine.transition_to(RunStatus.RUNNING)


def test_step_only_advances_while_running() -> None:
    machine = AgentRunStateMachine(make_run())

    with pytest.raises(RuntimeError):
        machine.advance_step()

