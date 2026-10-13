from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete

from timetable.application.use_cases.run_job import RunJob
from timetable.domain.entities.job import Job, JobStatus
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.persistence.models import JobModel
from timetable.infrastructure.solver.fake import fake_handler
from timetable.infrastructure.storage.local import LocalStorage


def test_run_job_end_to_end_with_postgres(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    repository = JobRepository()
    job = Job(id=uuid4(), status=JobStatus.QUEUED, input_ref="jobs/in/input.json")
    storage.put(job.input_ref, b"{}")
    repository.save(job)

    try:
        RunJob(repository, storage, fake_handler).execute(job.id)

        saved = repository.get_by_id(job.id)
        assert saved is not None
        assert saved.status == JobStatus.COMPLETED
        assert saved.result_ref is not None
        assert storage.exists(saved.result_ref)
    finally:
        with SessionFactory() as session:
            session.execute(delete(JobModel).where(JobModel.id == job.id))
            session.commit()
