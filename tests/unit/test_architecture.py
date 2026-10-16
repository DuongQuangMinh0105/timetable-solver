"""Kiểm tra quy tắc phụ thuộc giữa các tầng (Clean Architecture) bằng cách phân tích import.

Quy tắc (xem docs/architecture.md):
- domain chỉ import domain;
- application import domain và application;
- infrastructure import domain, application và infrastructure;
- interfaces import mọi tầng (đây là nơi lắp ráp);
- domain không dùng thư viện framework; application không dùng framework trừ `pydantic`.

Import nằm trong hàm hoặc sau `TYPE_CHECKING` cũng được tính, và import tương đối được quy đổi ra
tên đầy đủ trước khi kiểm tra.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
ROOT_PACKAGE = "timetable"
LAYERS = ("domain", "application", "infrastructure", "interfaces")

ALLOWED_LAYERS: dict[str, set[str]] = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "infrastructure": {"domain", "application", "infrastructure"},
    "interfaces": set(LAYERS),
}

FRAMEWORKS = {
    "alembic",
    "dotenv",
    "fastapi",
    "ortools",
    "openpyxl",
    "psycopg",
    "pydantic",
    "sqlalchemy",
    "starlette",
    "streamlit",
    "uvicorn",
}
FORBIDDEN_FRAMEWORKS: dict[str, set[str]] = {
    "domain": FRAMEWORKS,
    "application": FRAMEWORKS - {"pydantic"},
}


def imported_modules(source: str, module: str) -> list[tuple[int, str]]:
    """Mọi module được import (kể cả import lười và import tương đối) kèm số dòng.

    `module` là tên đầy đủ của file đang xét, ví dụ `timetable.domain.entities.room`.
    """
    package = module.rsplit(".", 1)[0]
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)]
                name = ".".join([*base, *([node.module] if node.module else [])])
            else:
                name = node.module or ""
            found.append((node.lineno, name))
    return found


def layer_of(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == ROOT_PACKAGE and parts[1] in LAYERS:
        return parts[1]
    return None


def violations_in(source: str, module: str) -> list[str]:
    """Các vi phạm quy tắc phụ thuộc trong một file nguồn."""
    layer = layer_of(module)
    if layer is None:
        return []
    problems: list[str] = []
    for lineno, imported in imported_modules(source, module):
        target = layer_of(imported)
        if target is not None and target not in ALLOWED_LAYERS[layer]:
            problems.append(
                f"{module}:{lineno}: tầng {layer} không được import tầng {target} ({imported})"
            )
        top = imported.split(".")[0]
        if top in FORBIDDEN_FRAMEWORKS.get(layer, set()):
            problems.append(f"{module}:{lineno}: tầng {layer} không được dùng thư viện {top}")
    return problems


def module_name(path: Path) -> str:
    relative = path.relative_to(SRC).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1] + ["__init__"]
    return ".".join(parts)


def test_every_layer_has_source_files() -> None:
    for layer in LAYERS:
        assert list((SRC / ROOT_PACKAGE / layer).rglob("*.py")), f"tầng {layer} không có file nào"


def test_project_respects_layer_dependencies() -> None:
    problems: list[str] = []
    for path in sorted((SRC / ROOT_PACKAGE).rglob("*.py")):
        problems.extend(violations_in(path.read_text(encoding="utf-8"), module_name(path)))
    assert not problems, "\n" + "\n".join(problems)


# --- Kiểm tra chính bộ kiểm tra (để không bị "đạt giả") -----------------------------------------


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("timetable.domain.a", "from timetable.infrastructure.solver import cpsat_solver"),
        ("timetable.domain.a", "import timetable.application.ports.solver"),
        ("timetable.domain.a", "def f():\n    from timetable.interfaces.api import main"),
        ("timetable.domain.sub.a", "from ...infrastructure import generator"),
        ("timetable.application.a", "from timetable.infrastructure.storage.local import X"),
        ("timetable.infrastructure.a", "from timetable.interfaces.api.main import app"),
        ("timetable.domain.a", "from ortools.sat.python import cp_model"),
        ("timetable.domain.a", "import pydantic"),
        ("timetable.application.a", "from sqlalchemy import select"),
        ("timetable.application.a", "from fastapi import FastAPI"),
    ],
)
def test_checker_flags_violations(module: str, source: str) -> None:
    assert violations_in(source, module)


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("timetable.domain.a", "from timetable.domain.entities import Room\nimport json"),
        ("timetable.domain.sub.a", "from ..entities import Room"),
        ("timetable.application.a", "from timetable.domain.entities import Problem"),
        ("timetable.application.a", "from pydantic import BaseModel"),
        ("timetable.infrastructure.a", "from timetable.application.ports.solver import SolverPort"),
        ("timetable.infrastructure.a", "from ortools.sat.python import cp_model"),
        ("timetable.interfaces.a", "from timetable.infrastructure.storage.local import X"),
        ("timetable.__init__", "from timetable.interfaces.api import main"),
    ],
)
def test_checker_accepts_allowed_imports(module: str, source: str) -> None:
    assert violations_in(source, module) == []
