"""Tạo một job mẫu: ghi input vào storage và lưu job (QUEUED) vào Postgres."""

import os
from pathlib import Path
from uuid import uuid4

from timetable.domain.entities.job import Job, JobStatus
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.storage.local import LocalStorage


def main() -> None:
    storage = LocalStorage(Path(os.getenv("STORAGE_DIR", "data/storage")))
    job = Job(id=uuid4(), status=JobStatus.QUEUED, input_ref="jobs/demo/input.json")
    storage.put(job.input_ref, b'{"demo": true}')
    JobRepository().save(job)
    print(job.id)


if __name__ == "__main__":
    main()
