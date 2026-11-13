# Source Documents for RAG

This folder must contain authoritative DPDP Act source documents before ChromaDB
RAG retrieval can provide grounded AI responses.

## ⚠️ Important Disclaimer

- Do NOT place invented, paraphrased, or AI-generated legal text here.
- Use only official government publications or authoritative legal sources.
- AI responses are grounded by these documents but are NOT guaranteed to be
  legally accurate. This tool does not provide legal advice.

## What to Place Here

Suggested sources (obtain from official Indian government portals):

- The Digital Personal Data Protection Act, 2023 (official text)
- DPDP Act Rules (once notified by the Government of India)
- Data Protection Board of India guidance documents (when published)

## Supported Formats

- `.txt` — UTF-8 plain text
- `.md`  — Markdown (treated as plain text)

## How to Ingest

After placing documents here, run from the `ai-service/` directory:

```bash
python ingest_documents.py
```

Verify ingestion:

```bash
python -c "from services.chroma_client import ChromaClient; c = ChromaClient(); print(c.collection.count(), 'chunks stored')"
```

## Without Documents

The AI service will still function (it uses the LLM without RAG context),
but responses will not be grounded in authoritative DPDP Act text.
The `/health` endpoint will report `chromadb_docs: 0`.
