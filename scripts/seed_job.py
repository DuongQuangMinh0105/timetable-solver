"""Tạo một job mẫu: ghi input vào storage và lưu job (QUEUED) vào Postgres.

Dùng: python scripts/seed_job.py [đường_dẫn_file_input.json]
Mặc định dùng docs/schema/input.sample.json.
"""

import sys
from pathlib import Path
from uuid import uuid4

from timetable.domain.entities.job import Job, JobStatus
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.storage.factory import create_storage

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "docs" / "schema" / "input.sample.json"


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    storage = create_storage()
    job = Job(id=uuid4(), status=JobStatus.QUEUED, input_ref=f"jobs/demo/{input_path.name}")
    storage.put(job.input_ref, input_path.read_bytes())
    JobRepository().save(job)
    print(job.id)


if __name__ == "__main__":
    main()
