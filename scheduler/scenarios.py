"""Deterministic scenarios: a feasible one, an oversubscribed one (for the
infeasibility explainer), and a scaled one for benchmarking.

Three participants in three timezones — and participant C crosses a DST
boundary between day 0 and day 1 (offset -5 -> -4) — so the only time all three
are simultaneously in working hours is a narrow shared window. That scarcity is
what makes multi-party scheduling hard and what the solver has to respect.
"""
from __future__ import annotations

from typing import List, Tuple

from .model import Meeting, Participant

# A: UTC, B: UTC+1, C: US-East with a spring-forward DST shift on day 1.
def people() -> List[Participant]:
    return [
        Participant("A", (0, 0)),
        Participant("B", (1, 1)),
        Participant("C", (-5, -4), busy=((30, 32),)),   # C busy 15:00-16:00 UTC day0
    ]


def feasible() -> Tuple[List[Participant], List[Meeting]]:
    m = [
        Meeting("all-hands-1", ("A", "B", "C"), 2, priority=5, required=True),
        Meeting("all-hands-2", ("A", "B", "C"), 2, priority=5, required=True),
        Meeting("all-hands-3", ("A", "B", "C"), 2, priority=5, required=True),
        Meeting("ab-sync", ("A", "B"), 2, priority=3),
        Meeting("ac-1on1", ("A", "C"), 2, priority=2),
    ]
    return people(), m


def oversubscribed() -> Tuple[List[Participant], List[Meeting]]:
    # The shared all-three window fits ~3 meetings; require 4 -> infeasible.
    m = [Meeting(f"all-hands-{i}", ("A", "B", "C"), 2, priority=5, required=True)
         for i in range(1, 5)]
    return people(), m


def scaled(n: int) -> Tuple[List[Participant], List[Meeting]]:
    """n two-person meetings over a pool that grows with n (~4 meetings/person),
    so the benchmark measures solve time, not a deliberate over-subscription."""
    size = max(6, n // 2)
    pool = [Participant(f"P{i:02d}", (0, 0)) for i in range(size)]
    meetings = []
    for i in range(n):
        a = i % size
        b = (i + 1 + i // size) % size
        if a == b:
            b = (b + 1) % size
        meetings.append(
            Meeting(f"m{i:03d}", (f"P{a:02d}", f"P{b:02d}"), 2, priority=1 + (i % 3)))
    return pool, meetings
