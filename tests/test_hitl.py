from unittest.mock import MagicMock

import pytest
from agents import RunState

from agent_harness import (
    ApprovalDecision,
    ApprovalHandler,
    PendingApprovalNotFoundError,
)


def test_approval_handler_approves_pending_sdk_interruption() -> None:
    interruption = object()
    state = MagicMock(spec=RunState)
    state.get_interruptions.return_value = [interruption]

    ApprovalHandler().apply(state, ApprovalDecision.APPROVE)

    state.approve.assert_called_once_with(interruption)
    state.reject.assert_not_called()


def test_approval_handler_rejects_with_message() -> None:
    interruption = object()
    state = MagicMock(spec=RunState)
    state.get_interruptions.return_value = [interruption]

    ApprovalHandler().apply(
        state,
        ApprovalDecision.REJECT,
        rejection_message="Not permitted",
    )

    state.reject.assert_called_once_with(
        interruption,
        rejection_message="Not permitted",
    )


def test_approval_handler_rejects_unknown_pending_index() -> None:
    state = MagicMock(spec=RunState)
    state.get_interruptions.return_value = []

    with pytest.raises(PendingApprovalNotFoundError):
        ApprovalHandler().apply(state, ApprovalDecision.APPROVE)
