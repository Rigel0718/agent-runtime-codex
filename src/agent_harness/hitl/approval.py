from enum import Enum
from typing import Any

from agents import RunState


class ApprovalDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class PendingApprovalNotFoundError(LookupError):
    pass


class ApprovalHandler:
    """Apply a human decision through the SDK RunState approval API."""

    def apply(
        self,
        state: RunState[Any],
        decision: ApprovalDecision,
        *,
        approval_index: int = 0,
        rejection_message: str | None = None,
    ) -> None:
        interruptions = state.get_interruptions()
        try:
            interruption = interruptions[approval_index]
        except IndexError as error:
            raise PendingApprovalNotFoundError(
                f"pending approval does not exist at index {approval_index}"
            ) from error

        if decision is ApprovalDecision.APPROVE:
            state.approve(interruption)
        else:
            state.reject(interruption, rejection_message=rejection_message)
