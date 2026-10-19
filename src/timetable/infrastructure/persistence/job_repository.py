from uuid import UUID

from sqlalchemy import select, update
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

    def claim_queued_job(self, job_id: UUID) -> Job | None:
        """Atomically change a queued job to running."""
        with self._session_factory() as session:
            statement = (
                update(JobModel)
                .where(
                    JobModel.id == job_id,
                    JobModel.status == JobStatus.QUEUED.value,
                )
                .values(
                    status=JobStatus.RUNNING.value,
                    error_message=None,
                )
                .returning(JobModel)
            )
            model = session.scalars(statement).one_or_none()
            session.commit()

            if model is None:
                return None

            return self._to_entity(model)

    def list_queued_jobs(
        self,
        limit: int = 100,
        after_id: UUID | None = None,
    ) -> list[Job]:
        """Return a bounded page of queued jobs after the given UUID."""
        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        with self._session_factory() as session:
            statement = select(JobModel).where(JobModel.status == JobStatus.QUEUED.value)

            if after_id is not None:
                statement = statement.where(JobModel.id > after_id)

            statement = statement.order_by(JobModel.id).limit(limit)
            models = session.scalars(statement).all()

            return [self._to_entity(model) for model in models]

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
