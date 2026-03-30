from fastapi import APIRouter
from src.api.v1.services.query_service import query_documents
from src.api.v1.schemas.query_schema import QueryRequest, QueryResponse

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    # will connect to query_service to get results based on query type

    results = query_documents(request.query, 5)
    return QueryResponse(query=request.query, results=results)
