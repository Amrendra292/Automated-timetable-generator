"""Explainable timetable quality metrics and rule-based recommendations."""
from collections import Counter, defaultdict
from statistics import mean, pstdev
from sqlalchemy.orm import Session
from .models import Course, Faculty, Room, ScheduleRun, StudentGroup, TimeSlot, TimetableEntry
from .scheduler import OPTIMIZATION_PROFILES


def build_quality_report(db: Session, optimization_profile: str | None = None) -> dict:
    entries = db.query(TimetableEntry).all()
    if optimization_profile is None:
        latest_run = db.query(ScheduleRun).order_by(ScheduleRun.id.desc()).first()
        optimization_profile = latest_run.optimization_profile if latest_run else "balanced"
    if not entries:
        return {
            "generated": False,
            "optimization_profile": optimization_profile,
            "profile_label": OPTIMIZATION_PROFILES.get(optimization_profile, OPTIMIZATION_PROFILES["balanced"])["label"],
            "sessions_scheduled": 0,
            "quality_score": 0,
            "hard_conflicts": 0,
            "compactness_score": 0,
            "average_idle_gaps_per_group_day": 0,
            "average_campus_days_per_group": 0,
            "campus_day_score": 0,
            "seat_utilization_pct": 0,
            "weekday_load_balance_score": 0,
            "daily_session_load": {},
            "recommendations": [{
                "title": "Generate your first timetable",
                "detail": "Add courses, faculty, groups and suitable rooms, then run the optimizer to create a schedule for analysis.",
                "priority": "next step",
            }],
            "score_method": "Indicative heuristic score; see README for component weights.",
        }

    faculty = {x.id: x for x in db.query(Faculty).all()}
    groups = {x.id: x for x in db.query(StudentGroup).all()}
    rooms = {x.id: x for x in db.query(Room).all()}
    courses = {x.id: x for x in db.query(Course).all()}
    slots = {x.id: x for x in db.query(TimeSlot).all()}

    faculty_slot, group_slot, room_slot = Counter(), Counter(), Counter()
    faculty_day_load = Counter()
    group_day_orders = defaultdict(list)
    group_active_days = defaultdict(set)
    seat_ratios = []
    conflicts = 0

    for entry in entries:
        slot = slots.get(entry.slot_id)
        room = rooms.get(entry.room_id)
        group = groups.get(entry.group_id)
        teacher = faculty.get(entry.faculty_id)
        if not slot or not room or not group or not teacher:
            conflicts += 1
            continue
        faculty_slot[(entry.faculty_id, entry.slot_id)] += 1
        group_slot[(entry.group_id, entry.slot_id)] += 1
        room_slot[(entry.room_id, entry.slot_id)] += 1
        faculty_day_load[(entry.faculty_id, slot.day)] += 1
        group_day_orders[(entry.group_id, slot.day)].append(slot.slot_order)
        group_active_days[entry.group_id].add(slot.day)
        seat_ratios.append(min(1.0, group.size / max(room.capacity, 1)))
        course = courses.get(entry.course_id)
        if room.capacity < group.size:
            conflicts += 1
        if course and room.room_type != course.room_type:
            conflicts += 1
        if slot.id in (teacher.unavailable_slots or []):
            conflicts += 1

    conflicts += sum(count - 1 for count in faculty_slot.values() if count > 1)
    conflicts += sum(count - 1 for count in group_slot.values() if count > 1)
    conflicts += sum(count - 1 for count in room_slot.values() if count > 1)
    for (faculty_id, day), count in faculty_day_load.items():
        teacher = faculty.get(faculty_id)
        if teacher and count > teacher.max_daily_load:
            conflicts += count - teacher.max_daily_load

    idle_gaps = []
    possible_gap_slots = 0
    for orders in group_day_orders.values():
        unique_orders = sorted(set(orders))
        gaps = sum(max(0, unique_orders[i + 1] - unique_orders[i] - 1) for i in range(len(unique_orders) - 1))
        idle_gaps.append(gaps)
        possible_gap_slots += max(0, unique_orders[-1] - unique_orders[0] - 1) if unique_orders else 0
    total_gaps = sum(idle_gaps)
    avg_gaps = mean(idle_gaps) if idle_gaps else 0.0
    avg_campus_days = mean(len(days) for days in group_active_days.values()) if group_active_days else 0.0
    compactness = 100.0 if possible_gap_slots == 0 else max(0.0, 100.0 * (1 - total_gaps / possible_gap_slots))

    daily_totals = Counter()
    for (_, day), count in faculty_day_load.items():
        daily_totals[day] += count
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_values = [daily_totals.get(day, 0) for day in days]
    avg_day = mean(day_values) if day_values else 0.0
    cv = (pstdev(day_values) / avg_day) if avg_day else 0.0
    load_balance = max(0.0, min(100.0, 100.0 * (1 - cv)))

    seat_utilization = (mean(seat_ratios) * 100.0) if seat_ratios else 0.0
    campus_day_score = max(0.0, min(100.0, 100.0 * (1 - avg_campus_days / 5.0)))
    conflict_score = max(0.0, 100.0 - conflicts * 25.0)
    quality_score = round(
        conflict_score * 0.35
        + compactness * 0.20
        + load_balance * 0.10
        + seat_utilization * 0.10
        + campus_day_score * 0.25,
        1,
    )

    recommendations = []
    if conflicts:
        recommendations.append({"title": "Review hard-constraint violations", "detail": f"The audit found {conflicts} issue(s). Re-run generation after checking resource availability and capacities.", "priority": "high"})
    if avg_gaps > 1.0:
        recommendations.append({"title": "Reduce student idle periods", "detail": f"Groups average {avg_gaps:.1f} empty slot(s) between classes on an active day. Try the Student-first profile.", "priority": "medium"})
    if avg_campus_days > 3.5:
        recommendations.append({"title": "Explore a more compact campus week", "detail": f"Groups use an average of {avg_campus_days:.1f} weekdays. Compare Student-first mode to cluster classes into fewer campus days.", "priority": "medium"})
    if seat_utilization < 65:
        recommendations.append({"title": "Improve room-to-group fit", "detail": f"Average seat utilization is {seat_utilization:.0f}%. Review room capacities or try Resource efficient mode.", "priority": "medium"})
    if load_balance < 55:
        recommendations.append({"title": "Review weekly load distribution", "detail": "Sessions are concentrated unevenly across weekdays. Compare the Balanced campus profile with your availability constraints.", "priority": "low"})
    if not recommendations:
        recommendations.append({"title": "Schedule looks healthy", "detail": "No audited hard conflicts were found and the measured quality indicators are within the current guidance thresholds.", "priority": "info"})

    return {
        "generated": True,
        "optimization_profile": optimization_profile,
        "profile_label": OPTIMIZATION_PROFILES.get(optimization_profile, OPTIMIZATION_PROFILES["balanced"])["label"],
        "sessions_scheduled": len(entries),
        "quality_score": quality_score,
        "hard_conflicts": conflicts,
        "compactness_score": round(compactness, 1),
        "average_idle_gaps_per_group_day": round(avg_gaps, 2),
        "average_campus_days_per_group": round(avg_campus_days, 2),
        "campus_day_score": round(campus_day_score, 1),
        "seat_utilization_pct": round(seat_utilization, 1),
        "weekday_load_balance_score": round(load_balance, 1),
        "daily_session_load": {day: daily_totals.get(day, 0) for day in days},
        "recommendations": recommendations,
        "score_method": "Indicative heuristic score: 35% conflict audit, 20% compactness, 10% weekday load distribution, 10% seat utilization and 25% campus-day footprint. Not an industry-standard benchmark.",
    }
