from sqlalchemy.orm import Session
from .models import Course, Faculty, Room, StudentGroup, TimeSlot, User
from .security import hash_password


def seed_database(db: Session) -> None:
    if not db.query(User).filter_by(email="admin@schedwise.dev").first():
        db.add(User(email="admin@schedwise.dev", password_hash=hash_password("Admin@123"), role="admin"))

    if db.query(TimeSlot).count() == 0:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods = [("09:00", "10:00"), ("10:00", "11:00"), ("11:00", "12:00"),
                   ("12:00", "13:00"), ("14:00", "15:00"), ("15:00", "16:00"), ("16:00", "17:00")]
        for day in days:
            for order, (start, end) in enumerate(periods):
                db.add(TimeSlot(day=day, start_time=start, end_time=end, slot_order=order))

    if db.query(Faculty).count() == 0:
        faculty = [
            Faculty(name="Dr. Aditi Sharma", email="aditi@university.edu", max_daily_load=4),
            Faculty(name="Prof. Rahul Mehta", email="rahul@university.edu", max_daily_load=4),
            Faculty(name="Dr. Neha Verma", email="neha@university.edu", max_daily_load=4),
            Faculty(name="Prof. Karan Singh", email="karan@university.edu", max_daily_load=4),
            Faculty(name="Dr. Isha Kapoor", email="isha@university.edu", max_daily_load=4),
        ]
        db.add_all(faculty)
        db.flush()

    if db.query(Room).count() == 0:
        db.add_all([
            Room(name="Room 101", capacity=60, room_type="classroom"),
            Room(name="Room 102", capacity=45, room_type="classroom"),
            Room(name="Room 201", capacity=40, room_type="classroom"),
            Room(name="Computer Lab 1", capacity=35, room_type="lab"),
            Room(name="Computer Lab 2", capacity=50, room_type="lab"),
        ])

    if db.query(StudentGroup).count() == 0:
        db.add_all([
            StudentGroup(name="CSE-A", size=45),
            StudentGroup(name="CSE-B", size=40),
            StudentGroup(name="CSE-C", size=32),
        ])
        db.flush()

    if db.query(Course).count() == 0:
        # Each course belongs to one faculty member and one student group.
        db.add_all([
            Course(code="CS101", title="Programming Fundamentals", faculty_id=1, group_id=1, sessions_per_week=3, room_type="classroom"),
            Course(code="CS102", title="Data Structures & Algorithms", faculty_id=2, group_id=1, sessions_per_week=3, room_type="classroom"),
            Course(code="CS103", title="Database Management Systems", faculty_id=3, group_id=1, sessions_per_week=2, room_type="classroom"),
            Course(code="CS104L", title="Database Systems Lab", faculty_id=3, group_id=1, sessions_per_week=1, room_type="lab"),
            Course(code="CS201", title="Computer Networks", faculty_id=4, group_id=2, sessions_per_week=3, room_type="classroom"),
            Course(code="CS202", title="Cyber Security", faculty_id=5, group_id=2, sessions_per_week=3, room_type="classroom"),
            Course(code="CS203", title="Python Programming", faculty_id=1, group_id=2, sessions_per_week=2, room_type="classroom"),
            Course(code="CS204L", title="Network Security Lab", faculty_id=4, group_id=2, sessions_per_week=1, room_type="lab"),
            Course(code="CS301", title="Cloud Computing", faculty_id=5, group_id=3, sessions_per_week=3, room_type="classroom"),
            Course(code="CS302", title="Software Engineering", faculty_id=2, group_id=3, sessions_per_week=2, room_type="classroom"),
        ])
    db.commit()
