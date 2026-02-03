from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query in natural language")


class AgentQueryResponse(BaseModel):
    answer: str
    request_id: str
    meta: Dict[str, Any] = Field(default_factory=dict)
