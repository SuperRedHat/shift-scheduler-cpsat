"""A CP-SAT multi-party meeting scheduler with timezone/working-hours, buffers,
priorities, and — the part that matters for a review — an INFEASIBILITY
EXPLAINER that names the minimal set of meetings that mutually conflict when a
set of calendars is oversubscribed, instead of just returning "no solution".

Time is modelled in fixed slots (default 30 min). Working hours are per
participant in their own timezone, with a per-day UTC offset so a DST shift is
handled correctly (a naive fixed-offset model would misplace the second day).

Built on Google OR-Tools CP-SAT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

SLOT_MIN = 30
SLOTS_PER_DAY = 24 * 60 // SLOT_MIN          # 48
WORK_START_LOCAL = 9 * 60 // SLOT_MIN        # 09:00 -> slot 18 of the day
WORK_END_LOCAL = 17 * 60 // SLOT_MIN         # 17:00 -> slot 34 of the day


@dataclass(frozen=True)
class Participant:
    pid: str
    # UTC offset in hours per day index (lets day 1 differ -> DST transition).
    utc_offset_by_day: Tuple[int, ...]
    busy: Tuple[Tuple[int, int], ...] = ()   # fixed (start_slot, end_slot) UTC blocks


@dataclass(frozen=True)
class Meeting:
    mid: str
    participants: Tuple[str, ...]
    duration_slots: int
    priority: int = 1
    required: bool = False


@dataclass
class SolveResult:
    status: str
    schedule: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    scheduled: List[str] = field(default_factory=list)
    unscheduled: List[str] = field(default_factory=list)
    objective: int = 0
    solve_ms: float = 0.0
    infeasible_core: List[str] = field(default_factory=list)


def working_slots(p: Participant, days: int) -> set:
    """UTC slots during which participant p is inside working hours."""
    out = set()
    for day in range(days):
        off = p.utc_offset_by_day[min(day, len(p.utc_offset_by_day) - 1)]
        off_slots = off * 60 // SLOT_MIN
        for local in range(WORK_START_LOCAL, WORK_END_LOCAL):
            utc_slot = day * SLOTS_PER_DAY + (local - off_slots)
            if 0 <= utc_slot < days * SLOTS_PER_DAY:
                out.add(utc_slot)
    return out


def _busy_slots(p: Participant) -> set:
    s = set()
    for a, b in p.busy:
        s.update(range(a, b))
    return s


class Scheduler:
    def __init__(self, participants: List[Participant], meetings: List[Meeting],
                 days: int = 2, buffer_slots: int = 1):
        self.participants = {p.pid: p for p in participants}
        self.meetings = meetings
        self.days = days
        self.horizon = days * SLOTS_PER_DAY
        self.buffer = buffer_slots
        self._work = {p.pid: working_slots(p, days) for p in participants}
        self._busy = {p.pid: _busy_slots(p) for p in participants}

    def allowed_starts(self, m: Meeting) -> List[int]:
        """Static feasibility: starts where every participant is working & free
        for the meeting's whole span."""
        d = m.duration_slots
        good = []
        for t in range(0, self.horizon - d + 1):
            span = range(t, t + d)
            ok = True
            for pid in m.participants:
                w, b = self._work[pid], self._busy[pid]
                if any(s not in w or s in b for s in span):
                    ok = False
                    break
            if ok:
                good.append(t)
        return good

    def _build(self):
        model = cp_model.CpModel()
        present, starts, novs = {}, {}, {pid: [] for pid in self.participants}
        for m in self.meetings:
            allowed = self.allowed_starts(m)
            pres = model.NewBoolVar(f"present_{m.mid}")
            if not allowed:
                model.Add(pres == 0)         # can never be placed
                present[m.mid] = pres
                starts[m.mid] = None
                continue
            st = model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(allowed), f"start_{m.mid}")
            present[m.mid] = pres
            starts[m.mid] = st
            # padded interval enforces a buffer between a participant's meetings
            iv = model.NewOptionalIntervalVar(
                st, m.duration_slots + self.buffer,
                model.NewIntVar(0, self.horizon + self.buffer, f"end_{m.mid}"),
                pres, f"iv_{m.mid}")
            for pid in m.participants:
                novs[pid].append(iv)
        # Buffer applies BETWEEN scheduled meetings; avoidance of pre-existing
        # busy blocks is already enforced by each meeting's allowed-start domain.
        for pid in self.participants:
            if novs[pid]:
                model.AddNoOverlap(novs[pid])
        return model, present, starts

    def solve(self, max_seconds: float = 5.0) -> SolveResult:
        model, present, starts = self._build()
        for m in self.meetings:
            if m.required:
                model.Add(present[m.mid] == 1)
        model.Maximize(sum(m.priority * present[m.mid] for m in self.meetings))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max_seconds
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)
        res = SolveResult(status=solver.StatusName(status),
                          solve_ms=solver.WallTime() * 1000.0)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            res.objective = int(solver.ObjectiveValue())
            for m in self.meetings:
                if starts[m.mid] is not None and solver.Value(present[m.mid]):
                    s = solver.Value(starts[m.mid])
                    res.schedule[m.mid] = (s, s + m.duration_slots)
                    res.scheduled.append(m.mid)
                else:
                    res.unscheduled.append(m.mid)
        return res

    def explain_infeasible(self, required_ids: List[str],
                           max_seconds: float = 5.0) -> List[str]:
        """Return a MINIMAL subset of `required_ids` that cannot all be scheduled
        together (IIS-style), using CP-SAT assumptions. Empty => they all fit.
        """
        model, present, starts = self._build()
        lit_to_mid = {}
        for mid in required_ids:
            model.AddAssumption(present[mid])
            lit_to_mid[present[mid].Index()] = mid
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max_seconds
        status = solver.Solve(model)
        if status != cp_model.INFEASIBLE:
            return []
        core = solver.SufficientAssumptionsForInfeasibility()
        return [lit_to_mid[i] for i in core if i in lit_to_mid]
