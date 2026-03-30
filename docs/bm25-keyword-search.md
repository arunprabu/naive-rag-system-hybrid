# Keyword Search with PostgreSQL Full-Text Search

## Why Is Keyword Search Needed When We Already Have Vector Search?

This is the most important question to answer before writing any code.

### What Vector Search Does

Vector search converts the query and documents into numerical embeddings and finds chunks whose embeddings are geometrically closest to the query embedding. It captures **meaning and intent**, not literal words.

For example, a query like _"time off policy"_ will successfully retrieve a chunk that says _"employees are entitled to annual leave"_ — even though none of the query words appear in the chunk. That's the strength of semantic search.

### Where Vector Search Fails

**1. Exact term matching**

Embeddings compress meaning. In that compression, specific tokens — especially rare ones — lose their precision. Consider:

- HR policy code `"POL-2024-HR-007"` → the embedding model has never seen this token pattern. It will be mapped to a generic region of the vector space.
- Employee name `"Rajesh Subramaniam"` → same problem.
- Product abbreviation `"LTA"` (Leave Travel Allowance) → the model may conflate it with unrelated things.

A user querying for `"POL-2024-HR-007"` expects that exact string to match. Vector search cannot guarantee this.

**2. Keyword specificity**

Consider two chunks:

- Chunk A: _"Employees can apply for casual leave through the HR portal"_
- Chunk B: _"The HR department oversees all employee benefits and wellness programs"_

For the query _"casual leave application"_, both chunks may have similar embedding distances because they share the domain context (HR, employees). But only Chunk A is correct. Keyword search would rank Chunk A first because it contains the exact terms.

**3. Negation and boolean logic**

Vector search has no concept of `NOT`. A query _"leave policy excluding maternity"_ cannot exclude maternity-related chunks in pure vector space. SQL's `tsquery` supports `!` (NOT) natively.

**4. Recall vs precision**

Vector search optimizes for **recall** — it will almost always return something. But for factual, policy-driven Q&A (like this HR support desk), **precision** matters more. Returning a plausible-but-wrong chunk is worse than returning nothing.

### The Right Mental Model

Think of them as two complementary filters:

```
User Query
    │
    ├──► Vector Search  →  "What does this query MEAN?"  →  semantic matches
    │
    └──► FTS (keyword)  →  "What exact WORDS appear?"   →  precise term matches
              │
              └──► Combine both with RRF → Hybrid Search (best of both)
```

Neither alone is sufficient. Together they cover each other's blind spots.

---

## How PostgreSQL FTS Works

### `tsvector` — the indexed form of a document

PostgreSQL preprocesses each document into a `tsvector`: stop words are removed, remaining words are stemmed to their root form, and each term is stored with its position in the text.

```sql
SELECT to_tsvector('english', 'Employees must submit leave requests via the HR portal');
-- Result: 'employ':1 'hr':8 'leav':5 'portal':9 'request':6 'submit':3
-- "must", "via", "the" are stop words → removed
-- "Employees" → stemmed to "employ"
-- "requests" → stemmed to "request"
```

### `tsquery` — the search expression

A `tsquery` is compiled from the user's input and matched against a `tsvector` using the `@@` operator.

```sql
-- plainto_tsquery: plain text input, terms joined with AND automatically
SELECT plainto_tsquery('english', 'leave request');
-- Result: 'leav' & 'request'

-- to_tsquery: explicit boolean operators
SELECT to_tsquery('english', 'leave & !maternity');
-- Result: 'leav' & !'matern'  (leave but NOT maternity)

-- websearch_to_tsquery: Google-style, safe for raw user input
SELECT websearch_to_tsquery('english', '"casual leave" -maternity');
```

### `ts_rank` — the relevance score

Scores how well a document matches the query, based on term frequency and — optionally — how close the matching terms are to each other.

```sql
SELECT ts_rank(to_tsvector('english', document), plainto_tsquery('english', 'leave request')) AS rank
```

Use `ts_rank_cd` (cover density) when term **proximity** matters — it gives higher scores when query terms appear adjacent in the document.

---

## PGVector Table Structure

LangChain's PGVector stores chunks in two tables (already exist after ingestion):

```
langchain_pg_collection  (id, name, cmetadata)
langchain_pg_embedding   (id, collection_id, embedding, document, cmetadata)
```

The `document` column holds raw chunk text. FTS runs entirely against this column — no schema changes needed.

---

## Implementation Steps

