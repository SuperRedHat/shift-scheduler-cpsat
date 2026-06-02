"""The feasible scenario must produce an optimal schedule that books every
required meeting, including across the DST boundary on day 1.
"""
from __future__ import annotations

from scheduler.checker import violations
from scheduler.model import Scheduler
from scheduler import scenarios


def test_feasible_books_all_required():
    ppl, mtgs = scenarios.feasible()
    s = Scheduler(ppl, mtgs)
    r = s.solve()
    assert r.status == "OPTIMAL"
    for m in mtgs:
        if m.required:
            assert m.mid in r.scheduled
    assert violations(s, r) == []


def test_dst_aware_placement():
    # all-hands meetings on day 1 must sit in the shared window AFTER C's
    # offset shifts -5 -> -4 (a naive fixed-offset model would misplace them).
    ppl, mtgs = scenarios.feasible()
    r = Scheduler(ppl, mtgs).solve()
    day1 = [(a, b) for mid, (a, b) in r.schedule.items() if "all-hands" in mid and a >= 48]
    assert day1, "expected at least one all-hands on day 1"
    for a, b in day1:
        # C (UTC-4 on day1) working 09:00-17:00 local == 13:00-21:00 UTC == slots 74..89
        assert a >= 74 and b <= 90
