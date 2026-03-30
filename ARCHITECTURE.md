# Project Structure

````src/
  api/
    v1/
      routes/
      services/
      models/
      schemas/
  ingestion/
    ingestion.py
data/
  HR_Support.pdf
main.py
pyproject.toml ```

For production-grade setup, you should eventually:
Add IVFFLAT index for fast similarity search:

````

CREATE INDEX ON langchain_pg_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);```

```

```
