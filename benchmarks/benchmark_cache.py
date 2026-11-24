#!/usr/bin/env python3
"""
benchmark_cache.py — Reproducible cache latency benchmark.

PURPOSE:
    Measures the latency difference between the uncached (AI-calling) path
    and the Redis cache-hit path.

MODES:
    1. Offline / Mocked (DEFAULT):
       - Uses a deterministic mocked AI provider (with simulated 250ms LLM processing time).
       - Does not require network access, live Groq API key, or paid tokens.
       - Demonstrates repeatable framework + cache path performance.

    2. Live Groq Mode (OPT-IN with --live):
       - Requires GROQ_API_KEY environment variable.
       - Measures actual live Groq Cloud network roundtrip vs. local cache hit.

USAGE:
    python benchmarks/benchmark_cache.py
    python benchmarks/benchmark_cache.py --samples 50 --warmup 5
    python benchmarks/benchmark_cache.py --live
"""

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add ai-service to sys.path so we can import app and services
AI_SERVICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-service")
sys.path.insert(0, AI_SERVICE_DIR)

from app import app, cache_service


def calculate_percentiles(values: list[float]) -> dict:
    """Calculate descriptive statistics for a list of latency values (in ms)."""
    if not values:
        return {}
    sorted_v = sorted(values)
    n = len(sorted_v)

    def p(pct):
        idx = int(n * (pct / 100.0))
        return sorted_v[min(idx, n - 1)]

    mean = sum(sorted_v) / n
    variance = sum((x - mean) ** 2 for x in sorted_v) / n
    stddev = variance ** 0.5

    return {
        "count": n,
        "min": round(sorted_v[0], 2),
        "p50": round(p(50), 2),
        "p90": round(p(90), 2),
        "p95": round(p(95), 2),
        "p99": round(p(99), 2),
        "max": round(sorted_v[-1], 2),
        "mean": round(mean, 2),
        "stddev": round(stddev, 2)
    }


