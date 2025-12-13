import os
import zipfile
import io
import shutil
import tempfile
# import pandas as pd  # Commented out as requested
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.config import settings
from app.services.student_list_service import student_list_service
from app.services.drive_service import GoogleDriveService
from app.services.data_service import DataService
from app.services import github_service  # Import the new github_service
from app.crud import CRUD
from app.sqlalchemy_models import Tps, AssignedClass
import re

class RegistrationService:
    def __init__(self, drive_service: GoogleDriveService, data_service: DataService):
        self.drive_service = drive_service
        self.data_service = data_service
        self.drive_data_folder_id: Optional[str] = None  # Will be set on first use or app startup

    async def _get_drive_data_folder_id(self) -> str:
        if not self.drive_data_folder_id:
            if settings.DRIVE_ROOT_FOLDER_ID is None:
                raise HTTPException(status_code=500, detail="DRIVE_ROOT_FOLDER_ID is not configured in .env")
            self.drive_data_folder_id = await self.drive_service.find_item_id_by_name(
                settings.DRIVE_ROOT_FOLDER_ID, "data", is_folder=True
            )
            if not self.drive_data_folder_id:
                raise HTTPException(status_code=500, detail="Google Drive 'data' folder not found.")
        return self.drive_data_folder_id

    def _sanitize_name(self, name: str) -> str:
        """Sanitizes full_name for use in folder names."""
        s = re.sub(r'[^\w\s-]', '', name).strip()
        s = re.sub(r'[-\s]+', '_', s)
        return s

    async def _validate_tp_timing(self, crud: CRUD, tp_id: int) -> Tps:
        tp = await crud.get_tp_by_id(tp_id)
        if not tp:
            raise HTTPException(status_code=404, detail="TP (Training Period) not found.")

        current_time = datetime.now(timezone.utc)
        allowed_start_time = tp.start_time
        max_access_end = tp.start_time + timedelta(hours=tp.max_access_hours)
        hard_end = tp.end_time + timedelta(minutes=tp.grace_minutes)
        allowed_end_time = min(max_access_end, hard_end)

        if not (allowed_start_time <= current_time <= allowed_end_time):
            raise HTTPException(
                status_code=400,
                detail=f"Registration is only allowed between {allowed_start_time.isoformat()} and {allowed_end_time.isoformat()} UTC."
            )
        return tp

    async def register_student(self, session: AsyncSession, student_id: str, full_name: str, email: str, tp_id: int) -> Dict[str, Any]:
        crud = CRUD(session)

        existing_user = await crud.get_user_by_student_id(student_id)
        tp = await self._validate_tp_timing(crud, tp_id)

        if getattr(settings, "DISABLE_DRIVE_IN_DEV", False):
            if existing_user:
                user = existing_user
            else:
                user = await crud.create_user(student_id=student_id, full_name=full_name, email=email)

            await crud.add_activity_log(
                user_id=user.id,
                activity_type="registration_dev",
                details="Registration completed in dev mode without Drive integration.",
            )

            return {
                "ok": True,
                "student_id": user.student_id,
                "assigned": [],
                "drive_zip_id": None,
            }

        if existing_user:
            if existing_user.email and existing_user.email != email:
                raise HTTPException(
                    status_code=400,
                    detail="This student ID is already registered with a different email.",
                )

            assigned = await crud.get_assigned_classes(tp_id=tp.tp_id, user_id=existing_user.id)
            dataset_file = await crud.get_dataset_file_for_user_tp(user_id=existing_user.id, tp_id=tp.tp_id)
            if assigned and dataset_file:
                return {
                    "ok": True,
                    "student_id": existing_user.student_id,
                    "assigned": [assigned.class_1, assigned.class_2, assigned.class_3],
                    "drive_zip_id": dataset_file.drive_file_id,
                }

        # 3. Sample 4 random authors and prepare student data (no pandas)
        authors = self.data_service.sample_authors(4)
        student_files_list = self.data_service.get_files_for_authors(authors)  # List of dicts

        if not student_files_list:
            raise HTTPException(status_code=500, detail="Sampled authors have no files associated. Please try again.")

        hidden_test_data = self.data_service.select_hidden_test_ids(student_files_list)
        hidden_file_ids = {item['text_id'] for item in hidden_test_data}

        # Create meta.csv content without pandas
        meta_csv_lines = ["id,FilePath,label_is_available"]
        for idx, row in enumerate(student_files_list):
            label = 0 if idx in hidden_file_ids else 1
            meta_csv_lines.append(f"{idx},{row['FilePath']},{label}")

        temp_dir = tempfile.mkdtemp()
        zip_file_path = None
        try:
            student_data_root = os.path.join(temp_dir, f"{student_id}_{self._sanitize_name(full_name)}")
            os.makedirs(student_data_root, exist_ok=True)

            student_meta_csv_path = os.path.join(student_data_root, "meta.csv")
            with open(student_meta_csv_path, "w", encoding="utf-8") as f:
                f.write("\n".join(meta_csv_lines))

            drive_data_folder_id = await self._get_drive_data_folder_id()

            for author_name in authors:
                author_folder_path = os.path.join(student_data_root, author_name)
                os.makedirs(author_folder_path, exist_ok=True)
                author_files_list = [f for f in student_files_list if f['Author'] == author_name]

                drive_author_folder_id = await self.drive_service.find_item_id_by_name(
                    drive_data_folder_id, author_name, is_folder=True
                )
                if not drive_author_folder_id:
                    raise HTTPException(status_code=500, detail=f"Google Drive author folder '{author_name}' not found.")

                for file_row in author_files_list:
                    file_name = file_row['FileName']
                    drive_file_id = await self.drive_service.find_item_id_by_name(
                        drive_author_folder_id, file_name, is_folder=False
                    )
                    if not drive_file_id:
                        print(f"Warning: File {file_name} not found in Drive for author {author_name}. Skipping.")
                        continue

                    file_content = await self.drive_service.download_file_by_id(drive_file_id)
                    with open(os.path.join(author_folder_path, file_name), 'wb') as f:
                        f.write(file_content)

            zip_filename = f"{student_id}_{self._sanitize_name(full_name)}_data.zip"
            zip_base = os.path.join(tempfile.gettempdir(), zip_filename.replace('.zip', ''))
            shutil.make_archive(zip_base, 'zip', student_data_root)
            zip_file_path = f"{zip_base}.zip"

            students_folder_id = await self.drive_service.ensure_folder(
                settings.DRIVE_ROOT_FOLDER_ID, "students"
            )
            student_drive_folder_id = await self.drive_service.ensure_folder(
                students_folder_id, f"{student_id}_{self._sanitize_name(full_name)}"
            )

            drive_zip_id = await self.drive_service.upload_file_to_folder(
                student_drive_folder_id, zip_file_path, "data.zip"
            )

            if existing_user:
                user = existing_user
            else:
                user = await crud.create_user(student_id=student_id, full_name=full_name, email=email)

            await crud.add_assigned_classes(tp_id=tp.tp_id, user_id=user.id,
                                            class_1=authors[0], class_2=authors[1], class_3=authors[2])
            await crud.add_file_record(user_id=user.id, drive_file_id=drive_zip_id, file_type="dataset_zip",
                                       tp_id=tp.tp_id,
                                       path=f"students/{student_id}_{self._sanitize_name(full_name)}/data.zip",
                                       original_filename="data.zip", stored_filename="data.zip")
            await crud.add_hidden_test_ids(tp_id=tp.tp_id, user_id=user.id, hidden_ids_data=hidden_test_data)
            await crud.add_activity_log(user_id=user.id, activity_type="registration",
                                        details=f"Student {student_id} registered with authors: {', '.join(authors)}")

            return {
                "ok": True,
                "student_id": student_id,
                "assigned": authors,
                "drive_zip_id": drive_zip_id
            }
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            if zip_file_path and os.path.exists(zip_file_path):
                os.remove(zip_file_path)
