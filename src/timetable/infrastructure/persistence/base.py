from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""


# Base chứa metadata của tất cả bảng ORM.
# Alembic sẽ dùng metadata này để phát hiện sự khác biệt giữa model và schema database.
