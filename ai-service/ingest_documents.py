#!/usr/bin/env python3
"""
ingest_documents.py — DPDP Act PDF and source document ingestion engine.

PURPOSE:
    Loads DPDP Act source documents (PDF, TXT, MD) from ./documents/,
    extracts text preserving page numbers and section headers,
    chunks them using paragraph-aware splitting with overlap,
    embeds them with sentence-transformers, and stores them in ChromaDB
    with deterministic chunk IDs and verified legal metadata.

LEGAL NOTICE:
    Informational assistance only. This pipeline ingests authoritative or
    locally supplied PDF source files to ground RAG responses. It does NOT
    guarantee legal correctness or eliminate LLM hallucinations.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from typing import List, Dict, Any, Tuple

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dpdp_ingest")

DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
MANIFEST_PATH = os.path.join(DOCUMENTS_DIR, "corpus_manifest.json")
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def compute_file_sha256(filepath: str) -> str:
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> Dict[str, Any]:
    """Load corpus_manifest.json if it exists."""
    if os.path.isfile(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not read manifest at {MANIFEST_PATH}: {e}")
    return {"documents": []}


def chunk_page_text(text: str, max_chars: int = 700, overlap: int = 100) -> List[str]:
    """
    Splits text into chunks preserving paragraph structure where possible.
    Includes character overlap across chunk boundaries.
    """
    if not text or not text.strip():
        return []

    # Split by double-newline or large paragraph breaks
    raw_paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    paragraphs = []

    for p in raw_paragraphs:
        if len(p) <= max_chars:
            paragraphs.append(p)
        else:
            # Split oversized paragraph by sentence or window
            start = 0
            while start < len(p):
                end = start + max_chars
                paragraphs.append(p[start:end].strip())
                start += max_chars - overlap

    chunks = []
    current_chunk = ""

    for p in paragraphs:
        if not current_chunk:
            current_chunk = p
        elif len(current_chunk) + len(p) + 2 <= max_chars:
            current_chunk += "\n\n" + p
        else:
            chunks.append(current_chunk)
            tail = current_chunk[-overlap:] if len(current_chunk) > overlap else ""
            current_chunk = (tail + "\n\n" + p).strip() if tail else p

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def extract_pdf_document(filepath: str, doc_id: str, title: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts pages from a PDF, detects section headers, and chunks text.
    Returns (chunks, extraction_stats).
    """
    if PdfReader is None:
        raise RuntimeError("Neither pypdf nor PyPDF2 is installed. Run: pip install pypdf")

    filename = os.path.basename(filepath)
    file_hash = compute_file_sha256(filepath)
    reader = PdfReader(filepath)

    if getattr(reader, "is_encrypted", False):
        raise ValueError(f"PDF {filename} is encrypted/password-protected.")

    total_pages = len(reader.pages)
    chunks = []
    current_section = "General"
    total_chars = 0
    empty_pages = []

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        raw_text = page.extract_text() or ""
        stripped_raw = raw_text.strip()

        if not stripped_raw:
            empty_pages.append(page_num)
            continue

        total_chars += len(stripped_raw)
        lines = raw_text.splitlines()
        cleaned_lines = []

        for line in lines:
            line_str = line.strip()
            # Remove repeated Gazette headers safely without altering legal text
            if re.match(r'^(THE\s+GAZETTE\s+OF\s+INDIA|\d+\s+THE\s+GAZETTE|\[भाग|\[PART)', line_str, re.IGNORECASE):
                continue
            if re.match(r'^(UPLOADED BY|Uploaded by|MGIPMRND)', line_str, re.IGNORECASE):
                continue

            # Detect chapter, section, or rule heading
            if re.match(r'^CHAPTER\s+[IVXLCDM]+', line_str, re.IGNORECASE):
                current_section = line_str[:80].strip()
            elif re.match(r'^\d+\.\s+([A-Z][a-zA-Z\s]{2,50}|[a-zA-Z\s]{2,50})\s*[—\.\-]', line_str):
                current_section = line_str[:80].strip()
            elif re.match(r'^\d+\.\s+\(\d+\)', line_str):
                current_section = line_str[:60].strip()

            cleaned_lines.append(line)

        page_content = "\n".join(cleaned_lines).strip()
        page_chunks = chunk_page_text(page_content, max_chars=700, overlap=100)

        for c_idx, c_text in enumerate(page_chunks):
            chunk_id = f"{doc_id}_p{page_num}_c{c_idx}"
            chunk_hash = hashlib.sha256(c_text.encode("utf-8")).hexdigest()[:16]

            chunks.append({
                "id": chunk_id,
                "document": c_text,
                "metadata": {
                    "doc_id": doc_id,
                    "source": filename,
                    "title": title,
                    "page": page_num,
                    "section": current_section,
                    "text_hash": chunk_hash,
                    "chunk_id": chunk_id,
                    "file_sha256": file_hash
                }
            })

    stats = {
        "filename": filename,
        "doc_id": doc_id,
        "file_hash": file_hash,
        "total_pages": total_pages,
        "empty_pages": empty_pages,
        "total_chars": total_chars,
        "chunks_created": len(chunks)
    }

    return chunks, stats


