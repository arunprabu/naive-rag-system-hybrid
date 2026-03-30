import re
from src.core.db import get_vector_store
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

# PGVector connection string uses SQLAlchemy format: postgresql+psycopg://...
# psycopg.connect needs standard format: postgresql://...
_raw_conn = os.getenv("PG_CONNECTION_STRING", "").replace("postgresql+psycopg", "postgresql")

# Patterns that signal a precise keyword lookup is needed
_KEYWORD_PATTERNS = [
    r"[A-Z]{2,}-\d{4}-\w+",   # policy/ticket codes: POL-2024-HR-007
    r"\b[A-Z]{2,5}\b",         # short uppercase abbreviations: LTA, CTC, ESI
    r"\d{6,}",                 # long numeric IDs / employee numbers
]
_KEYWORD_RE = re.compile("|".join(_KEYWORD_PATTERNS))


def _detect_mode(query: str) -> str:
    stripped = query.strip()
    # if the keyword patterns match anywhere in the query, 
    # we prioritize FTS search to find exact matches
    if _KEYWORD_RE.search(stripped): 
        return "keyword"
    
    # if the query is short (3 words or fewer), 
    # we treat it as a hybrid case to balance precision and recall
    if len(stripped.split()) <= 3:
        return "hybrid"

    # if the query is long and doesn't match keyword patterns, 
    # we assume it's a natural language question best served by vector search
    return "vector"


# vector search
def query_documents(query: str, k: int = 5) -> list[dict]:
    mode = _detect_mode(query)

    if mode == "keyword":
        return fts_search(query, k=k)

    if mode == "hybrid":
        return _hybrid_search(query, k=k)

    # vector — long natural-language question
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(query, k=k)
    return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]

# fts search
def fts_search(query: str, k: int = 5, collection_name: str = "hr_support_desk") -> list[dict]:
    """
    Keyword search against stored chunks using PostgreSQL tsvector / tsquery / ts_rank.

    Args:
        query:           User query string (plain text, any format)
        k:               Number of top results to return
        collection_name: PGVector collection to search

    Returns:
        List of dicts with 'content', 'metadata', and 'fts_rank'
    """
    sql = """
        SELECT
            e.document                                               AS content,
            e.cmetadata                                              AS metadata,
            ts_rank(
                to_tsvector('english', e.document),
                plainto_tsquery('english', %(query)s)
            )                                                        AS fts_rank
        FROM  langchain_pg_embedding  e
        JOIN  langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = %(collection)s
          AND to_tsvector('english', e.document)
              @@ plainto_tsquery('english', %(query)s)
        ORDER BY fts_rank DESC
        LIMIT %(k)s;
    """
    with psycopg.connect(_raw_conn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"query": query, "collection": collection_name, "k": k})
            rows = cur.fetchall()

    return [
        {
            "content":  row["content"],
            "metadata": row["metadata"],
            "fts_rank": round(float(row["fts_rank"]), 4),
        }
        for row in rows
    ]

# hybrid search
def _hybrid_search(query: str, k: int = 5) -> list[dict]:
    """
    Merge vector and FTS results using Reciprocal Rank Fusion (RRF).

    RRF score for a chunk = sum of 1/(rank + 60) across both result lists.
    Chunks appearing in both lists score higher than those in only one.
    The constant 60 prevents top-ranked outliers from dominating.
    """
    vector_store = get_vector_store()
    vector_docs = vector_store.similarity_search(query, k=k)
    fts_docs    = fts_search(query, k=k)

    rrf_scores: dict[str, float] = {}
    chunk_map:  dict[str, dict]  = {}

    for rank, doc in enumerate(vector_docs):
        key = doc.page_content[:120]
        rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (60 + rank + 1)
        chunk_map[key]  = {"content": doc.page_content, "metadata": doc.metadata}

    for rank, item in enumerate(fts_docs):
        key = item["content"][:120]
        rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (60 + rank + 1)
        chunk_map[key]  = {"content": item["content"], "metadata": item["metadata"]}

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [chunk_map[key] for key, _ in ranked[:k]]