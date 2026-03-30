from dotenv import load_dotenv
import os
from langchain_community.document_loaders import PyPDFLoader 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.core.db import get_vector_store

load_dotenv()
PG_CONNECTION = os.getenv("PG_CONNECTION_STRING")

def ingest_pdf(file_path):
    """Ingest a PDF file and save it in vector database"""

    # 1. Load PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    print("Pages:", len(docs))

    # 2. Metadata enrichment
    for doc in docs:
        doc.metadata.update({
            "source": file_path,
            "document_extension": "pdf",
            "page": doc.metadata.get("page"),
            "category": "hr_support_desk",
            "last_updated": os.path.getmtime(file_path)
        })

    # 3. Chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(docs)
    print("Chunks:", len(chunks))

    # 4 + 5. Embeddings + Store (delegated to core/db)
    vector_store = get_vector_store(collection_name="hr_support_desk")
  
    vector_store.add_documents(chunks)

    print("Ingestion completed successfully!")


if __name__ == "__main__":
    ingest_pdf("data/HR_Support_Desk_KnowledgeBase.pdf")

# to execute: 
# in windows 
# $env:PYTHONPATH="."; uv run src/ingestion/ingestion.py

# in macOS/Linux
# PYTHONPATH=. uv run src/ingestion/ingestion.py