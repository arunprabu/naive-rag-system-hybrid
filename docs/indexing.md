# Indexing Documents with Embeddings

This project uses a two-layer indexing approach: embedding-based ingestion into PostgreSQL via `pgvector`, followed by an optional vector index for fast similarity search at scale.

---

## Prerequisites

1. **PostgreSQL** running with the `pgvector` extension enabled:

   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **`.env` file** in the project root:

   ```
   PG_CONNECTION_STRING=postgresql+psycopg://user:password@localhost:5432/yourdb
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_EMBEDDINGS_MODEL=text-embedding-001
   ```

3. **Dependencies installed:**
   ```bash
   uv sync
   ```

---

## Step 1: Run the Ingestion Pipeline

Place your PDF under the `data/` folder, then run:

```bash
PYTHONPATH=. uv run src/ingestion/ingestion.py
```

**What happens internally (`src/ingestion/ingestion.py`):**

| Step   | What it does                                                                     |
| ------ | -------------------------------------------------------------------------------- |
| Load   | `PyPDFLoader` reads the PDF page by page                                         |
| Enrich | Adds metadata: source path, category, page number, last modified                 |
| Chunk  | `RecursiveCharacterTextSplitter` splits into 1000-char chunks (200-char overlap) |
| Embed  | `GoogleGenerativeAIEmbeddings` converts each chunk to a vector                   |
| Store  | `PGVector` saves chunks + vectors into the `hr_support_desk` collection          |

Expected output:

```
Pages: <n>
Chunks: <n>
Ingestion completed successfully!
```

The embedding model and database connection are configured in `src/core/db.py`.

---

## Step 2: Create a Vector Index (Production)

After ingestion, create an `IVFFLAT` index on the embeddings table for fast approximate nearest-neighbor search:

```sql
CREATE INDEX ON langchain_pg_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

> **Note:** Run this SQL once after initial ingestion. Re-run it if you substantially increase the number of documents.

### When is this needed?

| Scenario                     | Recommendation                         |
| ---------------------------- | -------------------------------------- |
| Small dataset (< 10k chunks) | Optional — exact search is fast enough |
| Large dataset (10k+ chunks)  | Required for acceptable query latency  |
| Production deployment        | Always add the index                   |

### Choosing `lists`

A good starting value for `lists` is `sqrt(number_of_rows)`. For example:

- 10,000 chunks → `lists = 100`
- 100,000 chunks → `lists = 316`

---

## Adding a New PDF

1. Copy the PDF into the `data/` folder.
2. Update the file path in `src/ingestion/ingestion.py` (bottom of the file) or call `ingest_pdf("data/your_file.pdf")` directly.
3. Re-run the ingestion command from Step 1.

Note: Also learn about HNSW.
