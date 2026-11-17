# SchedWise — Explainable Multi-Objective Campus Timetable Optimizer

SchedWise is a full-stack academic scheduling platform that generates weekly timetables while balancing student compactness, teaching-resource fit and weekday load distribution. Its differentiator is an **explainable optimization workflow**: an administrator can choose one of three scheduling profiles, inspect an audit of the generated timetable and receive rule-based recommendations tied to measurable schedule indicators.

This is **not a generative-AI chatbot**. The core engineering is a constraint-satisfaction/search problem with Minimum Remaining Values (MRV), backtracking and configurable soft-constraint scoring. The quality index is an indicative project metric, not an industry-standard university benchmark.

## What makes it different

### 1. Three optimization profiles

| Profile | Priority | Trade-off |
|---|---|---|
| Balanced campus | Compromise between student gaps, faculty spacing, repeat-course distribution and room fit | General-purpose starting point |
| Student-first | Clusters classes into fewer campus days while reducing within-day gaps | May create a less even weekday load across the whole campus |
| Resource efficient | Prioritizes reuse of rooms across the day and reduces room-day fragmentation, with a capacity-fit penalty | May accept more student/faculty gaps |

The profiles change the candidate-slot scoring weights inside the scheduler. They do not change hard constraints: an accepted schedule must still avoid faculty, group and room clashes, respect faculty unavailability and daily teaching limits, and assign rooms with suitable type and capacity.

### 2. Explainable quality audit

After generation, the backend audits the saved schedule and calculates:

- **Hard conflicts:** faculty/group/room overlaps, faculty unavailability, daily-load overflow, room capacity and room-type mismatches.
- **Compactness:** empty time-slot positions between the first and last class of each active student-group day.
- **Campus-day footprint:** average number of weekdays used by each scheduled student group; Student-first mode adds a strong penalty for opening another group-day.
- **Seat utilization:** average student-group size divided by the assigned room's capacity.
- **Weekday distribution:** how evenly the total number of sessions is spread across weekdays.
- **Rule-based recommendations:** specific next actions based on the measured indicators.

The **indicative quality index** uses 35% conflict audit, 20% compactness, 10% weekday distribution, 10% seat utilization and 25% campus-day footprint. The formula is exposed in the API response so the score is explainable; it should not be presented as a certified or externally validated score.

### 3. Full-stack workflow

- JWT-protected admin workspace.
- Manage courses, faculty, rooms and student groups.
- Generate a conflict-aware weekly timetable with one selected optimization profile.
- Filter timetable by student group and export CSV.
- Review the quality insights dashboard with weekday load bars and prioritized recommendations.
- FastAPI OpenAPI / Swagger documentation.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Styling | Tailwind CSS 4 + custom responsive CSS |
| Backend | Python, FastAPI, Pydantic |
| Data | PostgreSQL / SQLite, SQLAlchemy 2 |
| Authentication | JWT, PBKDF2-SHA256 password hashing |
| Scheduling | Constraint satisfaction, MRV, backtracking, weighted soft-constraint scoring |
| Quality audit | Python aggregation, explainable scoring and rule-based recommendations |
| API docs | OpenAPI / Swagger UI |
| Tests | Pytest |
| Containerization | Docker Compose |

## Quick start (Windows PowerShell)

### Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer and npm

### 1. Start the backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation, run this in the current terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

The API creates the local SQLite database and demonstration data automatically on first start. The Docker configuration uses PostgreSQL.

### 2. Start the frontend (new terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

### 3. Demo login

- Email: `admin@schedwise.dev`
- Password: `Admin@123`

Change the demo password and JWT secret before any public deployment. Replace demonstration data with your own test data before recording a project demo.

## Docker Compose (PostgreSQL + API + frontend)

From the project root:

```bash
docker compose up --build
```

Then open:
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Scheduling algorithm

1. Expand every course's weekly requirement into individual session tasks.
2. Build candidate slot/room combinations after filtering hard constraints.
3. Use **Minimum Remaining Values (MRV)** to select the task with the fewest currently available choices. A degree tie-breaker prioritizes tasks that share a faculty member or student group with more remaining tasks.
4. Rank candidate assignments with the selected profile's weighted soft-constraint score. The score considers student-group gaps, opening an additional campus day for a group, faculty gaps, repeated same-day sessions, room-capacity waste, opening an additional room for a day and faculty daily-load concentration.
5. Use **backtracking** when an assignment blocks all remaining options. Candidate domains are recalculated after each placement (forward-checking behavior).
6. Persist the schedule only when a complete assignment has been found; partial schedules are not saved.

