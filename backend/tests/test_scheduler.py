from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import Course, Faculty, Room, ScheduleRun, StudentGroup, TimeSlot
from app.scheduler import generate_schedule


def make_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_generator_never_creates_hard_conflicts():
    db = make_db()
    db.add_all([
        Faculty(id=1, name="Faculty One", email="one@test.dev", max_daily_load=3),
        Faculty(id=2, name="Faculty Two", email="two@test.dev", max_daily_load=3),
        StudentGroup(id=1, name="CSE-A", size=30),
        StudentGroup(id=2, name="CSE-B", size=25),
        Room(id=1, name="R-1", capacity=40, room_type="classroom"),
        Room(id=2, name="Lab-1", capacity=40, room_type="lab"),
    ])
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        for order in range(4):
            start_hour = 9 + order
            db.add(TimeSlot(day=day, start_time=f"{start_hour:02d}:00", end_time=f"{start_hour+1:02d}:00", slot_order=order))
    db.add_all([
        Course(code="CS1", title="Programming", faculty_id=1, group_id=1, sessions_per_week=3, room_type="classroom"),
        Course(code="CS2", title="Networks", faculty_id=2, group_id=2, sessions_per_week=3, room_type="classroom"),
        Course(code="CS3L", title="Lab", faculty_id=1, group_id=2, sessions_per_week=1, room_type="lab"),
    ])
    db.commit()
    result = generate_schedule(db)
    assert len(result) == 7
    assert len({(x["faculty_id"], x["slot_id"]) for x in result}) == len(result)
    assert len({(x["group_id"], x["slot_id"]) for x in result}) == len(result)
    assert len({(x["room_id"], x["slot_id"]) for x in result}) == len(result)


def test_generator_rejects_missing_compatible_room():
    from app.scheduler import SchedulingError
    db = make_db()
    db.add_all([
        Faculty(id=1, name="Faculty One", email="one@test.dev", max_daily_load=3),
        StudentGroup(id=1, name="CSE-A", size=50),
        Room(id=1, name="Small Room", capacity=25, room_type="classroom"),
        TimeSlot(id=1, day="Monday", start_time="09:00", end_time="10:00", slot_order=0),
        Course(code="CS1", title="Programming", faculty_id=1, group_id=1, sessions_per_week=1, room_type="classroom"),
    ])
    db.commit()
    try:
        generate_schedule(db)
        assert False, "Expected a SchedulingError for a room that is too small"
    except SchedulingError as exc:
        assert "required type and capacity" in str(exc)
        assert exc.diagnostics["courses_without_compatible_rooms"] == ["CS1"]


def test_optimization_profiles_generate_valid_schedules_and_quality_report():
    from app.analytics import build_quality_report
    from app.models import TimetableEntry

    db = make_db()
    db.add_all([
        Faculty(id=1, name="Faculty One", email="one@test.dev", max_daily_load=3),
        Faculty(id=2, name="Faculty Two", email="two@test.dev", max_daily_load=3),
        StudentGroup(id=1, name="CSE-A", size=30),
        StudentGroup(id=2, name="CSE-B", size=25),
        Room(id=1, name="R-1", capacity=40, room_type="classroom"),
        Room(id=2, name="Lab-1", capacity=40, room_type="lab"),
    ])
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        for order in range(4):
            start_hour = 9 + order
            db.add(TimeSlot(day=day, start_time=f"{start_hour:02d}:00", end_time=f"{start_hour+1:02d}:00", slot_order=order))
    db.add_all([
        Course(code="CS1", title="Programming", faculty_id=1, group_id=1, sessions_per_week=3, room_type="classroom"),
        Course(code="CS2", title="Networks", faculty_id=2, group_id=2, sessions_per_week=3, room_type="classroom"),
        Course(code="CS3L", title="Lab", faculty_id=1, group_id=2, sessions_per_week=1, room_type="lab"),
    ])
    db.commit()

    assignments = generate_schedule(db, optimization_profile="student_first")
    db.add_all([TimetableEntry(**assignment) for assignment in assignments])
    db.add(ScheduleRun(optimization_profile="student_first"))
    db.commit()

    report = build_quality_report(db)
    assert report["generated"] is True
    assert report["profile_label"] == "Student-first"
    assert report["sessions_scheduled"] == 7
    assert report["hard_conflicts"] == 0
    assert report["average_campus_days_per_group"] > 0
    assert 0 <= report["quality_score"] <= 100
    assert set(report["daily_session_load"]) == {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    assert isinstance(report["recommendations"], list) and report["recommendations"]


def test_generator_rejects_unknown_optimization_profile():
    from app.scheduler import SchedulingError
    db = make_db()
    try:
        generate_schedule(db, optimization_profile="magic-ai")
        assert False, "Expected an error for an unsupported optimization profile"
    except SchedulingError as exc:
        assert "Unknown optimization profile" in str(exc)


def test_seeded_demo_exposes_three_distinct_optimization_profiles():
    from app.models import TimeSlot
    from app.seed import seed_database

    db = make_db()
    seed_database(db)
    slots = {slot.id: slot for slot in db.query(TimeSlot).all()}
    allocations = {}
    active_days = {}
    for profile in ["balanced", "student_first", "resource_saver"]:
        assignments = generate_schedule(db, optimization_profile=profile)
        allocations[profile] = tuple(sorted((row["course_id"], row["slot_id"], row["room_id"]) for row in assignments))
        active_days[profile] = {
            group_id: len({slots[row["slot_id"]].day for row in assignments if row["group_id"] == group_id})
            for group_id in {row["group_id"] for row in assignments}
        }
    assert len(set(allocations.values())) == 3
    assert sum(active_days["student_first"].values()) < sum(active_days["balanced"].values())
