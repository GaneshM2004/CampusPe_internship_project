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

    def delete(self, **kwargs):
        pass

    def get(self, **kwargs):
        return {"ids": [], "documents": [], "metadatas": []}

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

    def ingest_chunks(self, chunks: list[dict], batch_size: int = 64) -> int:
        """
        Ingests pre-constructed chunk dicts:
        each dict must have 'id', 'document', and 'metadata'.
        Uses upsert with batching.
        """
        if not self._available or not chunks:
            return 0

        total_ingested = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_docs = [c["document"] for c in batch]
            batch_ids = [c["id"] for c in batch]
            batch_metas = [c["metadata"] for c in batch]

            try:
                batch_embeddings = self.model.encode(batch_docs).tolist()
                self.collection.upsert(
                    documents=batch_docs,
                    embeddings=batch_embeddings,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
                total_ingested += len(batch)
            except Exception as e:
                logger.error(f"ChromaDB batch ingest error at offset {i} (batch size {len(batch)}): {e}")

        logger.info(f"Successfully ingested {total_ingested} chunks.")
        return total_ingested

    def delete_document(self, doc_id: str) -> int:
        """
        Deletes all chunks belonging to doc_id.
        Returns number of deleted chunks if detectable.
        """
        if not self._available:
            return 0
        try:
            self.collection.delete(where={"doc_id": doc_id})
            logger.info(f"Deleted existing chunks for doc_id: '{doc_id}'")
            return 1
        except Exception as e:
            logger.warning(f"delete_document error for '{doc_id}' (attempting fallback): {e}")
            try:
                res = self.collection.get()
                ids_to_del = [cid for cid in res.get("ids", []) if cid.startswith(f"{doc_id}_")]
                if ids_to_del:
                    self.collection.delete(ids=ids_to_del)
                    return len(ids_to_del)
            except Exception as e2:
                logger.error(f"Fallback delete failed for '{doc_id}': {e2}")
            return 0

    def reset_collection(self):
        """Resets the collection, clearing all existing chunks."""
        if not self._available:
            return
        try:
            self.client.delete_collection("dpdp_compliance_docs")
            self.collection = self.client.get_or_create_collection(
                name="dpdp_compliance_docs",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collection 'dpdp_compliance_docs' reset.")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")

    def get_corpus_version(self) -> str:
        """
        Returns a deterministic version string for the current Chroma collection
        based on corpus manifest content hash so that Redis caching accurately
        invalidates whenever documents, manifest, or chunk count change.
        """
        if not self._available:
            return "unavailable"
        count = self.collection.count()
        if count == 0:
            return "empty"

        # Check for documents/corpus_manifest.json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifest_path = os.path.join(base_dir, "documents", "corpus_manifest.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "rb") as f:
                    m_hash = hashlib.sha256(f.read()).hexdigest()[:16]
                return f"v_manifest_{m_hash}_c{count}"
            except Exception:
                pass

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
