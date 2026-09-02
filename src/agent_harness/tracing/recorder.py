from dataclasses import dataclass, field
from uuid import UUID

from .model import TraceEvent, TraceEventType


@dataclass(slots=True)
class TraceRecorder:
    """Record trace events in memory for the current process."""

    events: list[TraceEvent] = field(default_factory=list)

    def record(self, run_id: UUID, event_type: TraceEventType) -> TraceEvent:
        event = TraceEvent(run_id=run_id, event_type=event_type)
        self.events.append(event)
        return event
