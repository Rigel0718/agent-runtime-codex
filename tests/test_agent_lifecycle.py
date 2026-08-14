from collections.abc import Callable
from uuid import uuid4

import pytest

from agent_harness import (
    AgentLifecycle,
    AgentRun,
    AgentRunStateMachine,
    InvalidRunTransitionError,
    RunStatus,
)


def make_lifecycle() -> AgentLifecycle:
    run = AgentRun(user_id=uuid4(), input="Summarize this document")
    return AgentLifecycle(run)


def test_happy_path_completes_run() -> None:
    lifecycle = make_lifecycle()

    assert lifecycle.start() is lifecycle.run
    assert lifecycle.run.status is RunStatus.RUNNING

    assert lifecycle.complete() is lifecycle.run
    assert lifecycle.run.status is RunStatus.COMPLETED


def test_approval_path_resumes_run() -> None:
    lifecycle = make_lifecycle()

    lifecycle.start()
    lifecycle.request_approval()
    assert lifecycle.run.status is RunStatus.WAITING_APPROVAL

    lifecycle.resume()
    assert lifecycle.run.status is RunStatus.RUNNING


@pytest.mark.parametrize(
    ("prepare", "operation", "expected_status"),
    [
        ((), "cancel", RunStatus.CANCELLED),
        (("start",), "fail", RunStatus.FAILED),
        (("start",), "cancel", RunStatus.CANCELLED),
        (("start", "request_approval"), "fail", RunStatus.FAILED),
        (("start", "request_approval"), "cancel", RunStatus.CANCELLED),
    ],
)
def test_terminal_operations_follow_state_machine_rules(
    prepare: tuple[str, ...],
    operation: str,
    expected_status: RunStatus,
) -> None:
    lifecycle = make_lifecycle()
    lifecycle_operation: Callable[[], AgentRun]

    for method_name in prepare:
        getattr(lifecycle, method_name)()

    lifecycle_operation = getattr(lifecycle, operation)
    lifecycle_operation()

    assert lifecycle.run.status is expected_status


def test_invalid_semantic_operation_preserves_run() -> None:
    lifecycle = make_lifecycle()
    original_updated_at = lifecycle.run.updated_at

    with pytest.raises(InvalidRunTransitionError):
        lifecycle.complete()

    assert lifecycle.run.status is RunStatus.CREATED
    assert lifecycle.run.updated_at == original_updated_at


def test_semantic_operation_delegates_to_state_machine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = make_lifecycle()
    targets: list[RunStatus] = []
    original_transition = AgentRunStateMachine.transition_to

    def record_transition(
        state_machine: AgentRunStateMachine,
        target: RunStatus,
    ) -> AgentRun:
        targets.append(target)
        return original_transition(state_machine, target)

    monkeypatch.setattr(AgentRunStateMachine, "transition_to", record_transition)

    lifecycle.start()

    assert targets == [RunStatus.RUNNING]
