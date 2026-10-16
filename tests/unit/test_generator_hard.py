from collections import Counter

from timetable.infrastructure.generator import HARD_PARAMS, generate_hard, generate_v1


def test_hard_same_seed_gives_identical_output() -> None:
    assert generate_hard(seed=3) == generate_hard(seed=3)


def test_hard_applies_params() -> None:
    data = generate_hard(seed=1)
    kinds = Counter(c["kind"] for c in data["class_groups"])
    assert len(data["class_groups"]) == HARD_PARAMS["num_classes"]
    assert len(data["teachers"]) == HARD_PARAMS["num_teachers"]
    assert kinds["mba"] == HARD_PARAMS["num_mba_classes"]
    assert kinds["art"] == HARD_PARAMS["num_art_classes"]


def test_hard_has_more_special_classes_than_default() -> None:
    hard = Counter(c["kind"] for c in generate_hard()["class_groups"])
    default = Counter(c["kind"] for c in generate_v1()["class_groups"])
    assert hard["mba"] > default["mba"]
    assert hard["art"] > default["art"]


def test_hard_overrides_are_applied() -> None:
    data = generate_hard(num_classes=12, num_mba_classes=3, num_art_classes=3)
    assert len(data["class_groups"]) == 12


def test_hard_special_room_load_fits_one_week() -> None:
    data = generate_hard()
    grid = data["grid"]
    week = grid["days"] * len(grid["allowed_periods"])
    load = Counter(u["required_room_type"] for u in data["lesson_units"])
    assert load["mba"] <= week
    assert load["art"] <= week
