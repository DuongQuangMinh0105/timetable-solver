import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from timetable.infrastructure.generator import (
    INFEASIBLE_PROFILES,
    MAX_CLASS_SIZE,
    MIN_CLASS_SIZE,
    PROFILES,
    ROOM_CAPACITY,
    generate_profile,
    generate_v1,
)

# File test nằm ở: tests/unit/infrastructure/test_generator.py
# parents[0] = infrastructure, parents[1] = unit, parents[2] = tests, parents[3] = thư mục gốc dự án
SAMPLE_PATH = Path(__file__).resolve().parents[2] / "docs" / "schema" / "input.sample.json"

# Bộ dữ liệu theo docs/test-data-spec.md: 10 lớp, 8 giáo viên, 2 lớp MBA, 2 lớp Design.
SPEC_PARAMS: dict[str, int] = {
    "num_classes": 10,
    "num_teachers": 8,
    "num_mba_classes": 2,
    "num_art_classes": 2,
}


def _load_sample() -> dict[str, Any]:
    with SAMPLE_PATH.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


def _without_seed_fields(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k not in {"solver", "_comment"}}


def _can_host(room: dict[str, Any], required_room_type: str) -> bool:
    return required_room_type == room["room_type"] or required_room_type in room["also_supports"]


# --- Seed cố định -----------------------------------------------------------


def test_same_seed_gives_identical_output() -> None:
    first = generate_v1(seed=7, **SPEC_PARAMS)
    second = generate_v1(seed=7, **SPEC_PARAMS)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_different_seed_changes_the_data() -> None:
    first = generate_v1(seed=1, **SPEC_PARAMS)
    second = generate_v1(seed=2, **SPEC_PARAMS)
    assert _without_seed_fields(first) != _without_seed_fields(second)


def test_seed_is_recorded_for_the_solver() -> None:
    assert generate_v1(seed=42)["solver"]["random_seed"] == 42


# --- Đúng schema ------------------------------------------------------------


def test_output_is_json_serializable() -> None:
    data = generate_v1(**SPEC_PARAMS)
    assert json.loads(json.dumps(data)) == data


def test_output_has_the_same_shape_as_the_sample() -> None:
    sample = _load_sample()
    data = generate_v1()

    assert set(data) == set(sample)
    assert data["schema_version"] == sample["schema_version"]
    assert data["grid"] == sample["grid"]
    assert data["constraints"] == sample["constraints"]
    for key, sample_value in sample.items():
        if isinstance(sample_value, list):
            assert set(data[key][0]) == set(sample_value[0]), key
        elif isinstance(sample_value, dict):
            assert set(data[key]) == set(sample_value), key


def test_default_parameters_match_the_sample_scale() -> None:
    sample = _load_sample()
    data = generate_v1()
    assert len(data["rooms"]) == len(sample["rooms"])
    assert [r["id"] for r in data["rooms"]] == [r["id"] for r in sample["rooms"]]
    assert len(data["class_groups"]) == len(sample["class_groups"])
    assert len(data["courses"]) == len(sample["courses"])
    assert len(data["lesson_units"]) == len(sample["lesson_units"])


# --- Tham số ----------------------------------------------------------------


def test_parameters_are_applied() -> None:
    data = generate_v1(**SPEC_PARAMS)
    kinds = Counter(c["kind"] for c in data["class_groups"])

    assert len(data["teachers"]) == 8
    assert len(data["class_groups"]) == 10
    assert kinds == {"regular": 6, "mba": 2, "art": 2}