def extract_text_document(filepath: str, doc_id: str, title: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Extracts and chunks plain text or markdown files."""
    filename = os.path.basename(filepath)
    file_hash = compute_file_sha256(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = []
    text_chunks = chunk_page_text(text, max_chars=700, overlap=100)

    for c_idx, c_text in enumerate(text_chunks):
        chunk_id = f"{doc_id}_p1_c{c_idx}"
        chunk_hash = hashlib.sha256(c_text.encode("utf-8")).hexdigest()[:16]

        chunks.append({
            "id": chunk_id,
            "document": c_text,
            "metadata": {
                "doc_id": doc_id,
                "source": filename,
                "title": title,
                "page": 1,
                "section": "General",
                "text_hash": chunk_hash,
                "chunk_id": chunk_id,
                "file_sha256": file_hash
            }
        })

    stats = {
        "filename": filename,
        "doc_id": doc_id,
        "file_hash": file_hash,
        "total_pages": 1,
        "empty_pages": [] if text.strip() else [1],
        "total_chars": len(text),
        "chunks_created": len(chunks)
    }

    return chunks, stats


def ingest_all(reset: bool = False) -> Dict[str, Any]:
    """
    Main ingestion execution:
    1. Scans ./documents/ for supported files
    2. Cross-references with corpus_manifest.json
    3. Chunks with legal section tracking
    4. Cleans up stale chunks and upserts to ChromaDB
    """
    from services.chroma_client import ChromaClient
    chroma = ChromaClient()

    if not getattr(chroma, "_available", False):
        raise RuntimeError("ChromaDB is not initialized or unavailable.")

    if reset:
        logger.info("Resetting entire ChromaDB collection before ingestion...")
        chroma.reset_collection()

    manifest = load_manifest()
    manifest_by_filename = {doc.get("filename"): doc for doc in manifest.get("documents", [])}

    if not os.path.isdir(DOCUMENTS_DIR):
        logger.error(f"Documents directory not found at: {DOCUMENTS_DIR}")
        return {"status": "error", "message": "Documents directory missing"}

    files = sorted([
        f for f in os.listdir(DOCUMENTS_DIR)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
        and not f.lower().startswith("readme")
    ])

    if not files:
        logger.warning(f"No documents found in {DOCUMENTS_DIR}. Supported: {SUPPORTED_EXTENSIONS}")
        return {"status": "empty", "files_found": 0}

    logger.info(f"Found {len(files)} document(s) in {DOCUMENTS_DIR}")

    all_stats = []
    total_chunks_stored = 0

    for filename in files:
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        ext = os.path.splitext(filename)[1].lower()

        # Look up metadata from manifest or derive default
        manifest_meta = manifest_by_filename.get(filename, {})
        doc_id = manifest_meta.get("doc_id", os.path.splitext(filename)[0].lower())
        title = manifest_meta.get("title", filename)

        logger.info(f"Processing: {filename} (doc_id: '{doc_id}')")

        try:
            if ext == ".pdf":
                chunks, stats = extract_pdf_document(filepath, doc_id, title)
            else:
                chunks, stats = extract_text_document(filepath, doc_id, title)

            # Purge stale chunks for this specific document before upserting
            chroma.delete_document(doc_id)

            # Upsert all newly extracted chunks
            ingested_count = chroma.ingest_chunks(chunks)
            stats["chunks_ingested"] = ingested_count
            total_chunks_stored += ingested_count
            all_stats.append(stats)

            logger.info(
                f"Ingested '{filename}': {stats['total_pages']} pages, "
                f"{stats['total_chars']} chars -> {ingested_count} chunks"
            )

        except Exception as e:
            logger.error(f"Failed to ingest {filename}: {e}", exc_info=True)

    final_collection_count = chroma.count()
    corpus_version = chroma.get_corpus_version()

    result = {
        "status": "success",
        "documents_processed": len(all_stats),
        "total_chunks_stored": total_chunks_stored,
        "chromadb_collection_count": final_collection_count,
        "corpus_version": corpus_version,
        "document_stats": all_stats
    }

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DPDP Act Document Ingestion")
    parser.add_argument("--reset", action="store_true", help="Wipe and recreate collection before ingestion")
    args = parser.parse_args()

    summary = ingest_all(reset=args.reset)
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY:")
    print(json.dumps(summary, indent=2))
    print("=" * 60)
