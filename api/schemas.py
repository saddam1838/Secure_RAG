from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class QueryRequest(BaseModel):
    query: str
    filters: Optional[dict] = None

class QueryResponse(BaseModel):
    response: str
    sources: List[str]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict]] = None

class ChatResponse(BaseModel):
    reply: str
    blocked: bool = False
    reason: Optional[str] = None

class ScanResponse(BaseModel):
    is_safe: bool
    filename: str
    size_mb: float
    issues: List[Dict]
    message: str

class MessageResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
