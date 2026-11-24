#!/usr/bin/env python3
"""
eval_grounded.py — Evaluation harness for RAG retrieval and citation grounding.

PURPOSE:
    Evaluates grounding quality against a reviewed test set of compliance queries:
    1. Retrieval Coverage: Percentage of queries returning at least one relevant context chunk.
    2. Citation Verification: Percentage of returned citations that match real chunk IDs in ChromaDB.
    3. Invalid Citation Rate: Percentage of citations that are hallucinated or unverified.

IMPORTANT NOTICE:
    - Results represent performance strictly on this defined benchmark test set and the
      currently ingested ChromaDB knowledge base.
    - These results do NOT constitute a universal claim of '100% grounded' or zero hallucinations.
    - Grounding improves auditability and traceability, but cannot guarantee legal correctness.

USAGE:
    python benchmarks/eval_grounded.py
"""

import json
import os
import platform
import sys
from datetime import datetime, timezone

# Add ai-service to sys.path
AI_SERVICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-service")
sys.path.insert(0, AI_SERVICE_DIR)

from services.chroma_client import ChromaClient
from services.rag_service import retrieve_rag_context


# Reviewed test set of DPDP Act compliance query scenarios
REVIEWED_TEST_SET = [
    {
        "id": "TC-001",
        "category": "Children Data Protection",
        "query": "Processing personal data of children under 18 years and obtaining parental consent.",
        "expected_topic": "children"
    },
    {
        "id": "TC-002",
        "category": "Data Breach Notification",
        "query": "Intimating the Data Protection Board of India and affected data principals upon personal data breach.",
        "expected_topic": "breach"
    },
    {
        "id": "TC-003",
        "category": "Behavioral Monitoring",
        "query": "Behavioral monitoring and targeted advertising directed at children.",
        "expected_topic": "children"
    },
    {
        "id": "TC-004",
        "category": "Penalties",
        "query": "Penalties for failure to prevent personal data breach up to 250 crore rupees.",
        "expected_topic": "penalty"
    },
    {
        "id": "TC-005",
        "category": "Cross-Border Transfer (Out of Corpus)",
        "query": "Transfer of personal data outside India to blacklisted countries or territories.",
        "expected_topic": "cross_border"
    }
]


def run_grounding_evaluation():
    print("=" * 70)
    print("DPDP Act Compliance Centre — RAG Grounding & Citation Evaluation")
    print("=" * 70)
    print(f"Date:         {datetime.now(timezone.utc).isoformat()}")
    print(f"Platform:     {platform.platform()} (Python {platform.python_version()})")
    print(f"Test Cases:   {len(REVIEWED_TEST_SET)} reviewed scenarios")
    print("=" * 70)

    chroma = ChromaClient()
    doc_count = chroma.count()

    print(f"ChromaDB Status: {'Available' if getattr(chroma, '_available', False) else 'Unavailable'}")
    print(f"Total Chunks in Collection: {doc_count}\n")

    if doc_count == 0:
        print("[WARNING] ChromaDB collection is empty! No authoritative source documents ingested.")
        print("To ingest documents: place files in ai-service/documents/ and run 'python ai-service/ingest_documents.py'.")
        print("Evaluating system behavior under empty-knowledge-base conditions...\n")

    # Get all valid chunk IDs currently in ChromaDB for citation verification
    valid_chunk_ids = set()
    if getattr(chroma, "_available", False) and doc_count > 0:
        try:
            get_data = chroma.collection.get(include=[])
            valid_chunk_ids = set(get_data.get("ids", []))
        except Exception:
            pass

    results = []
    retrieval_successes = 0
    total_citations = 0
    valid_citations = 0

    print(f"{'Test ID':<8} | {'Category':<28} | {'Grounded?':<10} | {'Citations':<10} | {'Status'}")
    print("-" * 75)

    for tc in REVIEWED_TEST_SET:
        grounded, context_block, citations, disclaimer = retrieve_rag_context(
            chroma,
            tc["query"],
            top_k=3
        )

        test_citations_valid = True
        for cite in citations:
            total_citations += 1
            cid = cite.get("chunk_id")
            if cid in valid_chunk_ids:
                valid_citations += 1
            else:
                test_citations_valid = False

        if grounded:
            retrieval_successes += 1
            status = "GROUNDED (verified)" if test_citations_valid else "INVALID_CITATION"
        else:
            status = "UNGROUNDED (honest fallback)"

        print(f"{tc['id']:<8} | {tc['category'][:26]:<28} | {str(grounded):<10} | {len(citations):<10} | {status}")

        results.append({
            "test_id": tc["id"],
            "category": tc["category"],
            "query": tc["query"],
            "grounded": grounded,
            "citations_returned": citations,
            "citations_count": len(citations),
            "citations_verified": test_citations_valid
        })

    # Metrics
    num_tests = len(REVIEWED_TEST_SET)
    retrieval_coverage_pct = round((retrieval_successes / num_tests) * 100.0, 2)
    invalid_citation_rate_pct = (
        round(((total_citations - valid_citations) / total_citations) * 100.0, 2)
        if total_citations > 0 else 0.0
    )
    citation_accuracy_pct = (
        round((valid_citations / total_citations) * 100.0, 2)
        if total_citations > 0 else 100.0
    )

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY (METRIC DEFINITIONS)")
    print("=" * 70)
    print(f"Total Test Cases:              {num_tests}")
    print(f"Retrieval Coverage:            {retrieval_coverage_pct}% ({retrieval_successes}/{num_tests} queries retrieved candidate chunks)")
    print(f"Total Citations Generated:     {total_citations}")
    print(f"Citations Verified in Chroma:  {valid_citations}/{total_citations} ({citation_accuracy_pct}%)")
    print(f"Invalid Citation Rate:         {invalid_citation_rate_pct}%")
    print("=" * 70)
    print("DEFINITIONS & IMPORTANT NOTICE:")
    print("1. 'Retrieval Coverage' measures candidate chunk retrieval from the local vector store.")
    print("2. 'Citations Verified' confirms chunk IDs match real metadata in ChromaDB.")
    print("3. Neither metric measures legal accuracy, regulatory compliance, or advice correctness.")
    print("=" * 70)

    # Save artifact
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "eval_grounded_results.json")
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_test_cases": num_tests,
        "chromadb_chunks_in_db": doc_count,
        "retrieval_coverage_percent": retrieval_coverage_pct,
        "total_citations_generated": total_citations,
        "citations_verified": valid_citations,
        "citation_accuracy_percent": citation_accuracy_pct,
        "invalid_citation_rate_percent": invalid_citation_rate_pct,
        "metric_definitions": {
            "retrieval_coverage": "Percentage of test queries retrieving candidate chunks from ChromaDB.",
            "citations_verified": "Percentage of citation chunk IDs verified against existing ChromaDB chunk metadata.",
            "legal_accuracy": "NOT MEASURED. AI output is informational assistance and is not guaranteed legally accurate."
        },
        "disclaimer": "Evaluated strictly on the defined test set. Not a universal guarantee or legal certification.",
        "test_results": results
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Saved evaluation results artifact to: {output_file}\n")
    return summary


if __name__ == "__main__":
    run_grounding_evaluation()
