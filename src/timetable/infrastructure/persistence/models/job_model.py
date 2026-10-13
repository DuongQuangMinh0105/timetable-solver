
from uuid import UUID

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from timetable.infrastructure.persistence.base import Base


class JobModel(Base):
    """SQLAlchemy model for persisted solver jobs."""

    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    input_ref: Mapped[str] = mapped_column(Text, nullable=False)
    result_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    
#Đây là model database, 
# không phải domain entity.
#  Chúng ta dùng String cho status để lưu các giá trị
#  như queued, running, completed, failed. result_ref cho phép NULL
#  vì job chưa hoàn thành có thể chưa có kết quả.