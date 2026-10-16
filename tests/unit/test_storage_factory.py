from pathlib import Path

import pytest

from timetable.infrastructure.storage.factory import create_storage
from timetable.infrastructure.storage.local import LocalStorage


def test_default_backend_is_local(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))

    storage = create_storage()

    assert isinstance(storage, LocalStorage)
    storage.put("a.txt", b"x")
    assert (tmp_path / "a.txt").read_bytes() == b"x"


def test_backend_name_is_case_insensitive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", " LOCAL ")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))

    assert isinstance(create_storage(), LocalStorage)


def test_unknown_backend_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "s3")

    with pytest.raises(ValueError, match="STORAGE_BACKEND"):
        create_storage()
