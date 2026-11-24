#!/usr/bin/env python3
"""
measure_setup.py — Measures local system initialization and startup latency.

PURPOSE:
    Provides a reproducible measurement of the local service setup, dependency loading,
    and vector store initialization time.

IMPORTANT:
    Does NOT guarantee a 'sub-2-minute setup' or any hardcoded time.
    Measures and reports actual system time on the current hardware environment.

USAGE:
    python benchmarks/measure_setup.py
"""

import json
import os
import platform
import sys
import time
from datetime import datetime, timezone

AI_SERVICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-service")
sys.path.insert(0, AI_SERVICE_DIR)


def measure_setup_time():
    print("=" * 70)
    print("DPDP Act Compliance Centre — Setup & Startup Timing Benchmark")
    print("=" * 70)
    print(f"Date:         {datetime.now(timezone.utc).isoformat()}")
    print(f"Platform:     {platform.platform()} (Python {platform.python_version()})")
    print("=" * 70)

    milestones = []
    total_start = time.perf_counter()

    # Step 1: Core imports
    t0 = time.perf_counter()
    import pydantic
    import flask
    step1_ms = round((time.perf_counter() - t0) * 1000, 2)
    milestones.append({"step": "Core web & validation imports (Flask, Pydantic)", "duration_ms": step1_ms})
    print(f"[1/4] Core web & validation imports:    {step1_ms:>8.2f} ms")

    # Step 2: Vector store / ML imports
    t0 = time.perf_counter()
    from services.chroma_client import ChromaClient
    from services.rag_service import retrieve_rag_context
    chroma = ChromaClient()
    step2_ms = round((time.perf_counter() - t0) * 1000, 2)
    milestones.append({
        "step": "ChromaDB & SentenceTransformer init",
        "duration_ms": step2_ms,
        "docs_loaded": chroma.count()
    })
    print(f"[2/4] ChromaDB & SentenceTransformer:  {step2_ms:>8.2f} ms ({chroma.count()} chunks in DB)")

    # Step 3: Cache service init
    t0 = time.perf_counter()
    from services.cache_service import CacheService
    from app import cache_service
    step3_ms = round((time.perf_counter() - t0) * 1000, 2)
    redis_status = "Connected" if cache_service.is_available() else "Unavailable (fallback active)"
    milestones.append({
        "step": "Redis CacheService init",
        "duration_ms": step3_ms,
        "redis_status": redis_status
    })
    print(f"[3/4] Redis CacheService check:         {step3_ms:>8.2f} ms (Status: {redis_status})")

    # Step 4: Flask application assembly & route registration
    t0 = time.perf_counter()
    from app import app
    app.config["TESTING"] = True
    client = app.test_client()
    health_res = client.get("/health")
    step4_ms = round((time.perf_counter() - t0) * 1000, 2)
    milestones.append({
        "step": "Flask app assembly & health check",
        "duration_ms": step4_ms,
        "health_status": health_res.status_code
    })
    print(f"[4/4] App assembly & health probe:      {step4_ms:>8.2f} ms (HTTP {health_res.status_code})")

    total_sec = round(time.perf_counter() - total_start, 3)

    print("=" * 70)
    print(f"Total Local Initialization Time:        {total_sec} seconds")
    print("=" * 70)
    print("NOTE: Cold startup time depends on hardware, disk I/O, and whether model")
    print("weights are pre-cached in local memory/storage. Do not treat this as a fixed guarantee.")
    print("=" * 70)

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "measure_setup_results.json")
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version()
        },
        "total_startup_seconds": total_sec,
        "milestones": milestones
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Saved setup measurement artifact to: {output_file}\n")
    return summary


if __name__ == "__main__":
    measure_setup_time()
