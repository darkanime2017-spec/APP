import os
import zipfile
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.config import settings
from app.services.student_list_service import student_list_service
from app.services.drive_service import GoogleDriveService
from app.services.data_service import DataService
from app.services import github_service # Import the new github_service
from app.crud import CRUD
from app.sqlalchemy_models import Tps, AssignedClass
import re

class RegistrationService:
    def __init__(self, drive_service: GoogleDriveService, data_service: DataService):
        self.drive_service = drive_service
        self.data_service = data_service
        self.drive_data_folder_id: Optional[str] = None # Will be set on first use or app startup
        
    async def login_existing_student(
        self,
        session: AsyncSession,
        student_id: str,
        tp_id: int,
    ) -> dict:
        crud = CRUD(session)

        user = await crud.get_user_by_student_id(student_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Student not registered"
            )

        # Validate TP timing
        tp = await self._validate_tp_timing(crud, tp_id)

        assigned = await crud.get_assigned_classes(tp_id=tp.tp_id, user_id=user.id)
        dataset_file = await crud.get_dataset_file_for_user_tp(
            user_id=user.id, tp_id=tp.tp_id
        )

        if not assigned or not dataset_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student not fully registered for this TP"
            )

        return {
            "ok": True,
            "student_id": user.student_id,
            "full_name": user.full_name,
            "assigned": [assigned.class_1, assigned.class_2, assigned.class_3],
            "drive_zip_id": dataset_file.drive_file_id,
        }

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
        # Respect both max_access_hours and explicit end_time with grace period
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

        # 1. Check for existing user with this student_id
        existing_user = await crud.get_user_by_student_id(student_id)

        # 2. Validate TP timing (always, even for existing users)
        tp = await self._validate_tp_timing(crud, tp_id)

        # Fast path for local development: skip all Google Drive / data generation work.
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

        # If user exists, enforce same email and keep original name
        if existing_user:
            if existing_user.email and existing_user.email != email:
                raise HTTPException(
                    status_code=400,
                    detail="This student ID is already registered with a different email.",
                )

            # Check if assignment and dataset already exist; if so, return them idempotently
            assigned = await crud.get_assigned_classes(tp_id=tp.tp_id, user_id=existing_user.id)
            dataset_file = await crud.get_dataset_file_for_user_tp(user_id=existing_user.id, tp_id=tp.tp_id)
            if assigned and dataset_file:
                return {
                    "ok": True,
                    "student_id": existing_user.student_id,
                    "assigned": [assigned.class_1, assigned.class_2, assigned.class_3],
                    "drive_zip_id": dataset_file.drive_file_id,
                }

        # 3. Sample 4 random authors and prepare student data for new or not-yet-assigned user
        authors = self.data_service.sample_authors(4)
        student_files_df = self.data_service.get_files_for_authors(authors).reset_index(drop=True)
        
        if student_files_df.empty:
            # This case should ideally be rare if metadata.csv is well-formed
            # For robustness, we could re-sample or raise a specific error
            raise HTTPException(status_code=500, detail="Sampled authors have no files associated. Please try again.")

        hidden_test_data = self.data_service.select_hidden_test_ids(student_files_df)
        hidden_file_ids = {item['text_id'] for item in hidden_test_data}

        # Create meta.csv content for the student: id, filepath, label_is_available
        student_meta_df = student_files_df[['FilePath', 'AuthorID']].copy()
        student_meta_df.insert(0, 'id', student_meta_df.index.astype(int))
        student_meta_df['label_is_available'] = student_meta_df['id'].apply(
            lambda x: 0 if x in hidden_file_ids else 1
        )
        # Ensure no ground truth labels are included in the student's meta.csv
        student_meta_df = student_meta_df.drop(columns=['AuthorID']) 

        # 4. Create temporary directory, assemble data, and upload zip to Google Drive
        temp_dir = tempfile.mkdtemp()
        zip_file_path = None
        try:
            student_data_root = os.path.join(temp_dir, f"{student_id}_{self._sanitize_name(full_name)}")
            os.makedirs(student_data_root, exist_ok=True)

            # Write student's meta.csv
            student_meta_csv_path = os.path.join(student_data_root, "meta.csv")
            student_meta_df.to_csv(student_meta_csv_path, index=False)

            # Locate the 'data' folder under the NLP_M1 root in the Shared Drive
            drive_data_folder_id = await self._get_drive_data_folder_id()

            # For each author, create a folder and download their files
            for author_name in authors:
                author_folder_path = os.path.join(student_data_root, author_name)
                os.makedirs(author_folder_path, exist_ok=True)

                # Files for this author in the student slice
                author_files_df = student_files_df[student_files_df['Author'] == author_name]

                # Find the Drive folder ID for this author within the 'data' folder
                drive_author_folder_id = await self.drive_service.find_item_id_by_name(
                    drive_data_folder_id, author_name, is_folder=True
                )
                if not drive_author_folder_id:
                    raise HTTPException(status_code=500, detail=f"Google Drive author folder '{author_name}' not found.")

                for _, row in author_files_df.iterrows():
                    file_name = row['FileName']
                    drive_file_id = await self.drive_service.find_item_id_by_name(
                        drive_author_folder_id, file_name, is_folder=False
                    )
                    if not drive_file_id:
                        print(f"Warning: File {file_name} not found in Drive for author {author_name}. Skipping.")
                        continue

                    file_content = await self.drive_service.download_file_by_id(drive_file_id)
                    with open(os.path.join(author_folder_path, file_name), 'wb') as f:
                        f.write(file_content)

            # Create the zip file
            zip_filename = f"{student_id}_{self._sanitize_name(full_name)}_data.zip"
            zip_base = os.path.join(tempfile.gettempdir(), zip_filename.replace('.zip', ''))
            shutil.make_archive(zip_base, 'zip', student_data_root)
            zip_file_path = f"{zip_base}.zip"

            # Upload zip to Drive under NLP_M1/students/<student_id>_<name>/data.zip
            students_folder_id = await self.drive_service.ensure_folder(
                settings.DRIVE_ROOT_FOLDER_ID, "students"
            )
            student_drive_folder_id = await self.drive_service.ensure_folder(
                students_folder_id, f"{student_id}_{self._sanitize_name(full_name)}"
            )

            drive_zip_id = await self.drive_service.upload_file_to_folder(
                student_drive_folder_id, zip_file_path, "data.zip"
            )

            # 6. Persist to Postgres
            if existing_user:
                user = existing_user
            else:
                user = await crud.create_user(student_id=student_id, full_name=full_name, email=email)
            # Store first 3 classes in DB; the 4th is still included in the data package.
            await crud.add_assigned_classes(tp_id=tp.tp_id, user_id=user.id, class_1=authors[0], class_2=authors[1], class_3=authors[2])
            await crud.add_file_record(user_id=user.id, drive_file_id=drive_zip_id, file_type="dataset_zip", tp_id=tp.tp_id,
                                       path=f"students/{student_id}_{self._sanitize_name(full_name)}/data.zip",
                                       original_filename="data.zip", stored_filename="data.zip")
            await crud.add_hidden_test_ids(tp_id=tp.tp_id, user_id=user.id, hidden_ids_data=hidden_test_data)
            await crud.add_activity_log(user_id=user.id, activity_type="registration", details=f"Student {student_id} registered with authors: {', '.join(authors)}")

            return {
                "ok": True,
                "student_id": student_id,
                "assigned": authors,
                "drive_zip_id": drive_zip_id
            }
        except HTTPException as e:
            await crud.add_activity_log(user_id=None, activity_type="error", details=f"Registration failed for {student_id}: {e.detail}")
            raise e
        except Exception as e:
            # Log the unexpected error and potentially re-raise
            print(f"An unexpected error occurred during registration for {student_id}: {e}")
            await crud.add_activity_log(user_id=None, activity_type="error", details=f"Unexpected error during registration for {student_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred during registration.")
        finally:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except PermissionError:
                    # On Windows, files can remain locked briefly; ignore cleanup failures.
                    pass
            if zip_file_path and os.path.exists(zip_file_path):
                try:
                    os.remove(zip_file_path)
                except PermissionError:
                    # Ignore if the OS still has a handle open; it will be cleaned up later.
                    pass

    async def login_existing_student(self, crud: CRUD, student_id: str, full_name: str) -> Dict[str, Any]:
        """Logs in a student using pre-generated ZIPs in Drive.

        Expects files under NLP_M1/students/<FULL_NAME>/<FULL_NAME>_books.zip.
        """
        # Validate that this full_name exists in students_list.csv
        if not student_list_service.is_valid_full_name(full_name):
            raise HTTPException(status_code=400, detail="Unknown student full name.")
        # Ensure user exists or create one
        existing_user = await crud.get_user_by_student_id(student_id)
        if existing_user:
            user = existing_user
        else:
            user = await crud.create_user(student_id=student_id, full_name=full_name, email=None)

        # Locate the student's folder in the Shared Drive
        students_folder_id = await self.drive_service.ensure_folder(
            settings.DRIVE_ROOT_FOLDER_ID, "students"
        )

        student_drive_folder_id = await self.drive_service.find_item_id_by_name(
            students_folder_id, full_name, is_folder=True
        )
        if not student_drive_folder_id:
            raise HTTPException(status_code=404, detail="Student folder not found in Drive.")

        zip_name = f"{full_name}_books.zip"
        drive_zip_id = await self.drive_service.find_item_id_by_name(
            student_drive_folder_id, zip_name, is_folder=False
        )
        if not drive_zip_id:
            raise HTTPException(status_code=404, detail="Student ZIP file not found in Drive.")

        # Optionally record a file record / activity for auditing (no TP context here)
        await crud.add_activity_log(
            user_id=user.id,
            activity_type="login",
            details=f"Student {student_id} logged in and ZIP {zip_name} located.",
        )

        return {
            "ok": True,
            "student_id": user.student_id,
            "full_name": user.full_name,
            "drive_zip_id": drive_zip_id,
            "zip_name": zip_name,
            "has_submitted": user.has_submitted,
        }

    async def get_student_zip_bytes(self, crud: CRUD, student_id: str) -> bytes:
        """Fetches the pre-generated ZIP bytes for a student from Drive."""
        user = await crud.get_user_by_student_id(student_id)
        if not user:
            raise HTTPException(status_code=404, detail="Student not found.")

        students_folder_id = await self.drive_service.find_item_id_by_name(
            settings.DRIVE_ROOT_FOLDER_ID, "students", is_folder=True
        )
        if not students_folder_id:
            raise HTTPException(status_code=404, detail="'students' folder not found in Drive.")

        student_drive_folder_id = await self.drive_service.find_item_id_by_name(
            students_folder_id, user.full_name, is_folder=True
        )
        if not student_drive_folder_id:
            raise HTTPException(status_code=404, detail="Student folder not found in Drive.")

        zip_name = f"{user.full_name}_books.zip"
        drive_zip_id = await self.drive_service.find_item_id_by_name(
            student_drive_folder_id, zip_name, is_folder=False
        )
        if not drive_zip_id:
            raise HTTPException(status_code=404, detail="Student ZIP file not found in Drive.")

        return await self.drive_service.download_file_by_id(drive_zip_id)

    async def get_student_meta_csv(self, crud: CRUD, student_id: str) -> Optional[bytes]:
        """
        Retrieves the meta.csv content for a given student from Drive.
        """
        user = await crud.get_user_by_student_id(student_id)
        if not user:
            raise HTTPException(status_code=404, detail="Student not found.")

        students_folder_id = await self.drive_service.find_item_id_by_name(
            settings.DRIVE_ROOT_FOLDER_ID, "students", is_folder=True
        )
        if not students_folder_id:
            raise HTTPException(status_code=500, detail="Google Drive 'students' folder not found.")

        student_drive_folder_id = await self.drive_service.find_item_id_by_name(
            students_folder_id, f"{student_id}_{self._sanitize_name(user.full_name)}", is_folder=True
        )
        if not student_drive_folder_id:
            raise HTTPException(status_code=404, detail="Student's Drive folder not found.")

        data_zip_id = await self.drive_service.find_item_id_by_name(
            student_drive_folder_id, "data.zip", is_folder=False
        )
        if not data_zip_id:
            raise HTTPException(status_code=404, detail="Student's data.zip not found.")

        zip_bytes = await self.drive_service.download_file_by_id(data_zip_id)
        
        # Extract meta.csv from the zip file in memory
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as z:
            # Assuming meta.csv is at the root of the student's data folder within the zip
            # e.g., student_id_fullname/meta.csv
            
            # Find the actual path to meta.csv inside the zip
            meta_csv_name = None
            for name in z.namelist():
                if name.endswith('meta.csv'):
                    meta_csv_name = name
                    break
            
            if meta_csv_name:
                return z.read(meta_csv_name)
            else:
                raise HTTPException(status_code=500, detail="meta.csv not found inside student's data.zip.")

    async def upload_submission(self, session: AsyncSession, student_id: str, file_content_bytes: bytes, file_type: str, original_filename: str, tp_id: int) -> Dict[str, Any]:
        crud = CRUD(session)

        # 1. Validate user and submission status
        user = await crud.get_user_by_student_id(student_id)
        if not user:
            raise HTTPException(status_code=404, detail="Student not found.")

        # If the student has already made a final submission, block any further uploads.
        if user.has_submitted:
            raise HTTPException(status_code=400, detail="Student has already submitted their final work.")

        # 2. Enforce strict file extension rules
        name_lower = (original_filename or "").lower()
        # Any "ipynb*" type must be a notebook file
        if file_type.startswith("ipynb") and not name_lower.endswith(".ipynb"):
            raise HTTPException(status_code=400, detail="File must be a .ipynb notebook.")
        if file_type == "embeddings" and not name_lower.endswith(".txt"):
            raise HTTPException(status_code=400, detail="Embedding file must be a .txt file.")

        # 3. Prepare file for GitHub upload
        sanitized_full_name = self._sanitize_name(user.full_name)
        # Choose a distinct prefix per kind so files don't overwrite each other
        if file_type.startswith("ipynb"):
            if "textprocess" in file_type:
                base_prefix = "textprocess"
            elif "classifier" in file_type:
                base_prefix = "classifier"
            else:
                base_prefix = "notebook"
            new_filename = f"{base_prefix}_{student_id}_{sanitized_full_name}.ipynb"
        elif file_type == "embeddings":
            base_prefix = "embeddings"
            new_filename = f"{base_prefix}_{student_id}_{sanitized_full_name}.txt"
        else:
            # Fallback: use original filename if type is unexpected
            base_prefix = "file"
            new_filename = original_filename or f"{base_prefix}_{student_id}_{sanitized_full_name}"
        
        github_file_path = f"{student_id}_{sanitized_full_name}/{new_filename}"
        commit_message = f"Add {file_type} for TP by {user.full_name}"

        github_upload_result = await github_service.upload_file_to_github(
            file_path_in_repo=github_file_path,
            file_content=file_content_bytes,
            commit_message=commit_message,
        )

        if not github_upload_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to GitHub.",
            )
        
        # 4. Save metadata to database. We store the GitHub URL in the existing drive_file_id column
        # to avoid changing the current database schema.
        await crud.add_file_record(
            user_id=user.id,
            drive_file_id=github_upload_result["content"]["html_url"],
            file_type=file_type,
            path=github_file_path,
            original_filename=original_filename,
            stored_filename=new_filename,
            size_bytes=len(file_content_bytes),
            tp_id=tp_id
        )
        
        await crud.add_activity_log(
            user_id=user.id,
            activity_type="submission",
            details=f"Student {student_id} submitted {new_filename} (saved to GitHub)",
        )

        # Mark final submission when embeddings are uploaded
        if file_type == "embeddings":
            await crud.update_user_submission_status(user.id, True)

        return {
            "ok": True,
            "student_id": student_id,
            "github_url": github_upload_result["content"]["html_url"],
            "path": github_file_path # Keep for compatibility if frontend expects it
        }

# This instance will be initialized at application startup
# registration_service = RegistrationService(drive_service, data_service)
