# SchedWise — Placement Interview Guide

## 60-second project explanation

“SchedWise is a full-stack campus timetable optimization platform. I built the frontend with React and TypeScript and the backend with FastAPI and SQLAlchemy, with PostgreSQL support. An administrator can manage courses, faculty, student groups and classrooms, then generate a weekly timetable. What makes the project different is that the administrator can choose between three optimization profiles—Balanced campus, Student-first and Resource efficient. The scheduling engine uses Minimum Remaining Values to pick the most constrained class session, backtracking to recover from invalid branches, and weighted soft constraints to rank candidate slot and room assignments. After generation, an explainable audit reports conflicts, student idle gaps, average campus days per group, seat utilization and weekday load distribution, then suggests rule-based improvements.”

## What is technically interesting?

1. **Constraint satisfaction:** Faculty, student groups and rooms cannot be double-booked in the same slot.
2. **MRV heuristic:** Choose the remaining session with the fewest legal placements first, reducing branching on constrained tasks.
3. **Backtracking:** If a placement makes the remainder impossible, undo it and try another candidate.
4. **Multi-objective scoring:** Profiles change the relative penalty for student gaps, faculty gaps, repeated same-day sessions, room-capacity waste, opening an additional room for a day and faculty daily-load concentration.
5. **Explainability:** The quality endpoint returns metrics and the weighted quality-index formula, not just a black-box score.

## Likely interviewer questions

### Why did you use MRV?
MRV prioritizes the most constrained session. A session with few legal slot/room combinations is more likely to cause failure, so placing it early can reduce wasted search.

### What are hard and soft constraints?
Hard constraints must never be violated, such as faculty, group or room clashes and room capacity. Soft constraints express preferences, such as minimizing gaps or unused room capacity. The profile changes soft-constraint weights only.

### Does the scheduler guarantee the best possible timetable?
No. It uses bounded backtracking and heuristic candidate ordering to find a feasible schedule. It does not prove global optimality. A CP-SAT solver such as OR-Tools would be a reasonable next step for exact or more advanced optimization studies.

### How do the three profiles differ?
Balanced campus distributes importance across student gaps, faculty spacing and room fit. Student-first penalizes idle gaps and activating an additional campus day for a student group. Resource efficient penalizes activating more rooms during a day and also considers room-capacity fit. The hard constraints remain the same.

### How is the quality index calculated?
It is a transparent, portfolio-specific weighted indicator: 35% conflict audit, 20% compactness, 10% weekday session distribution, 10% seat utilization and 25% campus-day footprint. I explain that it is not an industry-standard benchmark and discuss the component metrics separately.

### How do you test correctness?
Automated tests verify that generated assignments do not reuse faculty, student group or room slots, and that the generator rejects a course when no compatible room exists. Additional tests cover profile validation and the quality report. The API smoke test checks login, schedule generation and quality-audit retrieval.

### What would you improve next?
I would add multi-hour lab blocks, a faculty availability editor, schedule version comparison, PDF/ICS exports and an OR-Tools CP-SAT benchmark against the current MRV/backtracking baseline.

## Demo flow (2–3 minutes)

1. Sign in with the local demo administrator account.
2. Show the seeded courses, faculty, student groups and rooms.
3. Open Timetable and choose **Balanced campus**; generate and show the weekly grid.
4. Open **Quality insights** and explain the conflict audit, compactness, seat utilization and weekday distribution.
5. Return to Timetable, choose **Student-first** or **Resource efficient**, regenerate and compare active campus days per group, room allocation and the quality metrics.
6. Export the timetable as CSV and open `/docs` to show the API contract.

## Honest discussion points

- The optimization profiles guide a heuristic search; they do not prove global optimality.
- The quality index is project-defined and should not be compared with an external benchmark.
- The current domain model supports one-hour sessions; multi-hour lab blocks are future work.
- Never claim that a feature is AI-powered. The project uses search heuristics, weighted scoring and deterministic rule-based recommendations.
