from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.sqlalchemy_models import Base
from app.api.endpoints import router
from app.services.drive_service import drive_service as google_drive_service
from app.services.data_service import DataService
from app.services.registration_service import RegistrationService
import datetime
from app.crud import CRUD

# Global instances of services (used locally; endpoints module has its own instances)
data_service_instance = DataService(google_drive_service)
registration_service_instance = RegistrationService(google_drive_service, data_service_instance)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup...")
    
    # Initialize DataService instances (load metadata from Drive)
    from app.api import endpoints as api_endpoints

    await data_service_instance.load_metadata()
    await api_endpoints.data_service.load_metadata()
    print("Metadata loaded from Google Drive.")

    # Create database tables (for development/initial setup)
    # In a production environment, you would use Alembic for migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/checked.")

    # Insert a sample TP for testing if one doesn't exist
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        crud = CRUD(session)
        sample_tp = await crud.get_tp_by_id(1)
        if not sample_tp:
            # Example TP: valid for 24 hours from now, max access 4 hours, 15 min grace
            start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)  # Start 30 min ago
            end_time = start_time + datetime.timedelta(days=1)  # End 1 day from start
            await crud.create_tp(
                name="NLP Test TP",
                start_time=start_time,
                end_time=end_time,
                grace_minutes=15,
                max_access_hours=4,
            )
            print("Sample TP created in database.")
        
    yield
    print("Application shutdown.")

app = FastAPI(
    title="NLP TP Platform API",
    version="1.0.0",
    description="API for NLP TP student registration, data assignment, and submission.",
    lifespan=lifespan,
)

# CORS settings for frontend
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to the NLP TP Platform API"}

# Make service instances available via FastAPI's dependency injection system if needed elsewhere
app.dependency_overrides[DataService] = lambda: data_service_instance
app.dependency_overrides[RegistrationService] = lambda: registration_service_instance
