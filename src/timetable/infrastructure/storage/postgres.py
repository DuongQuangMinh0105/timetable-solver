from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.models import BlobModel


class PostgresStorage:
    """Hiện thực StoragePort: lưu file trong bảng `blobs` của Postgres.

    Dùng khi nơi chạy không có ổ đĩa bền (ví dụ Render miễn phí). Chỉ hợp với file nhỏ
    (JSON input và kết quả), vì dung lượng bị giới hạn bởi gói Postgres.
    """

    def __init__(self, session_factory: sessionmaker[Session] = SessionFactory) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _check(key: str) -> str:
        parts = key.split("/")
        if not key or key.startswith("/") or ".." in parts:
            raise ValueError(f"Invalid storage key: {key!r}")
        return key

    def put(self, key: str, data: bytes) -> None:
        self._check(key)
        statement = (
            insert(BlobModel)
            .values(key=key, data=data)
            .on_conflict_do_update(index_elements=[BlobModel.key], set_={"data": data})
        )
        with self._session_factory() as session:
            session.execute(statement)
            session.commit()

    def get(self, key: str) -> bytes:
        self._check(key)
        with self._session_factory() as session:
            data = session.scalar(select(BlobModel.data).where(BlobModel.key == key))
        if data is None:
            raise FileNotFoundError(key)
        return bytes(data)

    def exists(self, key: str) -> bool:
        self._check(key)
        with self._session_factory() as session:
            found = session.scalar(select(BlobModel.key).where(BlobModel.key == key))
        return found is not None

    def delete(self, key: str) -> None:
        self._check(key)
        with self._session_factory() as session:
            session.execute(delete(BlobModel).where(BlobModel.key == key))
            session.commit()
