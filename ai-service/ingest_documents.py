#!/usr/bin/env python3
"""
ingest_documents.py — DPDP Act source document ingestion script.

PURPOSE:
    Loads DPDP Act source documents from the ./documents/ folder,
    chunks them, embeds them with sentence-transformers, and stores
    them in ChromaDB for RAG-grounded AI responses.

IMPORTANT:
    - You must supply your own authoritative DPDP Act source documents.
    - Do NOT place invented or paraphrased legal text here; use only
      official government publications or authoritative legal sources.
    - The AI responses are only as reliable as the documents you provide.
    - This script does NOT guarantee legally accurate AI output.

SUPPORTED FILE FORMATS:
    - .txt (UTF-8 plain text)
    - .md  (Markdown, treated as plain text)

USAGE:
    1. Place your source documents in the ./documents/ folder.
    2. Run:  python ingest_documents.py
    3. Verify with: python -c "from services.chroma_client import ChromaClient; c = ChromaClient(); print(c.collection.count(), 'chunks stored')"

DOCKER:
    When running in Docker, the chroma_data/ volume must be mounted.
    See docker-compose.yml for the volume configuration.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")
SUPPORTED_EXTENSIONS = {".txt", ".md"}


def load_documents(directory: str) -> list[dict]:
    """Load all supported text files from the given directory."""
    if not os.path.isdir(directory):
        logger.error(f"Documents directory not found: {directory}")
        logger.error("Create the ./documents/ folder and add your DPDP source files there.")
        return []

    files = []
    for filename in sorted(os.listdir(directory)):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if not text:
                logger.warning(f"Skipping empty file: {filename}")
                continue
            doc_id = os.path.splitext(filename)[0]
            files.append({
                "doc_id": doc_id,
                "text": text,
                "metadata": {"source": filename, "doc_id": doc_id}
            })
            logger.info(f"Loaded: {filename} ({len(text)} chars)")
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")

    return files


def main():
    logger.info("=== DPDP Act Document Ingestion ===")

    # Import ChromaClient (requires chromadb + sentence-transformers)
    try:
        from services.chroma_client import ChromaClient
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Run: pip install chromadb sentence-transformers")
        sys.exit(1)

    chroma = ChromaClient()
    if not getattr(chroma, '_available', False):
        logger.error("ChromaDB is not available. Check installation.")
        sys.exit(1)

    before_count = chroma.collection.count()
    logger.info(f"ChromaDB currently holds {before_count} chunks.")

    documents = load_documents(DOCUMENTS_DIR)
    if not documents:
        logger.warning("No documents found. Add .txt or .md files to ./documents/")
        logger.warning("RAG will not be active without source documents.")
        sys.exit(0)

    ingested = 0
    for doc in documents:
        try:
            chroma.ingest_document(
                doc_id=doc["doc_id"],
                text=doc["text"],
                metadata=doc["metadata"]
            )
            ingested += 1
        except Exception as e:
            logger.error(f"Failed to ingest {doc['doc_id']}: {e}")

    after_count = chroma.collection.count()
    logger.info(f"Ingestion complete: {ingested}/{len(documents)} documents processed.")
    logger.info(f"ChromaDB now holds {after_count} chunks (was {before_count}).")

    if after_count == 0:
        logger.warning("No chunks were stored. Check that your documents contain text.")


if __name__ == "__main__":
    main()
