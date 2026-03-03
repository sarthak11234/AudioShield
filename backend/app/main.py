from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload_router, status_router, download_router, auth_router
from app.core.database import engine, Base
from app.models import Task, User  # Import to register models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="AudioShield API",
    description="AI Voice Cloning Protection Service",
    version="0.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(status_router)
app.include_router(download_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "audioshield"}

