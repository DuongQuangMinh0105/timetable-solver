from pathlib import Path

import pytest

from timetable.application.ports.storage import StoragePort
from timetable.infrastructure.storage.local import LocalStorage


def make_storage(tmp_path: Path) -> StoragePort:
    return LocalStorage(tmp_path)


def test_put_then_get(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    storage.put("jobs/1/input.json", b'{"a": 1}')
    assert storage.get("jobs/1/input.json") == b'{"a": 1}'


def test_exists(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    assert not storage.exists("x.bin")
    storage.put("x.bin", b"1")
    assert storage.exists("x.bin")


def test_delete(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    storage.put("x.bin", b"1")
    storage.delete("x.bin")
    assert not storage.exists("x.bin")


def test_delete_missing_is_ok(tmp_path: Path) -> None:
    make_storage(tmp_path).delete("missing.bin")


def test_get_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        make_storage(tmp_path).get("missing.bin")


def test_key_outside_root_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        make_storage(tmp_path).put("../escape.txt", b"x")
