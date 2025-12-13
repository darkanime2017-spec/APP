"""
Main application file for the FastAPI backend.

This file initializes the FastAPI application, includes the API routers,
and defines any top-level application logic or middleware.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, upload
from app.services.auth_service import initialize_firebase

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_firebase()
    yield

app = FastAPI(
    title="Online TP Platform API",
    description="API for managing online practical works (TPs), submissions, and evaluations.",
    version="0.1.0",
)

# --- Add CORS Middleware ---
# This allows the frontend (running on http://localhost:3000)
# to make requests to the backend.
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.router.lifespan_context = lifespan
# Include the authentication router
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Online TP Platform API!"}