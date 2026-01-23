from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload_router, status_router, download_router

app = FastAPI(
    title="AudioShield API",
    description="AI Voice Cloning Protection Service",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)
app.include_router(status_router)
app.include_router(download_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "audioshield"}
