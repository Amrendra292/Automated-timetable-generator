"""Constraint-based timetable generator using MRV backtracking and soft scoring."""
from collections import defaultdict
from dataclasses import dataclass
from sqlalchemy.orm import Session
from .models import Course, Faculty, Room, StudentGroup, TimeSlot


@dataclass(frozen=True)
class SessionTask:
    key: str
    course: Course
    faculty: Faculty
    group: StudentGroup


class SchedulingError(Exception):
    def __init__(self, message: str, diagnostics: dict | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


OPTIMIZATION_PROFILES = {
    "balanced": {
        "label": "Balanced campus",
        "description": "Balances student compactness, faculty spacing and room fit.",
        "group_gap": 5.0, "faculty_gap": 1.5, "same_course_day": 4.0,
        "room_waste": 1.0, "room_activation": 0.5, "group_day_activation": 0.5, "faculty_daily_load": 1.0,
    },
    "student_first": {
        "label": "Student-first",
        "description": "Clusters classes into fewer campus days and prioritizes compact student timetables.",
        "group_gap": 12.0, "faculty_gap": 0.5, "same_course_day": 2.0,
        "room_waste": 0.2, "room_activation": 0.1, "group_day_activation": 12.0, "faculty_daily_load": 0.2,
    },
    "resource_saver": {
        "label": "Resource efficient",
        "description": "Prioritizes room reuse and reduced room-day fragmentation while retaining capacity fit.",
        "group_gap": 3.0, "faculty_gap": 1.0, "same_course_day": 3.0,
        "room_waste": 2.5, "room_activation": 4.0, "group_day_activation": 0.2, "faculty_daily_load": 1.2,
    },
}


def generate_schedule(
    db: Session,
    max_search_nodes: int = 60000,
    optimization_profile: str = "balanced",
) -> list[dict]:
    if optimization_profile not in OPTIMIZATION_PROFILES:
        raise SchedulingError(
            "Unknown optimization profile.",
            {"available_profiles": sorted(OPTIMIZATION_PROFILES)},
        )
    weights = OPTIMIZATION_PROFILES[optimization_profile]

    courses = db.query(Course).order_by(Course.id).all()
    faculty_by_id = {x.id: x for x in db.query(Faculty).all()}
    groups_by_id = {x.id: x for x in db.query(StudentGroup).all()}
    rooms = db.query(Room).order_by(Room.capacity).all()
    slots = db.query(TimeSlot).order_by(TimeSlot.day, TimeSlot.slot_order).all()

    if not courses or not rooms or not slots:
        raise SchedulingError("Add at least one course, one room and the weekly time slots before generating a timetable.")

    tasks: list[SessionTask] = []
    for course in courses:
        faculty = faculty_by_id.get(course.faculty_id)
        group = groups_by_id.get(course.group_id)
        if not faculty or not group:
            raise SchedulingError(f"Course {course.code} has a missing faculty member or student group.")
        for session_no in range(1, course.sessions_per_week + 1):
            tasks.append(SessionTask(f"{course.id}-{session_no}", course, faculty, group))

    room_candidates = {
        course.id: [room for room in rooms if room.capacity >= groups_by_id[course.group_id].size and room.room_type == course.room_type]
        for course in courses
    }
    impossible = [c.code for c in courses if not room_candidates[c.id]]
    if impossible:
        raise SchedulingError(
            "Some courses do not have a room with the required type and capacity.",
            {"courses_without_compatible_rooms": impossible},
        )

    occupied_faculty: set[tuple[int, int]] = set()
    occupied_group: set[tuple[int, int]] = set()
    occupied_room: set[tuple[int, int]] = set()
    faculty_day_load: dict[tuple[int, str], int] = defaultdict(int)
    group_day_slots: dict[tuple[int, str], list[int]] = defaultdict(list)
    group_day_usage: dict[tuple[int, str], int] = defaultdict(int)
    faculty_day_slots: dict[tuple[int, str], list[int]] = defaultdict(list)
    course_day_count: dict[tuple[int, str], int] = defaultdict(int)
    room_day_usage: dict[tuple[int, str], int] = defaultdict(int)
    assigned: dict[str, tuple[TimeSlot, Room]] = {}
    nodes = 0

    def available(task: SessionTask) -> list[tuple[TimeSlot, Room]]:
        choices: list[tuple[TimeSlot, Room]] = []
        blocked = set(task.faculty.unavailable_slots or [])
        for slot in slots:
            if slot.id in blocked:
                continue
            if (task.faculty.id, slot.id) in occupied_faculty:
                continue
            if (task.group.id, slot.id) in occupied_group:
                continue
            if faculty_day_load[(task.faculty.id, slot.day)] >= task.faculty.max_daily_load:
                continue
            for room in room_candidates[task.course.id]:
                if (room.id, slot.id) not in occupied_room:
                    choices.append((slot, room))
        return choices

    def gap_count(existing: list[int], new_order: int) -> int:
        ordered = sorted(existing + [new_order])
        return sum(max(0, ordered[i + 1] - ordered[i] - 1) for i in range(len(ordered) - 1))

    def score(task: SessionTask, slot: TimeSlot, room: Room) -> float:
        # Lower scores are preferred. Hard constraints are filtered in available().
        group_gaps = gap_count(group_day_slots[(task.group.id, slot.day)], slot.slot_order)
        faculty_gaps = gap_count(faculty_day_slots[(task.faculty.id, slot.day)], slot.slot_order)
        same_course_day = course_day_count[(task.course.id, slot.day)]
        room_waste = max(0, room.capacity - task.group.size) / max(room.capacity, 1)
        # Penalize concentrating all of a faculty member's classes on one day.
        # The profile weights expose a transparent multi-objective trade-off.
        faculty_daily_load = faculty_day_load[(task.faculty.id, slot.day)]
        new_room_day = 1.0 if room_day_usage[(room.id, slot.day)] == 0 else 0.0
        new_group_day = 1.0 if group_day_usage[(task.group.id, slot.day)] == 0 else 0.0
        return (
            group_gaps * weights["group_gap"]
            + faculty_gaps * weights["faculty_gap"]
            + same_course_day * weights["same_course_day"]
            + room_waste * weights["room_waste"]
            + new_room_day * weights["room_activation"]
            + new_group_day * weights["group_day_activation"]
            + (faculty_daily_load ** 2) * weights["faculty_daily_load"]
            + slot.slot_order * 0.015
        )

    def place(task: SessionTask, slot: TimeSlot, room: Room) -> None:
        assigned[task.key] = (slot, room)
        occupied_faculty.add((task.faculty.id, slot.id))
        occupied_group.add((task.group.id, slot.id))
        occupied_room.add((room.id, slot.id))
        faculty_day_load[(task.faculty.id, slot.day)] += 1
        group_day_slots[(task.group.id, slot.day)].append(slot.slot_order)
        group_day_usage[(task.group.id, slot.day)] += 1
        faculty_day_slots[(task.faculty.id, slot.day)].append(slot.slot_order)
        course_day_count[(task.course.id, slot.day)] += 1
        room_day_usage[(room.id, slot.day)] += 1

    def unplace(task: SessionTask, slot: TimeSlot, room: Room) -> None:
        assigned.pop(task.key, None)
        occupied_faculty.remove((task.faculty.id, slot.id))
        occupied_group.remove((task.group.id, slot.id))
        occupied_room.remove((room.id, slot.id))
        faculty_day_load[(task.faculty.id, slot.day)] -= 1
        group_day_slots[(task.group.id, slot.day)].remove(slot.slot_order)
        group_day_usage[(task.group.id, slot.day)] -= 1
        faculty_day_slots[(task.faculty.id, slot.day)].remove(slot.slot_order)
        course_day_count[(task.course.id, slot.day)] -= 1
        room_day_usage[(room.id, slot.day)] -= 1

    def search(remaining: list[SessionTask]) -> bool:
        nonlocal nodes
        if not remaining:
            return True
        if nodes >= max_search_nodes:
            return False

        # Minimum Remaining Values (MRV): branch on the most constrained session first.
        best_task = None
        best_choices = None
        best_degree = -1
        for task in remaining:
            choices = available(task)
            if not choices:
                return False
            degree = sum(1 for other in remaining if other.key != task.key and (
                other.faculty.id == task.faculty.id or other.group.id == task.group.id
            ))
            if best_choices is None or len(choices) < len(best_choices) or (
                len(choices) == len(best_choices) and degree > best_degree
            ):
                best_task, best_choices, best_degree = task, choices, degree
                if len(best_choices) == 1:
                    break

        assert best_task is not None and best_choices is not None
        best_choices.sort(key=lambda pair: score(best_task, pair[0], pair[1]))
        next_remaining = [task for task in remaining if task.key != best_task.key]
        for slot, room in best_choices:
            nodes += 1
            place(best_task, slot, room)
            if search(next_remaining):
                return True
            unplace(best_task, slot, room)
            if nodes >= max_search_nodes:
                break
        return False

    if not search(tasks):
        raise SchedulingError(
            "A conflict-free timetable could not be found with the current constraints. Add more rooms or time slots, increase faculty availability, or reduce weekly sessions.",
            {"search_nodes": nodes, "sessions_requested": len(tasks)},
        )

    result = []
    task_by_key = {task.key: task for task in tasks}
    for key, (slot, room) in assigned.items():
        task = task_by_key[key]
        result.append({
            "course_id": task.course.id,
            "faculty_id": task.faculty.id,
            "group_id": task.group.id,
            "room_id": room.id,
            "slot_id": slot.id,
        })
    return result
