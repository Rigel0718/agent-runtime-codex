from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from agent_harness.runs.model import RunStatus

from .database import Base


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status", native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
