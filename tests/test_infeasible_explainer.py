"""When a set of calendars is oversubscribed, the solver must EXPLAIN the
infeasibility — return a minimal conflicting subset — and removing one member
of that core must make the problem feasible again.
"""
from __future__ import annotations

from scheduler.checker import violations
from scheduler.model import Scheduler
from scheduler import scenarios


def test_oversubscribed_is_infeasible_with_a_core():
    ppl, mtgs = scenarios.oversubscribed()
    s = Scheduler(ppl, mtgs)
    core = s.explain_infeasible([m.mid for m in mtgs])
    assert len(core) >= 2                       # a real conflict, not an empty answer
    assert set(core) <= {m.mid for m in mtgs}


def test_relaxing_the_core_restores_feasibility():
    ppl, mtgs = scenarios.oversubscribed()
    s = Scheduler(ppl, mtgs)
    core = s.explain_infeasible([m.mid for m in mtgs])
    assert core
    # Make every meeting optional, then forbid the first core meeting; the rest
    # must now schedule with no violations.
    kept = [m for m in mtgs if m.mid != core[0]]
    relaxed = [type(m)(m.mid, m.participants, m.duration_slots, m.priority, True)
               for m in kept]
    s2 = Scheduler(ppl, relaxed)
    r2 = s2.solve()
    assert r2.status in ("OPTIMAL", "FEASIBLE")
    assert violations(s2, r2) == []


def test_feasible_set_has_empty_core():
    ppl, mtgs = scenarios.feasible()
    s = Scheduler(ppl, mtgs)
    # only the required all-hands; these DO fit, so no conflict core
    req = [m.mid for m in mtgs if m.required]
    assert s.explain_infeasible(req) == []
