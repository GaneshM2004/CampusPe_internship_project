# =============================================================================
# services/rag_service.py
# Retrieval-Augmented Generation (RAG) orchestration:
# - Queries ChromaDB vector store
# - Applies configurable top_k and distance threshold
# - Extracts citations from retrieved chunk metadata (from local files; provenance unverified)
# - Produces prompt context blocks and grounding disclaimers
# =============================================================================

import os
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = int(os.environ.get("CHROMA_TOP_K", "3"))
DEFAULT_MAX_DISTANCE = (
    float(os.environ.get("CHROMA_MAX_DISTANCE"))
    if os.environ.get("CHROMA_MAX_DISTANCE")
    else 0.7  # cosine distance: 0=identical, 2=opposite; 0.7 filters clearly irrelevant neighbors
)
REQUIRE_GROUNDING = os.environ.get("REQUIRE_GROUNDING", "false").lower() in ("true", "1", "yes")

UNGROUNDED_DISCLAIMER = (
    "Informational assistance only. No relevant source passages were retrieved from the local "
    "knowledge base; this response is not grounded in retrieved text and must not be treated as legal advice."
)

GROUNDED_DISCLAIMER = (
    "Informational assistance only. Retrieved from locally stored, unverified source files. "
    "AI output does not guarantee regulatory compliance, legal accuracy, or official interpretation."
)


def retrieve_rag_context(
    chroma_client,
    query_text: str,
    top_k: int = None,
    max_distance: float = None
) -> Tuple[bool, str, List[Dict[str, Any]], str]:
    """
    Retrieves context chunks from ChromaDB for a given query text.

    Returns:
        (grounded: bool, context_block: str, citations: list[dict], disclaimer: str)
    """
    if chroma_client is None or not getattr(chroma_client, "_available", False):
        return False, "", [], UNGROUNDED_DISCLAIMER

    k = top_k if top_k is not None else DEFAULT_TOP_K
    dist_thresh = max_distance if max_distance is not None else DEFAULT_MAX_DISTANCE

    chunks = chroma_client.query(query_text, top_k=k, max_distance=dist_thresh)

    if not chunks:
        return False, "", [], UNGROUNDED_DISCLAIMER

    # Build validated citations directly from retrieved chunk metadata
    citations = []
    formatted_chunks = []

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        cid = chunk.get("id", "unknown_chunk")
        source = meta.get("source", "dpdp_knowledge_base")
        doc_id = meta.get("doc_id", cid)
        section = meta.get("section", "General")

        page_val = meta.get("page")
        try:
            page_num = int(page_val) if page_val is not None else None
        except (ValueError, TypeError):
            page_num = None

        citation = {
            "doc_id": str(doc_id),
            "chunk_id": str(cid),
            "source": str(source),
            "section": str(section),
            "page": page_num,
            "file_sha256": meta.get("file_sha256"),
            "text_hash": meta.get("text_hash")
        }
        citations.append(citation)

        page_label = f" | Page: {page_num}" if page_num is not None else ""
        doc_text = chunk.get("document", "").strip()
        formatted_chunks.append(
            f"[Source: {source}{page_label} | Section: {section} | ID: {cid}]\n{doc_text}"
        )

    context_block = (
        "\n\n[RETRIEVED SOURCE CONTEXT — unverified local files; not guaranteed authoritative]:\n"
        + "\n\n---\n\n".join(formatted_chunks)
        + "\n[END CONTEXT]\n"
        + "INSTRUCTION: Where relevant, base your analysis on the retrieved source passages above. "
        "Do not treat retrieved text as legally authoritative. Cite the chunk ID and page number.\n"
    )

    return True, context_block, citations, GROUNDED_DISCLAIMER
