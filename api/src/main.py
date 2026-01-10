from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import engine, init_db
from api_v2_simple import app as api_v2_app

# Import models from __init__.py to ensure they're registered with Base
from datagod.models import Jurisdiction, DataSource, Record, Entity, Relationship

# Create database tables using the correct Base
init_db()

# Create main FastAPI app
main_app = FastAPI(
    title="DataGod API",
    version="2.0.0",
    description="API for DataGod - Public Records Data Aggregation Platform"
)

# Add CORS middleware
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v2 sub-application
main_app.mount("/api/v2", api_v2_app)

# Root endpoint
@main_app.get("/")
async def root():
    return {
        "message": "DataGod API is running",
        "version": "2.0.0",
        "documentation": "/docs",
        "api_v2": "/api/v2"
    }

# Health check endpoint
@main_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "api_version": "2.0.0",
        "message": "DataGod API v2 is operational"
    }
