from typing import List, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.sqlalchemy_models import User, Tps, AssignedClass, File, Submission, HiddenTestId, ActivityLog
import datetime

class CRUD:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, student_id: str, full_name: str, email: str) -> User:
        user = User(student_id=student_id, full_name=full_name, email=email)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_by_student_id(self, student_id: str) -> Optional[User]:
        statement = select(User).where(User.student_id == student_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_tp_by_id(self, tp_id: int) -> Optional[Tps]:
        statement = select(Tps).where(Tps.tp_id == tp_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_tp(self, name: str, start_time: datetime.datetime, end_time: datetime.datetime, grace_minutes: int, max_access_hours: int) -> Tps:
        tp = Tps(name=name, start_time=start_time, end_time=end_time, grace_minutes=grace_minutes, max_access_hours=max_access_hours)
        self.session.add(tp)
        await self.session.commit()
        await self.session.refresh(tp)
        return tp

    async def add_assigned_classes(self, tp_id: int, user_id: int, class_1: str, class_2: str, class_3: str) -> AssignedClass:
        assigned_classes = AssignedClass(tp_id=tp_id, user_id=user_id, class_1=class_1, class_2=class_2, class_3=class_3)
        self.session.add(assigned_classes)
        await self.session.commit()
        await self.session.refresh(assigned_classes)
        return assigned_classes

    async def get_assigned_classes(self, tp_id: int, user_id: int) -> Optional[AssignedClass]:
        statement = select(AssignedClass).where(
            AssignedClass.tp_id == tp_id,
            AssignedClass.user_id == user_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def add_file_record(self, user_id: int, drive_file_id: str, file_type: str, path: Optional[str] = None,
                              original_filename: Optional[str] = None, stored_filename: Optional[str] = None,
                              size_bytes: Optional[int] = None, tp_id: Optional[int] = None) -> File:
        file_record = File(
            tp_id=tp_id,
            user_id=user_id,
            drive_file_id=drive_file_id,
            path=path or "",
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=file_type,
            size_bytes=size_bytes,
        )
        self.session.add(file_record)
        await self.session.commit()
        await self.session.refresh(file_record)
        return file_record

    async def get_dataset_file_for_user_tp(self, user_id: int, tp_id: int) -> Optional[File]:
        statement = select(File).where(
            File.user_id == user_id,
            File.tp_id == tp_id,
            File.file_type == "dataset_zip",
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def add_submission_record(self, user_id: int, file_id: int, file_type: str, tp_id: Optional[int] = None) -> Submission:
        submission = Submission(user_id=user_id, file_id=file_id, file_type=file_type, tp_id=tp_id)
        self.session.add(submission)
        # Update user's has_submitted flag only for embeddings submissions
        user = await self.session.get(User, user_id)
        if user and file_type.endswith("embeddings"):
            user.has_submitted = True
            self.session.add(user)
        await self.session.commit()
        await self.session.refresh(submission)
        return submission

    async def add_hidden_test_ids(self, tp_id: int, user_id: int, hidden_ids_data: List[dict]) -> List[HiddenTestId]:
        hidden_test_objects = []
        for item in hidden_ids_data:
            hidden_test = HiddenTestId(
                tp_id=tp_id,
                user_id=user_id,
                text_id=item['text_id'],
                ground_truth=item['ground_truth']
            )
            self.session.add(hidden_test)
            hidden_test_objects.append(hidden_test)
        await self.session.commit()
        for obj in hidden_test_objects:
            await self.session.refresh(obj)
        return hidden_test_objects

    async def add_activity_log(self, user_id: Optional[int], activity_type: str, details: str | dict) -> ActivityLog:
        log = ActivityLog(user_id=user_id, action_key=activity_type, details={"message": details} if isinstance(details, str) else details)
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log
    
    async def update_user_submission_status(self, user_id: int, has_submitted: bool):
        user = await self.session.get(User, user_id)
        if user:
            user.has_submitted = has_submitted
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