@pytest.mark.parametrize(
    "params",
    [
        {"num_classes": 0},
        {"num_teachers": 0},
        {"num_mba_classes": -1},
        {"num_art_classes": -1},
        {"num_classes": 2, "num_mba_classes": 2, "num_art_classes": 1},
    ],
)
def test_invalid_parameters_raise(params: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        generate_v1(**params)


# --- Tính nhất quán của dữ liệu sinh ra -------------------------------------


def test_references_are_consistent() -> None:
    data = generate_v1(**SPEC_PARAMS)
    class_ids = {c["id"] for c in data["class_groups"]}
    teacher_ids = {t["id"] for t in data["teachers"]}
    course_ids = {c["id"] for c in data["courses"]}

    assert len(course_ids) == len(data["courses"])
    assert all(
        c["class_id"] in class_ids and c["teacher_id"] in teacher_ids for c in data["courses"]
    )
    assert all(u["course_id"] in course_ids for u in data["lesson_units"])
    assert len({u["id"] for u in data["lesson_units"]}) == len(data["lesson_units"])


def test_units_match_periods_per_week() -> None:
    data = generate_v1(**SPEC_PARAMS)
    units_per_course = Counter(u["course_id"] for u in data["lesson_units"])
    for course in data["courses"]:
        assert units_per_course[course["id"]] == course["periods_per_week"]


def test_class_sizes_fit_the_rooms() -> None:
    data = generate_v1(**SPEC_PARAMS)
    sizes = [c["size"] for c in data["class_groups"]]
    assert all(MIN_CLASS_SIZE <= s <= MAX_CLASS_SIZE for s in sizes)
    assert MAX_CLASS_SIZE <= ROOM_CAPACITY


def test_every_unit_has_a_valid_room() -> None:
    data = generate_v1(**SPEC_PARAMS)
    size = {c["id"]: c["size"] for c in data["class_groups"]}
    for unit in data["lesson_units"]:
        needed = size[unit["class_id"]]
        assert any(
            _can_host(room, unit["required_room_type"]) and room["capacity"] >= needed
            for room in data["rooms"]
        ), unit["id"]


def test_special_classes_use_special_rooms() -> None:
    data = generate_v1(**SPEC_PARAMS)
    kind = {c["id"]: c["kind"] for c in data["class_groups"]}
    units = data["lesson_units"]
    mba_types = {u["required_room_type"] for u in units if kind[u["class_id"]] == "mba"}
    art_types = {u["required_room_type"] for u in units if kind[u["class_id"]] == "art"}

    assert mba_types == {"mba"}
    assert "art" in art_types


def test_no_teacher_is_assigned_more_than_a_week_allows() -> None:
    data = generate_v1(**SPEC_PARAMS)
    grid = data["grid"]
    capacity = grid["days"] * len(grid["allowed_periods"])
    load = Counter(u["teacher_id"] for u in data["lesson_units"])
    assert max(load.values()) <= capacity


# --- Bộ tham số đặt tên sẵn (kích thước và dữ liệu "khó") ---------------------


def _periods_needing(data: dict[str, Any], room_type: str) -> int:
    return sum(
        c["periods_per_week"] for c in data["courses"] if c["required_room_type"] == room_type
    )


def _week_capacity(data: dict[str, Any]) -> int:
    grid = data["grid"]
    return grid["days"] * len(grid["allowed_periods"])


def test_profile_matches_its_parameters() -> None:
    data = generate_profile("spec")
    assert data == generate_v1(**PROFILES["spec"])


def test_unknown_profile_raises() -> None:
    with pytest.raises(ValueError):
        generate_profile("does-not-exist")


def test_profiles_are_deterministic() -> None:
    for name in PROFILES:
        assert generate_profile(name, seed=3) == generate_profile(name, seed=3)


def test_many_mba_profile_uses_most_of_g316_without_exceeding_it() -> None:
    data = generate_profile("many_mba")
    demand = _periods_needing(data, "mba")
    assert 0.8 * _week_capacity(data) <= demand <= _week_capacity(data)


def test_many_art_profile_uses_most_of_g313_without_exceeding_it() -> None:
    data = generate_profile("many_art")
    demand = _periods_needing(data, "art")
    assert 0.8 * _week_capacity(data) <= demand <= _week_capacity(data)


def test_tight_teachers_profile_has_fewer_teachers_than_spec() -> None:
    assert len(generate_profile("tight_teachers")["teachers"]) < len(
        generate_profile("spec")["teachers"]
    )


def test_overload_mba_profile_exceeds_g316_capacity() -> None:
    data = generate_profile("overload_mba")
    assert "overload_mba" in INFEASIBLE_PROFILES
    assert _periods_needing(data, "mba") > _week_capacity(data)


def test_only_overload_profiles_are_marked_infeasible() -> None:
    for name in PROFILES:
        data = generate_profile(name)
        too_much = max(
            _periods_needing(data, "mba"), _periods_needing(data, "art")
        ) > _week_capacity(data)
        assert too_much == (name in INFEASIBLE_PROFILES), name
