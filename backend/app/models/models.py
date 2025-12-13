import datetime
from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: str = Field(unique=True, index=True)
    full_name: str
    email: str = Field(unique=True)
    registration_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    has_submitted: bool = Field(default=False)
    
    assigned_classes: Optional["AssignedClasses"] = Relationship(back_populates="user")
    files: List["File"] = Relationship(back_populates="user")
    submissions: List["Submission"] = Relationship(back_populates="user")
    hidden_test_ids: List["HiddenTestId"] = Relationship(back_populates="user")
    activity_logs: List["ActivityLog"] = Relationship(back_populates="user")

class TP(SQLModel, table=True):
    __tablename__ = 'tps'
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="NLP M1")
    start_time: datetime.datetime
    end_time: datetime.datetime
    grace_minutes: int = Field(default=15)
    max_access_hours: int = Field(default=4)

class AssignedClasses(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    class_1: str
    class_2: str
    class_3: str
    
    user: Optional[User] = Relationship(back_populates="assigned_classes")

class File(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    drive_file_id: str
    file_type: str  # e.g., 'dataset_zip', 'submission_ipynb'
    upload_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    
    user: Optional[User] = Relationship(back_populates="files")
    submission: Optional["Submission"] = Relationship(back_populates="file")

class Submission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    file_id: int = Field(foreign_key="file.id", unique=True)
    submission_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="submissions")
    file: Optional[File] = Relationship(back_populates="submission")

class HiddenTestId(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    original_file_id: int # From the global metadata.csv
    ground_truth_author_id: int

    user: Optional[User] = Relationship(back_populates="hidden_test_ids")

class ActivityLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    activity_type: str # e.g., 'registration', 'submission', 'error'
    details: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="activity_logs")
