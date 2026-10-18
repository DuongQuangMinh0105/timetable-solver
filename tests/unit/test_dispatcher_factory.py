import pytest

from timetable.infrastructure.dispatch.factory import create_dispatcher
from timetable.infrastructure.dispatch.local import LocalJobDispatcher
from timetable.infrastructure.dispatch.redis import RedisJobDispatcher


def test_default_dispatcher_is_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JOB_DISPATCHER", raising=False)

    assert isinstance(create_dispatcher(), RedisJobDispatcher)


def test_local_dispatcher_can_be_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_DISPATCHER", "local")

    assert isinstance(create_dispatcher(), LocalJobDispatcher)


def test_dispatcher_name_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_DISPATCHER", " LOCAL ")

    assert isinstance(create_dispatcher(), LocalJobDispatcher)


def test_unknown_dispatcher_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_DISPATCHER", "kafka")

    with pytest.raises(ValueError, match="JOB_DISPATCHER"):
        create_dispatcher()
