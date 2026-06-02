"""Property test: across every problem size, the solver NEVER violates a hard
constraint (verified by the independent checker, not by CP-SAT itself).
"""
from __future__ import annotations

import pytest

from scheduler.checker import violations
from scheduler.model import Scheduler
from scheduler import scenarios


@pytest.mark.parametrize("n", [8, 12, 24, 40])
def test_no_hard_constraint_ever_violated(n):
    pool, mtgs = scenarios.scaled(n)
    s = Scheduler(pool, mtgs)
    r = s.solve(max_seconds=10)
    assert r.status in ("OPTIMAL", "FEASIBLE")
    assert violations(s, r) == []          # the invariant: 0 violations, every size


def test_busy_block_is_respected():
    # C is busy 15:00-16:00 UTC on day 0 (slots 30-31); no meeting may overlap it.
    ppl, mtgs = scenarios.feasible()
    s = Scheduler(ppl, mtgs)
    r = s.solve()
    for mid, (a, b) in r.schedule.items():
        people = next(m.participants for m in mtgs if m.mid == mid)
        if "C" in people:
            assert not (a < 32 and b > 30)  # no overlap with [30,32)
