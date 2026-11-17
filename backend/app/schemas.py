from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class FacultyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    max_daily_load: int = Field(default=4, ge=1, le=10)
    unavailable_slots: list[int] = Field(default_factory=list)


class RoomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    capacity: int = Field(ge=1, le=500)
    room_type: str = Field(default="classroom", pattern="^(classroom|lab)$")


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    size: int = Field(ge=1, le=500)


class CourseCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    title: str = Field(min_length=2, max_length=160)
    faculty_id: int
    group_id: int
    sessions_per_week: int = Field(default=2, ge=1, le=10)
    room_type: str = Field(default="classroom", pattern="^(classroom|lab)$")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GenerationRequest(BaseModel):
    optimization_profile: str = Field(default="balanced", pattern="^(balanced|student_first|resource_saver)$")
