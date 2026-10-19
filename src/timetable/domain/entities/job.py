
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: UUID
    status: JobStatus
    input_ref: str
    result_ref: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    heartbeat_at: datetime | None = None
