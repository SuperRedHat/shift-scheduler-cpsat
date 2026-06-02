"""An INDEPENDENT verifier of a solution — deliberately not using CP-SAT, so a
bug in the model can't hide a bug in its own check. The property tests assert
this returns no violations: no hard constraint is ever broken.
"""
from __future__ import annotations

from typing import List

from .model import Scheduler, SolveResult, working_slots


def violations(sched: Scheduler, res: SolveResult) -> List[str]:
    out: List[str] = []
    meetings = {m.mid: m for m in sched.meetings}
    work = {pid: working_slots(p, sched.days) for pid, p in sched.participants.items()}
    busy = {pid: set(s for a, b in p.busy for s in range(a, b))
            for pid, p in sched.participants.items()}

    # per-participant occupied slots (with each meeting's actual span)
    occ = {pid: [] for pid in sched.participants}
    for mid in res.scheduled:
        m = meetings[mid]
        s, e = res.schedule[mid]
        span = set(range(s, e))
        for pid in m.participants:
            # working hours
            if not span <= work[pid]:
                out.append(f"{mid}: {pid} outside working hours {sorted(span)}")
            # busy avoidance
            if span & busy[pid]:
                out.append(f"{mid}: {pid} overlaps a busy block")
            occ[pid].append((s, e, mid))

    # no double-booking and buffer respected, per participant
    for pid, items in occ.items():
        items.sort()
        for (s1, e1, m1), (s2, e2, m2) in zip(items, items[1:]):
            if s2 < e1:
                out.append(f"{pid}: {m1} and {m2} overlap")
            elif s2 - e1 < sched.buffer:
                out.append(f"{pid}: {m1}->{m2} violates buffer ({s2 - e1} < {sched.buffer})")

    # required meetings must be scheduled
    for m in sched.meetings:
        if m.required and m.mid not in res.scheduled:
            out.append(f"{m.mid}: required but not scheduled")
    return out
