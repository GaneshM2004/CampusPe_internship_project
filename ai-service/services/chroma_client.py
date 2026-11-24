# =============================================================================
# services/chroma_client.py
# ChromaDB vector store client with persistent storage, repeatable upsert,
# distance filtering, metadata tracking, and corpus versioning for RAG.
# =============================================================================

import hashlib
import logging
import os

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Slices text into chunks of `chunk_size` characters with an `overlap`.
    Returns an empty list for empty or whitespace-only text.
    """
    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    text_length = len(text)

    if text_length <= chunk_size:
        return [text]

    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


class _FakeCollection:
    """Stub collection used when ChromaDB is not installed or fails initialization."""

    def count(self) -> int:
        return 0

    def add(self, **kwargs):
        pass

    def upsert(self, **kwargs):
        pass

    def query(self, **kwargs):
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }


class ChromaClient:
    def __init__(self, persist_dir: str = None):
        if persist_dir:
            data_dir = persist_dir
        elif os.environ.get("CHROMA_DATA_DIR"):
            data_dir = os.environ.get("CHROMA_DATA_DIR")
        else:
            # Locate chroma_data directory relative to ai-service package
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "chroma_data")

        self.persist_dir = data_dir

        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.client.get_or_create_collection(
                name="dpdp_compliance_docs",
                metadata={"hnsw:space": "cosine"}
            )
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
            except Exception:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self._available = True
            logger.info(f"ChromaDB ready — {self.collection.count()} chunks loaded at {self.persist_dir}")

        except ImportError:
            logger.warning("chromadb / sentence-transformers not installed. ChromaDB disabled.")
            self._available = False
            self.collection = _FakeCollection()

        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}. Using stub.")
            self._available = False
            self.collection = _FakeCollection()

    def ingest_document(self, doc_id: str, text: str, metadata: dict = None) -> int:
        """
        Ingest a document using chunking, sentence-transformer embeddings,
        and ChromaDB upsert (safe for repeated runs with stable IDs).
        """
        if not self._available:
            logger.warning("ChromaDB is not available; cannot ingest document.")
            return 0

        chunks = chunk_text(text, chunk_size=500, overlap=50)
        if not chunks:
            return 0

        base_meta = metadata.copy() if metadata else {}
        base_meta.setdefault("source", "manual_ingestion")
        base_meta.setdefault("doc_id", doc_id)

        try:
            embeddings = self.model.encode(chunks).tolist()
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {**base_meta, "chunk_index": i, "chunk_id": ids[i]}
                for i in range(len(chunks))
            ]

            # Use upsert to allow repeatable ingestion without duplicate ID errors
            self.collection.upsert(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully ingested document '{doc_id}' into {len(chunks)} chunks.")
            return len(chunks)
        except Exception as e:
            logger.error(f"ChromaDB ingest error for '{doc_id}': {e}")
            return 0

    def add_document(self, doc_id: str, text: str):
        """Single-document add method kept for backward compatibility."""
        if not self._available:
            return
        try:
            embedding = self.model.encode(text).tolist()
            self.collection.upsert(
                documents=[text],
                embeddings=[embedding],
                metadatas=[{"source": "single_doc", "doc_id": doc_id}],
                ids=[doc_id]
            )
            logger.info(f"ChromaDB: added doc '{doc_id}'")
        except Exception as e:
            logger.error(f"ChromaDB add error: {e}")

    def query(self, question: str, top_k: int = 3, max_distance: float = None) -> list[dict]:
        """
        Retrieve relevant chunks from ChromaDB with distance filtering and metadata.
        Returns a list of dicts: [{"id": ..., "document": ..., "metadata": ..., "distance": ...}]
        """
        if not self._available:
            return []

        doc_count = self.collection.count()
        if doc_count == 0:
            return []

        try:
            k = max(1, min(top_k, doc_count))
            embedding = self.model.encode(question).tolist()
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )

            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            ids = results.get("ids", [[]])[0]
            dists = results.get("distances", [[]])[0] if "distances" in results else [0.0] * len(docs)

            retrieved = []
            for doc, meta, cid, dist in zip(docs, metas, ids, dists):
                d_val = float(dist)
                if max_distance is not None and d_val > max_distance:
                    continue
                retrieved.append({
                    "id": cid,
                    "document": doc,
                    "metadata": meta or {},
                    "distance": d_val
                })

            return retrieved
        except Exception as e:
            logger.error(f"ChromaDB query error: {e}")
            return []

    def get_corpus_version(self) -> str:
        """
        Returns a deterministic version string for the current Chroma collection
        so that Redis caching can accurately invalidate when the corpus changes.
        """
        if not self._available:
            return "unavailable"
        count = self.collection.count()
        if count == 0:
            return "empty"
        return f"v_count_{count}"

    def count(self) -> int:
        """Return the number of items in the collection."""
        if not self._available:
            return 0
        try:
            return self.collection.count()
        except Exception:
            return 0


if __name__ == '__main__':
    test_document = (
        "The Digital Personal Data Protection Act (DPDP Act) of India mandates that Data Fiduciaries "
        "must obtain verifiable parental consent before processing any personal data of a child (a person under 18). "
        "Furthermore, fiduciaries are prohibited from undertaking tracking or behavioral monitoring of children "
        "or targeted advertising directed at children. In the event of a personal data breach, the Data Fiduciary "
        "must intimate the Data Protection Board of India and each affected Data Principal. Penalties for non-compliance "
        "can reach up to 250 crore rupees per instance."
    )

    print("Testing RAG Ingestion Pipeline...")
    client = ChromaClient()
    client.ingest_document(doc_id="dpdp_rule_001", text=test_document, metadata={"category": "children_and_breaches"})
    print(f"Total chunks now stored in ChromaDB: {client.collection.count()}")
