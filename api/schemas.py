from pydantic import BaseModel
from typing import Optional, List


class QueryRequest(BaseModel):
    query: str
    filters: Optional[dict] = None


class QueryResponse(BaseModel):
    response: str
    sources: List[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
