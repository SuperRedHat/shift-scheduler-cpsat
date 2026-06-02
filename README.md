# shift-scheduler-cpsat — a CP-SAT meeting scheduler that explains itself

A small, runnable CP-SAT model that schedules multi-party meetings across
timezones under working-hours / buffer / priority / no-double-booking
constraints — and, when a set of calendars is **oversubscribed**, returns a
**minimal conflicting subset** ("these N meetings can't all fit") instead of a
bare "infeasible". Built on Google OR-Tools.

```bash
pip install -r requirements.txt    # ortools
python demo.py                     # optimal schedule + infeasibility explainer + benchmark
python -m pytest -q                # 10 tests, incl. an independent constraint checker
```

---

## The hard part — and how this handles it

Coordinating meetings across calendars and timezones is NP-hard: working hours,
buffers, priorities and "nobody double-booked" interact, and the simultaneously-
available window is narrow. A greedy/nested-loop scheduler ships invalid
schedules the moment constraints conflict, and on an over-subscribed calendar it
either hangs or silently drops a meeting. CP-SAT gives an **optimal** schedule
when one exists and an **explanation** when one doesn't:

- **Timezone + DST aware.** Working hours are per participant in their own zone,
  with a per-day UTC offset, so a participant crossing a DST boundary (offset
  `-5 → -4` on day 1) is placed correctly — a fixed-offset model would be an
  hour off on day 2.
- **Hard constraints, modelled not hoped.** Allowed start domains encode
  working-hours + busy-block avoidance; per-participant `NoOverlap` over
  buffer-padded intervals enforces no-double-booking + the inter-meeting buffer.
- **Priorities as the objective.** Maximise booked priority; lower-priority
  meetings yield first under contention.
- **Infeasibility explainer (IIS-style).** Force the required meetings as CP-SAT
  *assumptions*; on `INFEASIBLE`, `SufficientAssumptionsForInfeasibility()`
  returns the minimal subset that mutually conflicts.

---

## What the demo prints

```
FEASIBLE: status=OPTIMAL  objective=20  solve≈18ms      (3 timezones, C crosses DST)
   ab-sync     D0 09:00–10:00   all-hands  D0 14:00–15:00 / D1 13:00–14:00 / D1 14:30–15:30 …
   independent constraint check: 0 violations  -> PASS

OVERSUBSCRIBED: forcing 4 all-hands required -> INFEASIBLE
   minimal conflicting set: [all-hands-1..4]   (any 3 fit; the 4th is the conflict)

BENCHMARK   12 → OPTIMAL 12ms · 30 → OPTIMAL 12ms · 60 → OPTIMAL 27ms
```

---

## Tests that have teeth

- `test_no_hard_constraint_ever_violated` — for sizes 8/12/24/40, an
  **independent checker** (not CP-SAT) re-derives the schedule and asserts **0**
  violations: no double-booking, every meeting inside all participants' working
  hours, busy blocks avoided, buffer respected.
- `test_oversubscribed_is_infeasible_with_a_core` +
  `test_relaxing_the_core_restores_feasibility` — the explainer returns a real
  conflict, and dropping one core member makes it solvable.
- `test_dst_aware_placement` — day-1 all-hands land in the post-DST window.
- `test_busy_block_is_respected` — no meeting overlaps a pre-existing event.

CI (`.github/workflows/ci.yml`) installs OR-Tools and runs the suite + demo.

---

## How this maps to your posting (CP-SAT scheduling review)

Your scope was: review the CP-SAT model for correctness/completeness; validate
working-hours, timezone, buffer, priority and back-to-back constraints; find
edge cases (DST, oversubscribed calendars, circular dependencies); assess scale;
deliver pass/fail per constraint + recommendations. This repo is a *worked
reference of exactly that*:

- the **independent checker** (`scheduler/checker.py`) is precisely a
  per-constraint pass/fail oracle — the shape of the deliverable I'd hand you;
- the **infeasibility explainer** is how I'd diagnose your "oversubscribed
  calendars" / "circular dependencies" edge cases instead of guessing;
- the **DST handling** and the **benchmark** show the timezone and scalability
  checks you asked for (your "50+ events per user").

How I'd review yours: re-express each of your stated constraints as an
independent check, build adversarial instances (DST boundary, oversubscription,
zero-availability participant, conflicting priorities), run them against your
model, and report pass/fail + a minimal failing instance for every gap — plus
solve-time vs size at your target scale.

## How I'd productionize / extend

- Optional-meeting soft objective with lateness/back-to-back weights; per-room
  or per-resource capacity via additional `NoOverlap` dimensions.
- Real IANA timezones (zoneinfo) replacing the per-day offset model; calendar
  ingestion for busy blocks.
- Warm-start + time-limited search with a reported optimality gap at large n.

## Assumptions & limitations (honest scope)

- A demo of the modelling + diagnosis pattern: 30-min slots, a 2-day horizon,
  per-day integer offsets (a clean stand-in for full IANA/DST). Your real
  constraints, calendars and scale are the engagement.

MIT licensed — see `LICENSE`.
