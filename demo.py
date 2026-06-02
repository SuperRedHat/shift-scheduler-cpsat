#!/usr/bin/env python3
"""Schedule multi-party meetings across timezones with CP-SAT, prove no hard
constraint is violated, EXPLAIN an oversubscribed (infeasible) case instead of
just failing, and benchmark solve time vs size.

    python demo.py
"""
from __future__ import annotations

from scheduler.checker import violations
from scheduler.model import SLOT_MIN, SLOTS_PER_DAY, Scheduler
from scheduler import scenarios


def fmt(slot: int) -> str:
    day, sod = divmod(slot, SLOTS_PER_DAY)
    h, m = divmod(sod * SLOT_MIN, 60)
    return f"D{day} {h:02d}:{m:02d}"


def banner(t: str) -> None:
    print("\n" + "=" * 68 + f"\n  {t}\n" + "=" * 68)


def main() -> int:
    banner("THE HARD PART")
    print(
        "Coordinating meetings across calendars and timezones is NP-hard: working\n"
        "hours, buffers, priorities and no-double-booking interact, and the shared\n"
        "window is narrow. A greedy loop produces invalid or infeasible schedules;\n"
        "a CP-SAT model produces an optimal one — and, when it can't, says WHY."
    )

    banner("FEASIBLE: optimal schedule (3 timezones, C crosses a DST boundary)")
    ppl, mtgs = scenarios.feasible()
    s = Scheduler(ppl, mtgs)
    r = s.solve()
    print(f"  status={r.status}  objective(priority booked)={r.objective}  solve={r.solve_ms:.1f}ms")
    for mid, (a, b) in sorted(r.schedule.items(), key=lambda kv: kv[1]):
        who = ",".join(next(m.participants for m in mtgs if m.mid == mid))
        print(f"    {mid:14s} {fmt(a)}-{fmt(b)} UTC   ({who})")
    v = violations(s, r)
    print(f"  independent constraint check: {len(v)} violations  -> {'PASS' if not v else v}")

    banner("OVERSUBSCRIBED: explain the infeasibility (not just 'no solution')")
    ppl2, mtgs2 = scenarios.oversubscribed()
    s2 = Scheduler(ppl2, mtgs2)
    r2 = s2.solve()
    core = s2.explain_infeasible([m.mid for m in mtgs2])
    print(f"  forcing all {len(mtgs2)} all-hands required -> {r2.status}")
    print(f"  minimal conflicting set (IIS-style): {core}")
    print(f"  >>> these {len(core)} meetings cannot all share the available window;")
    print(f"      drop/relax one and it becomes feasible. A greedy solver would")
    print(f"      have silently dropped or mis-placed one instead.")

    banner("BENCHMARK: solve time vs size (2-person meetings, pool grows with n)")
    print(f"  {'meetings':>9} | {'status':>8} | {'booked':>6} | {'solve(ms)':>9}")
    for n in (12, 30, 60):
        pool, ms = scenarios.scaled(n)
        rs = Scheduler(pool, ms).solve(max_seconds=10)
        booked = len(rs.scheduled)
        print(f"  {n:>9} | {rs.status:>8} | {booked:>6} | {rs.solve_ms:>9.1f}")

    banner("RESULT")
    ok = (r.status in ("OPTIMAL", "FEASIBLE") and not v
          and r2.status == "INFEASIBLE" and len(core) >= 2)
    print(
        f"  optimal feasible schedule, 0 violations : {r.status in ('OPTIMAL','FEASIBLE') and not v}\n"
        f"  infeasibility explained (not just failed): {r2.status == 'INFEASIBLE' and len(core) >= 2}\n"
        f"  ALL CHECKS PASS: {ok}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
