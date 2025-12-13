from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Form
from pydantic import BaseModel
from fastapi.responses import Response
from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session
from app.schemas import RegisterRequest, RegisterResponse, SubmissionUploadResponse, StudentLoginRequest, StudentLoginResponse, TpResponse
from app.services.drive_service import drive_service as google_drive_service
from app.services.student_list_service import student_list_service
from app.services.data_service import DataService
from app.services.registration_service import RegistrationService
from app.crud import CRUD
from app.sqlalchemy_models import User
from sqlmodel import select

router = APIRouter()

# Initialize services (this will be done once at application startup in main.py)
# For now, we define them here for dependency injection
data_service = DataService(google_drive_service)
registration_service = RegistrationService(google_drive_service, data_service)

# Dependency to get CRUD operations instance
async def get_crud(session: AsyncSession = Depends(get_session)) -> CRUD:
    return CRUD(session)

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
    crud: CRUD = Depends(get_crud)
):
    """
    Registers a new student, assigns authors, prepares data, uploads to Drive,
    and records details in the database.
    """
    return await registration_service.register_student(
        session, request.student_id, request.full_name, request.email, request.tp_id
    )

@router.post("/student/login", response_model=StudentLoginResponse, status_code=status.HTTP_200_OK)
async def student_login(
    request: StudentLoginRequest,
    crud: CRUD = Depends(get_crud),
):
    """Logs in a student using an existing pre-generated ZIP in Drive."""
    return await registration_service.login_existing_student(
        crud, request.student_id, request.full_name
    )


@router.get("/tp/{tp_id}", response_model=TpResponse)
async def get_tp(tp_id: int, crud: CRUD = Depends(get_crud)):
    """Returns TP information (timing, description) from the database."""
    tp = await crud.get_tp_by_id(tp_id)
    if not tp:
        raise HTTPException(status_code=404, detail="TP not found.")

    return TpResponse(
        tp_id=tp.tp_id,
        name=tp.name,
        description=tp.description or "",
        start_time=tp.start_time.isoformat(),
        end_time=tp.end_time.isoformat(),
        grace_minutes=tp.grace_minutes,
        max_access_hours=tp.max_access_hours,
    )


@router.get("/student/list", response_model=list[str])
async def get_student_list(session: AsyncSession = Depends(get_session)):
    """Returns all valid student full names from students_list.csv, excluding those who already submitted."""
    all_names = student_list_service.get_all_full_names()

    stmt = select(User.full_name, User.has_submitted)
    result = await session.execute(stmt)
    rows = result.all()
    submitted_names = {row[0] for row in rows if row[1]}

    return [name for name in all_names if name not in submitted_names]

@router.get("/student/{student_id}/meta")
async def get_student_meta(
    student_id: str,
    crud: CRUD = Depends(get_crud)
):
    """
    Returns the student's meta.csv content.
    """
    meta_csv_content = await registration_service.get_student_meta_csv(crud, student_id)
    if not meta_csv_content:
        raise HTTPException(status_code=404, detail="Student meta.csv not found or could not be generated.")
    
    return Response(content=meta_csv_content, media_type="text/csv")


@router.get("/student/{student_id}/zip")
async def download_student_zip(
    student_id: str,
    crud: CRUD = Depends(get_crud),
):
    """Downloads the student's pre-generated ZIP file from Drive."""
    zip_bytes = await registration_service.get_student_zip_bytes(crud, student_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=student_{student_id}.zip"
        },
    )

@router.post("/upload-submission", response_model=SubmissionUploadResponse, status_code=status.HTTP_200_OK)
async def upload_submission(
    tp_id: int = Form(...), # Added tp_id
    student_id: str = Form(...),
    file_type: str = Form(..., description="Type of file: 'ipynb' or 'embeddings'"),
    file: UploadFile = FastAPIFile(...),
    session: AsyncSession = Depends(get_session),
    crud: CRUD = Depends(get_crud)
):
    """
    Uploads a student's submission (ipynb or embeddings file) to GitHub,
    enforcing time windows and single submission per student.
    """
    # Allow any file_type that starts with 'ipynb' (for multiple notebook kinds) or is exactly 'embeddings'.
    if not (file_type == "embeddings" or file_type.startswith("ipynb")):
        raise HTTPException(status_code=400, detail="Invalid file_type. Must be 'ipynb*' or 'embeddings'.")
    
    file_content = await file.read()
    
    return await registration_service.upload_submission(
        session, student_id, file_content, file_type, file.filename, tp_id # Pass tp_id
    )

@router.post("/upload", response_model=SubmissionUploadResponse, status_code=status.HTTP_200_OK)
async def upload_legacy(
    tp_id: int = Form(...), # Added tp_id
    student_id: str = Form(...),
    file_type: str = Form(..., description="Type of file: 'ipynb' or 'embeddings'"),
    file: UploadFile = FastAPIFile(...),
    session: AsyncSession = Depends(get_session),
    crud: CRUD = Depends(get_crud),
):
    """Compatibility endpoint for the frontend calling POST /api/upload.

    Internally delegates to the same logic as /upload-submission.
    """
    # Allow any file_type that starts with 'ipynb' (for multiple notebook kinds) or is exactly 'embeddings'.
    if not (file_type == "embeddings" or file_type.startswith("ipynb")):
        raise HTTPException(status_code=400, detail="Invalid file_type. Must be 'ipynb*' or 'embeddings'.")

    file_content = await file.read()

    return await registration_service.upload_submission(
        session, student_id, file_content, file_type, file.filename, tp_id # Pass tp_id
    )

class FirebaseLoginPayload(BaseModel):
    firebase_uid: str
    student_id: str
    full_name: str
    email: str


@router.post("/auth/firebase_login")
async def firebase_login_stub(payload: FirebaseLoginPayload):
    """Development stub for Firebase login.

    Echoes back a user-like object so the frontend can store it.
    """
    return {
        "firebase_uid": payload.firebase_uid,
        "student_id": payload.student_id,
        "full_name": payload.full_name,
        "email": payload.email,
    }
