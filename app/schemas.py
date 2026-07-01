from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class HandleMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default-session"
    files: Optional[List[Dict[str, Any]]] = None
    vision_summary: Optional[str] = None


class TicketStatusUpdate(BaseModel):
    status: str


class HandoffStatusUpdate(BaseModel):
    status: str


class RecoveryConversionUpdate(BaseModel):
    conversion_status: str


class RecoveryTouchUpdate(BaseModel):
    touch_status: str


class TaskStatusUpdate(BaseModel):
    status: str
