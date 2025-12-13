from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID


class RegisterRequest(BaseModel):
    student_id: str
    full_name: str
    email: EmailStr
    tp_id: int


class RegisterResponse(BaseModel):
    ok: bool = True
    student_id: str
    assigned: List[str]
    drive_zip_id: str


class FileBase(BaseModel):
    path: str
    original_filename: Optional[str] = None
    stored_filename: Optional[str] = None
    file_type: Optional[str] = None
    size_bytes: Optional[int] = None
    user_id: UUID
    tp_id: int

class FileCreate(FileBase):
    github_url: str

class File(FileBase):
    id: UUID
    uploaded_at: datetime

    class Config:
        from_attributes = True


class SubmissionUploadResponse(BaseModel):
    ok: bool = True
    student_id: str
    submission_id: Optional[int] = None
    github_url: Optional[str] = None # Changed from drive_file_id
    path: Optional[str] = None


class StudentLoginRequest(BaseModel):
    student_id: str
    full_name: str


class StudentLoginResponse(BaseModel):
    ok: bool = True
    student_id: str
    full_name: str
    drive_zip_id: Optional[str] = None
    zip_name: Optional[str] = None
    has_submitted: bool = False


class TpResponse(BaseModel):
    tp_id: int
    name: str
    description: str
    start_time: str
    end_time: str
    grace_minutes: int
    max_access_hours: int
