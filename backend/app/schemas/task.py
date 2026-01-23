from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class TaskCreate(BaseModel):
    original_name: str

class TaskResponse(BaseModel):
    id: UUID
    original_name: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class TaskStatus(BaseModel):
    id: UUID
    status: str
    progress: Optional[str] = None