### Step 1 — Add GIN Index (run once after ingestion)

A GIN (Generalized Inverted Index) pre-computes the `tsvector` for every row, making FTS queries fast instead of doing a full table scan.

```sql
CREATE INDEX ON langchain_pg_embedding
USING GIN (to_tsvector('english', document));
```

Run this once in your database after the first ingestion. Re-running is safe (Postgres will skip if index already exists using `CREATE INDEX IF NOT EXISTS`).

---

### Step 2 — Create `src/retrieval/fts_retriever.py`

> **Note on the connection string:** `PGVector` uses the SQLAlchemy format (`postgresql+psycopg://...`). Raw `psycopg` needs the standard format (`postgresql://...`). Strip the `+psycopg` driver prefix before connecting.

```python
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

# PGVector connection string uses SQLAlchemy format: postgresql+psycopg://...
# psycopg.connect needs standard format: postgresql://...
_raw_conn = os.getenv("PG_CONNECTION_STRING", "").replace("postgresql+psycopg", "postgresql")


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
        JOIN  langchain_pg_collection c ON c.id = e.collection_id
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
```

---

### Step 3 — Update `src/api/v1/services/query_service.py`

The retrieval strategy is determined **automatically** from the query — no `mode` field is exposed in the API. Users just send their query as usual.

#### How auto-detection works

```
Has code / ID / uppercase abbreviation?  →  keyword  (exact lookup needed)
Short query (1–3 words)?                 →  hybrid   (ambiguous, use both signals)
Long natural-language question?          →  vector   (semantic intent dominates)
```

```python
import re
from src.core.db import get_vector_store
from src.retrieval.fts_retriever import fts_search

# Patterns that signal a precise keyword lookup is needed
_KEYWORD_PATTERNS = [
    r"[A-Z]{2,}-\d{4}-\w+",   # policy/ticket codes: POL-2024-HR-007
    r"\b[A-Z]{2,5}\b",         # short uppercase abbreviations: LTA, CTC, ESI
    r"\d{6,}",                 # long numeric IDs / employee numbers
]
_KEYWORD_RE = re.compile("|".join(_KEYWORD_PATTERNS))


def _detect_mode(query: str) -> str:
    stripped = query.strip()
    if _KEYWORD_RE.search(stripped):
        return "keyword"
    if len(stripped.split()) <= 3:
        return "hybrid"
    return "vector"


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
```

#### Examples of auto-detected mode

| Query                                                 | Detected mode | Reason                         |
| ----------------------------------------------------- | ------------- | ------------------------------ |
| `"POL-2024-HR-007"`                                   | `keyword`     | matches code pattern           |
| `"LTA"`                                               | `keyword`     | short uppercase abbreviation   |
| `"casual leave"`                                      | `hybrid`      | 2 words, no special pattern    |
| `"How do I apply for annual leave in the HR portal?"` | `vector`      | long natural-language sentence |

---

## Choosing the Right `tsquery` Function

| Function               | Input style                                 | Use when                             |
| ---------------------- | ------------------------------------------- | ------------------------------------ |
| `plainto_tsquery`      | Plain text — any user input                 | Default; never throws a syntax error |
| `to_tsquery`           | Explicit operators (`&`, `\|`, `!`, `:*`)   | Programmatic / structured queries    |
| `websearch_to_tsquery` | Google-style (`"exact phrase"`, `-exclude`) | Web search UX                        |

`plainto_tsquery` is the safest choice for user-facing input.

---

## Summary: When to Use What

| Scenario                                 | Use                                   |
| ---------------------------------------- | ------------------------------------- |
| _"What is the annual leave policy?"_     | Vector — semantic question            |
| _"POL-2024-HR-007"_                      | Keyword — exact code lookup           |
| _"How do I apply for casual leave?"_     | Hybrid — has both intent and keywords |
| _"Leave policy not including maternity"_ | Keyword — boolean NOT needed          |
| General-purpose HR Q&A                   | Hybrid (recommended default)          |

---

## Production Notes

- The GIN index (Step 1) is the single most impactful performance step. Without it, every FTS query scans the entire `langchain_pg_embedding` table.
- Use `ts_rank_cd` instead of `ts_rank` when term **adjacency** matters (e.g., _"leave request"_ should score higher than a chunk with "leave" and "request" far apart).
- The RRF constant `60` is the widely accepted default from the original RRF paper. Increase it to reduce the dominance of top-ranked results.
