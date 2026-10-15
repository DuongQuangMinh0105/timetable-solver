from dataclasses import dataclass
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
