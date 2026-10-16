from sqlalchemy import LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from timetable.infrastructure.persistence.base import Base


class BlobModel(Base):
    """File nhỏ (input và kết quả của job) lưu ngay trong Postgres, dùng khi không có ổ đĩa bền."""

    __tablename__ = "blobs"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
