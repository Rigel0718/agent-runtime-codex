from uuid import UUID

from pydantic import BaseModel


class AgentContext(BaseModel):
    """Harness-owned contextual data for one Agent execution."""

    run_id: UUID
    user_id: UUID