The search is bounded by 60,000 candidate nodes by default. This is a heuristic first-feasible search with profile-based candidate ordering, not a proof of global optimality. For larger deployments, an OR-Tools CP-SAT model could be evaluated against this baseline.

### Seeded demo comparison

The following results were observed with the included 23-session demonstration dataset. They show that the profiles create different allocations and trade-offs; the figures are illustrative for this seed data, not a performance claim for every institution.

| Profile | Sessions | Average active weekdays per group | Audited hard conflicts | Indicative quality index |
|---|---:|---:|---:|---:|
| Balanced campus | 23 | 4.00 | 0 | 77.5 |
| Student-first | 23 | 2.00 | 0 | 79.2 |
| Resource efficient | 23 | 3.33 | 0 | 72.9 |

## Quality index methodology

The API returns the individual components and the formula alongside the score:

```text
quality_index = 0.35 * conflict_score
              + 0.20 * compactness_score
              + 0.10 * weekday_load_balance_score
              + 0.10 * seat_utilization_score
              + 0.25 * campus_day_score
```

`conflict_score` starts at 100 and drops by 25 per audited conflict, with a floor of 0. `campus_day_score` is based on average active weekdays per scheduled group relative to the five-day week. The other components are bounded from 0 to 100. This is a transparent portfolio metric designed to make trade-offs visible; users should review the component metrics instead of relying only on the aggregate.

## API endpoints

All `/api/*` endpoints except `/api/auth/login` require `Authorization: Bearer <token>`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/auth/login` | Obtain JWT token |
| GET | `/api/auth/me` | Current admin profile |
| GET | `/api/dashboard/stats` | Dashboard totals |
| GET/POST | `/api/courses` | List / create courses |
| GET/POST | `/api/faculty` | List / create faculty |
| GET/POST | `/api/rooms` | List / create rooms |
| GET/POST | `/api/groups` | List / create student groups |
| GET | `/api/slots` | List weekly time slots |
| GET | `/api/timetable` | View generated timetable (`?group_id=1` optional) |
| POST | `/api/timetable/generate` | Generate timetable; body accepts `optimization_profile` (`balanced`, `student_first`, `resource_saver`) |
| GET | `/api/analytics/quality` | Audit current timetable and return quality metrics/recommendations |
| DELETE | `/api/timetable` | Clear timetable and latest run metadata |
| GET | `/api/timetable/export.csv` | Download CSV export |

Swagger UI: http://localhost:8000/docs

## Tests

From `backend/`:

```powershell
python -m pytest -q
```

Tests cover conflict-free generation, missing compatible rooms, profile selection and quality-report generation. A local API smoke test also exercised JWT login, Student-first generation and the quality endpoint against the seeded demo dataset.

## Strong resume bullets

Use these after you have run the application yourself and can explain the code:

- Built **SchedWise**, a full-stack campus timetable optimizer using React, TypeScript, FastAPI and PostgreSQL, with JWT-protected resource management and CSV timetable export.
- Implemented an MRV-based backtracking scheduler with three weighted optimization profiles, balancing student idle gaps, faculty spacing and classroom-capacity utilization while enforcing hard scheduling constraints.
- Developed an explainable schedule-audit API and dashboard that report timetable conflicts, compactness, seat utilization and weekday load distribution, then generate rule-based improvement recommendations.

## Suggested GitHub repository description

`SchedWise is an explainable multi-objective campus timetable optimizer built with React, TypeScript, FastAPI and PostgreSQL. It uses MRV backtracking, configurable scheduling profiles and a quality-audit dashboard to balance student compactness and room utilization while enforcing hard constraints.`

## Current scope and limitations

- Supports one-hour sessions and a Monday–Friday template. Multi-hour labs, holidays, semester-specific calendars and cross-listed courses are not modeled yet.
- Faculty unavailability is supported in the backend data model; the current UI does not yet provide an editor for unavailable slot IDs.
- The current scheduler uses a bounded backtracking search with heuristic candidate ordering. The three profiles express different priorities; they do not guarantee a globally optimal result.
- The quality index is an internal, explainable heuristic, not an independently validated metric.
- The demo account and secrets are for local development only. Add admin user management, password reset, rate limiting, audit logs, production secret management and a deployment-specific security review before public use.
