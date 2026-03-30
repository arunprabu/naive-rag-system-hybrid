Note: This example doesn't use agent. It is for demo purpose

# Work on Ingestion

# Work on core/db.py

# apply db.py logic in ingestion

# ======

# Work on schemas/query_schema.py

# Work on routes/query.py

s

# fix for the bad text extraction.

## replace PyPDFLoader with the following

from langchain_community.document_loaders import UnstructuredPDFLoader

loader = UnstructuredPDFLoader(file_path)
docs = loader.load()
