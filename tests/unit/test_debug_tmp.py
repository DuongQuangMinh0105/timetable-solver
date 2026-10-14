import inspect

import solver_helpers as s
from timetable.domain import entities


def test_dbg() -> None:
    print("\n===== solver_helpers.unit =====")
    print(inspect.getsource(s.unit))
    print("===== solver_helpers.make_problem =====")
    print(inspect.getsource(s.make_problem))
    print("===== entities =====")
    print(inspect.getsource(entities))
