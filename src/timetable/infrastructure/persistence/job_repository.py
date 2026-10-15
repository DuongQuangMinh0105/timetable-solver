from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from timetable.domain.entities.job import Job, JobStatus
from timetable.domain.ports.job_repository import JobRepositoryPort
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.models import JobModel


class JobRepository(JobRepositoryPort):
    """PostgreSQL implementation of the job repository."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionFactory,
    ) -> None:
        self._session_factory = session_factory

    def save(self, job: Job) -> None:
        """Persist a new job."""
        with self._session_factory() as session:
            session.add(self._to_model(job))
            session.commit()

    def get_by_id(self, job_id: UUID) -> Job | None:
        """Retrieve a job by its ID."""
        with self._session_factory() as session:
            statement = select(JobModel).where(JobModel.id == job_id)
            model = session.scalar(statement)

            if model is None:
                return None

            return self._to_entity(model)

    def update(self, job: Job) -> None:
        """Update an existing job."""
        with self._session_factory() as session:
            model = session.get(JobModel, job.id)

            if model is None:
                raise LookupError(f"Job {job.id} does not exist.")

            model.status = job.status.value
            model.input_ref = job.input_ref
            model.result_ref = job.result_ref
            model.error_message = job.error_message
            session.commit()

    @staticmethod
    def _to_model(job: Job) -> JobModel:
        """Convert a domain entity to an ORM model."""
        return JobModel(
            id=job.id,
            status=job.status.value,
            input_ref=job.input_ref,
            result_ref=job.result_ref,
            error_message=job.error_message,
        )

    @staticmethod
    def _to_entity(model: JobModel) -> Job:
        """Convert an ORM model to a domain entity."""
        return Job(
            id=model.id,
            status=JobStatus(model.status),
            input_ref=model.input_ref,
            result_ref=model.result_ref,
            error_message=model.error_message,
        )
