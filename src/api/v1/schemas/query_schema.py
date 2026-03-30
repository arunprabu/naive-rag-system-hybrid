from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# ---- Request ----
class QueryRequest(BaseModel):
    query: str = Field(..., description="User query")
    # k: int = Field(default=5, ge=1, le=20, description="Top-k results")
    category: Optional[str] = Field(
        default=None,
        description="Optional metadata filter (e.g., hr_support_desk)"
    )

# ---- Result Chunk ----
class QueryResult(BaseModel):
    content: str
    metadata: Dict[str, Any]

# ---- Response ----
class QueryResponse(BaseModel):
    query: str
    results: List[QueryResult]