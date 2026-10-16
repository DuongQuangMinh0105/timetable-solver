from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import delete

from timetable.application.ports.storage import StoragePort
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.models import BlobModel
from timetable.infrastructure.storage.factory import create_storage
from timetable.infrastructure.storage.postgres import PostgresStorage


@pytest.fixture
def prefix() -> Iterator[str]:
    """Mỗi test dùng một tiền tố riêng và dọn sạch sau khi chạy."""
    value = f"test-{uuid4()}"
    yield value
    with SessionFactory() as session:
        session.execute(delete(BlobModel).where(BlobModel.key.like(f"{value}/%")))
        session.commit()


def _storage() -> StoragePort:
    return PostgresStorage()


def test_put_then_get(prefix: str) -> None:
    storage = _storage()
    storage.put(f"{prefix}/jobs/1/input.json", b'{"a": 1}')
    assert storage.get(f"{prefix}/jobs/1/input.json") == b'{"a": 1}'


def test_put_overwrites_existing_key(prefix: str) -> None:
    storage = _storage()
    storage.put(f"{prefix}/x.bin", b"old")
    storage.put(f"{prefix}/x.bin", b"new")
    assert storage.get(f"{prefix}/x.bin") == b"new"


def test_binary_data_round_trips(prefix: str) -> None:
    payload = bytes(range(256)) * 4096  # 1 MiB, đủ mọi giá trị byte
    storage = _storage()
    storage.put(f"{prefix}/blob.bin", payload)
    assert storage.get(f"{prefix}/blob.bin") == payload


def test_exists(prefix: str) -> None:
    storage = _storage()
    assert not storage.exists(f"{prefix}/x.bin")
    storage.put(f"{prefix}/x.bin", b"1")
    assert storage.exists(f"{prefix}/x.bin")


def test_delete(prefix: str) -> None:
    storage = _storage()
    storage.put(f"{prefix}/x.bin", b"1")
    storage.delete(f"{prefix}/x.bin")
    assert not storage.exists(f"{prefix}/x.bin")


def test_delete_missing_is_ok(prefix: str) -> None:
    _storage().delete(f"{prefix}/missing.bin")


def test_get_missing_raises(prefix: str) -> None:
    with pytest.raises(FileNotFoundError):
        _storage().get(f"{prefix}/missing.bin")


@pytest.mark.parametrize("key", ["../escape.txt", "a/../b", "/abs.txt", ""])
def test_invalid_keys_are_rejected(key: str) -> None:
    with pytest.raises(ValueError):
        _storage().put(key, b"x")


def test_factory_builds_postgres_backend(monkeypatch: pytest.MonkeyPatch, prefix: str) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "postgres")

    storage = create_storage()

    assert isinstance(storage, PostgresStorage)
    storage.put(f"{prefix}/f.txt", b"ok")
    assert storage.get(f"{prefix}/f.txt") == b"ok"
