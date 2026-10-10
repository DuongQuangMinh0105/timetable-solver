from timetable.application.use_cases.diagnose_infeasibility import DiagnoseInfeasibility
from timetable.domain.services.precheck import OfferingInfo


class FakeDiagnoser:
    def __init__(self, groups):
        self._groups = groups
        self.called = False

    def conflicting_groups(self):
        self.called = True
        return self._groups


OK = [OfferingInfo("A", "regular", 25, 2, "T1")]


def test_precheck_issue_skips_solver():
    fake = FakeDiagnoser(["room_clash"])
    bad = [OfferingInfo("A", "regular", 40, 2, "T1")]
    report = DiagnoseInfeasibility(fake).execute(bad, regular_room_count=5)
    assert report.source == "precheck"
    assert not fake.called


def test_solver_groups_are_translated():
    report = DiagnoseInfeasibility(FakeDiagnoser(["mba_room"])).execute(OK, 5)
    assert report.source == "solver"
    assert "G316" in report.issues[0].message


def test_unknown_group_has_generic_message():
    report = DiagnoseInfeasibility(FakeDiagnoser(["xyz"])).execute(OK, 5)
    assert "xyz" in report.issues[0].message


def test_no_conflict_found():
    report = DiagnoseInfeasibility(FakeDiagnoser([])).execute(OK, 5)
    assert not report.has_issues
