# =============================================================================
# services/rag_service.py
# Retrieval-Augmented Generation (RAG) orchestration:
# - Queries ChromaDB vector store
# - Applies configurable top_k and distance threshold
# - Extracts verified citations from retrieved metadata (never hallucinated)
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
    else None
)
REQUIRE_GROUNDING = os.environ.get("REQUIRE_GROUNDING", "false").lower() in ("true", "1", "yes")

UNGROUNDED_DISCLAIMER = (
    "Informational assistance only. No matching authoritative DPDP Act source documents were "
    "retrieved from the knowledge base; this response is ungrounded and must not be treated as legal advice."
)

GROUNDED_DISCLAIMER = (
    "Informational assistance only. Grounded against retrieved knowledge base source chunks, "
    "but AI output cannot guarantee regulatory compliance or legal accuracy."
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

        citation = {
            "doc_id": str(doc_id),
            "chunk_id": str(cid),
            "source": str(source),
            "section": str(section)
        }
        citations.append(citation)

        doc_text = chunk.get("document", "").strip()
        formatted_chunks.append(
            f"[Source: {source} | Section: {section} | ID: {cid}]\n{doc_text}"
        )

    context_block = (
        "\n\n[AUTHORITATIVE DPDP ACT KNOWLEDGE BASE CONTEXT]:\n"
        + "\n\n---\n\n".join(formatted_chunks)
        + "\n[END CONTEXT]\n"
        + "INSTRUCTION: Ground your analysis strictly in the context above where relevant.\n"
    )

    return True, context_block, citations, GROUNDED_DISCLAIMER
