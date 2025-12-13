# backend/app/main.py
import os
import logging
import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import engine
from app.sqlalchemy_models import Base
from app.api.endpoints import router
from app.services.drive_service import drive_service as google_drive_service
from app.services.data_service import DataService
from app.services.registration_service import RegistrationService
from app.crud import CRUD

# ----- service instances -----
data_service_instance = DataService(google_drive_service)
registration_service_instance = RegistrationService(google_drive_service, data_service_instance)

# ----- logging tweaks -----
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)  # reduce SQLAlchemy noise
logger = logging.getLogger(__name__)

# ----- CORS origins from env (comma-separated) -----
# Default now points to your deployed frontend
# Example: FRONTEND_ORIGINS="https://front-8w36ml0b7-tareks-projects-e887ddd8.vercel.app"
origins_env = os.getenv(
    "FRONTEND_ORIGINS", 
    "https://front-8w36ml0b7-tareks-projects-e887ddd8.vercel.app"
)
CORS_ORIGINS = [u.strip() for u in origins_env.split(",") if u.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")

    # Initialize DataService metadata (Drive)
    from app.api import endpoints as api_endpoints

    await data_service_instance.load_metadata()
    await api_endpoints.data_service.load_metadata()
    logger.info("Metadata loaded from Google Drive.")

    # Create/check DB tables (dev / initial setup)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/checked.")

    # Insert a sample TP for testing if one doesn't exist
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        crud = CRUD(session)
        sample_tp = await crud.get_tp_by_id(1)
        if not sample_tp:
            start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
            end_time = start_time + datetime.timedelta(days=1)
            await crud.create_tp(
                name="NLP Test TP",
                start_time=start_time,
                end_time=end_time,
                grace_minutes=15,
                max_access_hours=4,
            )
            logger.info("Sample TP created in database.")

    yield
    logger.info("Application shutdown.")

# ----- FastAPI app -----
app = FastAPI(
    title="NLP TP Platform API",
    version="1.0.0",
    description="API for NLP TP student registration, data assignment, and submission.",
    lifespan=lifespan,
)

# ----- CORS middleware -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- include API routes first so /api gets handled by router ----- 
app.include_router(router, prefix="/api")

# ----- health & root endpoints -----
@app.get("/healthz", include_in_schema=False, status_code=status.HTTP_200_OK)
async def healthz():
    return {"status": "ok"}

@app.head("/healthz", include_in_schema=False, status_code=status.HTTP_200_OK)
async def healthz_head():
    return Response(status_code=200)

@app.head("/", include_in_schema=False)
async def root_head():
    return Response(status_code=200)

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to the NLP TP Platform API"}

# ----- mount static React build if present ----- 
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info(f"Serving frontend static files from: {static_dir}")
else:
    logger.info(f"No static frontend found at {static_dir} — API only.")

# ----- dependency overrides so endpoints can use the same instances ----- 
app.dependency_overrides[DataService] = lambda: data_service_instance
app.dependency_overrides[RegistrationService] = lambda: registration_service_instance

# ----- run with uvicorn when executed directly (helps local dev) ----- 
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    reload_flag = os.environ.get("DEV_RELOAD", "false").lower() in ("1", "true", "yes")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload_flag)
