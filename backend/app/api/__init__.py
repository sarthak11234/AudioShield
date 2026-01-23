from app.api.upload import router as upload_router
from app.api.status import router as status_router
from app.api.download import router as download_router

__all__ = ["upload_router", "status_router", "download_router"]