def run_benchmark(samples: int = 50, warmup: int = 5, mock_delay_ms: float = 250.0, live: bool = False):
    print("=" * 70)
    print("DPDP Act Compliance Centre — Redis Cache Latency Benchmark")
    print("=" * 70)
    print(f"Date:         {datetime.now(timezone.utc).isoformat()}")
    print(f"Platform:     {platform.platform()} (Python {platform.python_version()})")
    print(f"Mode:         {'LIVE GROQ API' if live else 'DETERMINISTIC MOCKED AI (offline)'}")
    print(f"Sample Count: {samples} requests per test phase")
    print(f"Warm-up runs: {warmup} iterations")
    if not live:
        print(f"Simulated AI: {mock_delay_ms} ms simulated model inference latency")
    print("=" * 70)

    if live and not os.environ.get("GROQ_API_KEY"):
        print("ERROR: --live mode requires the GROQ_API_KEY environment variable.")
        sys.exit(1)

    app.config["TESTING"] = True
    test_client = app.test_client()

    mock_ai_response = {
        "professional_description": "Employee payroll and banking records processed under statutory compliance mandate."
    }

    # In-memory dictionary for deterministic mock Redis if live Redis is unavailable
    in_memory_cache = {}
    use_mock_redis = not cache_service.is_available()

    if use_mock_redis:
        print("[INFO] Live Redis not connected — using in-memory mock store for cache measurements.")
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda k: in_memory_cache.get(k)
        mock_redis.setex.side_effect = lambda k, ttl, v: in_memory_cache.update({k: v})
        mock_redis.ping.return_value = True
        cache_service.client = mock_redis
        cache_service.enabled = True
    else:
        print(f"[INFO] Using live Redis server for caching measurements.")

    def do_request(text: str, is_live_mode: bool):
        start = time.perf_counter()
        if is_live_mode:
            res = test_client.post("/describe", json={"input_text": text})
        else:
            with patch("routes.describe._groq.call_for_json") as mock_groq:
                def fake_call(*args, **kwargs):
                    if mock_delay_ms > 0:
                        time.sleep(mock_delay_ms / 1000.0)
                    return mock_ai_response
                mock_groq.side_effect = fake_call
                res = test_client.post("/describe", json={"input_text": text})

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert res.status_code == 200, f"Request failed: {res.status_code} - {res.data}"
        return elapsed_ms

    # Warm-up phase
    print("\nExecuting warm-up iterations...")
    for i in range(warmup):
        do_request(f"Warmup query iteration {i}", is_live_mode=live)

    # Phase 1: Uncached Path (Cold misses: unique input per iteration)
    print(f"\nMeasuring Uncached Path ({samples} cold misses)...")
    uncached_latencies = []
    for i in range(samples):
        latency = do_request(f"Unique compliance audit query #{i} for cold miss measurement", is_live_mode=live)
        uncached_latencies.append(latency)

    # Seed the cache with a designated benchmark query
    benchmark_cached_query = "Standard employee consent record for benchmark cache-hit measurement."
    do_request(benchmark_cached_query, is_live_mode=live)

    # Phase 2: Cached Path (Warm hits: identical input, hitting Redis)
    print(f"Measuring Cached Path ({samples} warm hits on identical key)...")
    cached_latencies = []
    for i in range(samples):
        latency = do_request(benchmark_cached_query, is_live_mode=live)
        cached_latencies.append(latency)

    # Compute Statistics
    stats_uncached = calculate_percentiles(uncached_latencies)
    stats_cached = calculate_percentiles(cached_latencies)

    p50_uncached = stats_uncached["p50"]
    p50_cached = stats_cached["p50"]
    latency_reduction_pct = (
        round(((p50_uncached - p50_cached) / p50_uncached) * 100.0, 2)
        if p50_uncached > 0 else 0.0
    )
    speedup_factor = round(p50_uncached / p50_cached, 2) if p50_cached > 0 else 0.0

    # Output Results Table
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    print(f"{'Metric':<18} | {'Uncached (Cold)':<18} | {'Cached (Warm Hit)':<18}")
    print("-" * 62)
    print(f"{'p50 (Median)':<18} | {stats_uncached['p50']:>14.2f} ms | {stats_cached['p50']:>14.2f} ms")
    print(f"{'p90':<18} | {stats_uncached['p90']:>14.2f} ms | {stats_cached['p90']:>14.2f} ms")
    print(f"{'p95':<18} | {stats_uncached['p95']:>14.2f} ms | {stats_cached['p95']:>14.2f} ms")
    print(f"{'p99':<18} | {stats_uncached['p99']:>14.2f} ms | {stats_cached['p99']:>14.2f} ms")
    print(f"{'Mean':<18} | {stats_uncached['mean']:>14.2f} ms | {stats_cached['mean']:>14.2f} ms")
    print(f"{'StdDev':<18} | {stats_uncached['stddev']:>14.2f} ms | {stats_cached['stddev']:>14.2f} ms")
    print(f"{'Min / Max':<18} | {stats_uncached['min']:.1f} / {stats_uncached['max']:.1f} ms | {stats_cached['min']:.1f} / {stats_cached['max']:.1f} ms")
    print("=" * 70)
    print(f"Measured Median Speedup:     {speedup_factor}x faster")
    print(f"Measured Latency Reduction:  {latency_reduction_pct}% (from {p50_uncached}ms to {p50_cached}ms)")
    print("=" * 70)

    # Save benchmark artifact to JSON for reproducibility
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "benchmark_cache_results.json")
    results_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "mode": "live_groq" if live else "deterministic_mock",
            "mock_delay_ms": mock_delay_ms if not live else None
        },
        "samples": samples,
        "warmup": warmup,
        "uncached_stats": stats_uncached,
        "cached_stats": stats_cached,
        "latency_reduction_percent": latency_reduction_pct,
        "speedup_factor": speedup_factor
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    print(f"Saved reproducible results artifact to: {output_file}\n")
    return results_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reproducible Redis cache benchmark for DPDP Act Compliance Centre.")
    parser.add_argument("--samples", type=int, default=50, help="Number of samples to collect (default: 50)")
    parser.add_argument("--warmup", type=int, default=5, help="Number of warmup iterations (default: 5)")
    parser.add_argument("--mock-delay-ms", type=float, default=250.0, help="Simulated AI latency for offline mock mode (default: 250ms)")
    parser.add_argument("--live", action="store_true", help="Run with live Groq Cloud API (requires GROQ_API_KEY)")
    args = parser.parse_args()

    run_benchmark(
        samples=args.samples,
        warmup=args.warmup,
        mock_delay_ms=args.mock_delay_ms,
        live=args.live
    )
