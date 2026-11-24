# Knowledge Base Source Documents for DPDP RAG

This directory stores source documents used to populate the ChromaDB vector database for RAG-grounded responses in the DPDP Act Compliance Centre.

---

## ⚠️ Important Legal & Authenticity Disclaimer

- **Informational Assistance Only:** Ingestion of documents into ChromaDB grounds AI responses with factual reference passages, but **does not guarantee legal accuracy** or regulatory compliance. AI output is not a substitute for qualified legal advice.
- **Provenance & Verification:** Ingestion of a file does **not** prove its legal authenticity. All documents indexed in `corpus_manifest.json` are recorded with `source_authority_status: "unverified_local_file"` until official publication URLs (such as `egazette.gov.in`) or certifying authority metadata are independently confirmed.
- **No Fabricated Content:** Never place invented, paraphrased, or AI-generated legal text in this directory.

---

## Supported File Formats

1. **PDF (`.pdf`)**:
   - Requires `pypdf` (installed via `requirements.txt`).
   - Digital vector PDFs are processed page-by-page. Scanned or image-only PDFs without OCR text layers are detected and skipped with warnings.
   - Repeated Gazette publication headers and footers are cleanly stripped without altering statutory text, numbering, or legal meaning.
2. **Plain Text (`.txt`) & Markdown (`.md`)**:
   - UTF-8 encoded text files.
   - Paragraph-split into grounded chunks.

---

## Metadata & Traceability

Every ingested chunk stored in ChromaDB contains verified traceability metadata:
- `doc_id`: Unique document identifier (e.g., `dpdp_act_2023`, `dpdp_rules_2025`).
- `source`: Source filename (e.g., `DPDP_ACT_2023.pdf`).
- `title`: Document title recorded in `corpus_manifest.json`.
- `page`: Exact document page number ($1$-indexed).
- `section`: Detected statutory section, chapter, or rule heading (e.g., `Section 9. Processing of data of children`).
- `file_sha256`: Cryptographic SHA-256 checksum of the source file.
- `text_hash`: SHA-256 checksum of the chunk text.
- `chunk_id`: Deterministic ID format: `{doc_id}_p{page_num}_c{chunk_index}`.

---

## Ingestion Instructions

### Ingesting PDF Documents
1. Ensure `pypdf` is installed (`pip install -r requirements.txt`).
2. Verify or add document entry in `corpus_manifest.json`.
3. Run the ingestion command from the `ai-service/` directory:
   ```bash
   cd ai-service
   python ingest_documents.py
   ```

### Ingesting TXT / MD Documents
1. Place `.txt` or `.md` files in this directory.
2. Run the same ingestion command:
   ```bash
   cd ai-service
   python ingest_documents.py
   ```

### Verification Command
Verify the number of chunks loaded into ChromaDB:
```bash
python -c "from services.chroma_client import ChromaClient; c=ChromaClient(); print(c.count())"
```

### Idempotency & Re-indexing
Rerunning `python ingest_documents.py` is **fully idempotent**:
- Existing chunks for re-indexed documents are purged prior to upsert.
- Unchanged documents retain stable chunk IDs without creating duplicates.
- To perform a complete database wipe and rebuild from scratch, use:
  ```bash
  python ingest_documents.py --reset
  ```

---

## Behavior Without Documents

If no source documents are present or ChromaDB is unavailable:
- The AI service operates in **ungrounded fallback mode**.
- Every response returns `grounded: false`, empty citations (`[]`), and an explicit ungrounded disclaimer.
- If `REQUIRE_GROUNDING=true` is set, endpoints safely reject ungrounded queries with HTTP `422 Unprocessable Entity`.
