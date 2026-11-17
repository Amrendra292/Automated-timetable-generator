import csv
import io
import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, APIRouter, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .database import Base, engine, get_db, SessionLocal
from .models import Course, Faculty, Room, ScheduleRun, StudentGroup, TimeSlot, TimetableEntry, User
from .schemas import LoginRequest, FacultyCreate, RoomCreate, GroupCreate, CourseCreate, GenerationRequest
from .security import verify_password, create_access_token, get_current_user
from .seed import seed_database
from .scheduler import generate_schedule, SchedulingError
from .analytics import build_quality_report


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="SchedWise API",
    description="Explainable multi-objective university timetable generation and quality audit API.",
    version="2.0.0",
    lifespan=lifespan,
)
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "schedwise-api"}


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role}}


api = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


def safe_commit(db: Session, message: str = "A record with this value already exists"):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=message)


def entry_payload(db: Session, entry: TimetableEntry) -> dict:
    course = db.get(Course, entry.course_id)
    faculty = db.get(Faculty, entry.faculty_id)
    group = db.get(StudentGroup, entry.group_id)
    room = db.get(Room, entry.room_id)
    slot = db.get(TimeSlot, entry.slot_id)
    return {
        "id": entry.id,
        "course_id": entry.course_id,
        "course_code": course.code,
        "course_title": course.title,
        "faculty_id": entry.faculty_id,
        "faculty_name": faculty.name,
        "group_id": entry.group_id,
        "group_name": group.name,
        "room_id": entry.room_id,
        "room_name": room.name,
        "slot_id": entry.slot_id,
        "day": slot.day,
        "start_time": slot.start_time,
        "end_time": slot.end_time,
        "slot_order": slot.slot_order,
        "room_type": room.room_type,
    }


@api.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}


@api.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    return {
        "courses": db.query(Course).count(),
        "faculty": db.query(Faculty).count(),
        "rooms": db.query(Room).count(),
        "groups": db.query(StudentGroup).count(),
        "scheduled_sessions": db.query(TimetableEntry).count(),
        "weekly_sessions_required": db.query(func.sum(Course.sessions_per_week)).scalar() or 0,
    }


@api.get("/faculty")
def list_faculty(db: Session = Depends(get_db)):
    return [{"id": x.id, "name": x.name, "email": x.email, "max_daily_load": x.max_daily_load, "unavailable_slots": x.unavailable_slots or []} for x in db.query(Faculty).order_by(Faculty.name).all()]


@api.post("/faculty", status_code=201)
def create_faculty(payload: FacultyCreate, db: Session = Depends(get_db)):
    item = Faculty(**payload.model_dump())
    db.add(item)
    safe_commit(db, "A faculty member with this email already exists")
    db.refresh(item)
    return {"id": item.id, "name": item.name, "email": item.email, "max_daily_load": item.max_daily_load, "unavailable_slots": item.unavailable_slots or []}


@api.get("/rooms")
def list_rooms(db: Session = Depends(get_db)):
    return [{"id": x.id, "name": x.name, "capacity": x.capacity, "room_type": x.room_type} for x in db.query(Room).order_by(Room.name).all()]


@api.post("/rooms", status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    item = Room(**payload.model_dump())
    db.add(item)
    safe_commit(db, "A room with this name already exists")
    db.refresh(item)
    return {"id": item.id, "name": item.name, "capacity": item.capacity, "room_type": item.room_type}


@api.get("/groups")
def list_groups(db: Session = Depends(get_db)):
    return [{"id": x.id, "name": x.name, "size": x.size} for x in db.query(StudentGroup).order_by(StudentGroup.name).all()]


@api.post("/groups", status_code=201)
def create_group(payload: GroupCreate, db: Session = Depends(get_db)):
    item = StudentGroup(**payload.model_dump())
    db.add(item)
    safe_commit(db, "A student group with this name already exists")
    db.refresh(item)
    return {"id": item.id, "name": item.name, "size": item.size}


@api.get("/courses")
def list_courses(db: Session = Depends(get_db)):
    items = db.query(Course).order_by(Course.code).all()
    return [{
        "id": x.id, "code": x.code, "title": x.title, "faculty_id": x.faculty_id,
        "faculty_name": db.get(Faculty, x.faculty_id).name,
        "group_id": x.group_id, "group_name": db.get(StudentGroup, x.group_id).name,
        "sessions_per_week": x.sessions_per_week, "room_type": x.room_type,
    } for x in items]


@api.post("/courses", status_code=201)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    if not db.get(Faculty, payload.faculty_id):
        raise HTTPException(status_code=400, detail="Select an existing faculty member")
    if not db.get(StudentGroup, payload.group_id):
        raise HTTPException(status_code=400, detail="Select an existing student group")
    item = Course(**payload.model_dump())
    db.add(item)
    safe_commit(db, "A course with this code already exists")
    db.refresh(item)
    return {"id": item.id, "code": item.code, "title": item.title, "faculty_id": item.faculty_id, "group_id": item.group_id, "sessions_per_week": item.sessions_per_week, "room_type": item.room_type}


@api.get("/slots")
def list_slots(db: Session = Depends(get_db)):
    return [{"id": x.id, "day": x.day, "start_time": x.start_time, "end_time": x.end_time, "slot_order": x.slot_order} for x in db.query(TimeSlot).order_by(TimeSlot.slot_order, TimeSlot.day).all()]


@api.get("/timetable")
def get_timetable(group_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(TimetableEntry)
    if group_id is not None:
        query = query.filter(TimetableEntry.group_id == group_id)
    entries = query.all()
    return [entry_payload(db, x) for x in entries]


@api.get("/analytics/quality")
def timetable_quality(db: Session = Depends(get_db)):
    return build_quality_report(db)


@api.post("/timetable/generate")
def create_timetable(payload: GenerationRequest | None = None, db: Session = Depends(get_db)):
    profile = payload.optimization_profile if payload else "balanced"
    try:
        assignments = generate_schedule(db, optimization_profile=profile)
    except SchedulingError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "diagnostics": exc.diagnostics})
    db.query(TimetableEntry).delete()
    db.query(ScheduleRun).delete()
    db.add_all([TimetableEntry(**assignment) for assignment in assignments])
    db.add(ScheduleRun(optimization_profile=profile))
    db.commit()
    entries = db.query(TimetableEntry).all()
    quality = build_quality_report(db, profile)
    return {"message": "Timetable generated successfully", "scheduled_sessions": len(entries), "optimization_profile": profile, "quality": quality, "entries": [entry_payload(db, x) for x in entries]}


@api.delete("/timetable", status_code=204)
def clear_timetable(db: Session = Depends(get_db)):
    db.query(TimetableEntry).delete()
    db.query(ScheduleRun).delete()
    db.commit()
    return None


@api.get("/timetable/export.csv")
def export_timetable(db: Session = Depends(get_db)):
    entries = [entry_payload(db, x) for x in db.query(TimetableEntry).all()]
    if not entries:
        raise HTTPException(status_code=404, detail="Generate a timetable before exporting")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["day", "start_time", "end_time", "group_name", "course_code", "course_title", "faculty_name", "room_name"])
    writer.writeheader()
    for entry in sorted(entries, key=lambda x: (x["slot_order"], x["day"], x["group_name"])):
        writer.writerow({key: entry[key] for key in writer.fieldnames})
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=schedwise-timetable.csv"})


app.include_router(api)
