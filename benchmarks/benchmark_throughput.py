#!/usr/bin/env python3
"""
benchmark_throughput.py — Model token generation throughput benchmark.

PURPOSE:
    Measures completion token throughput (tokens per second) using live Groq Cloud API.

OPT-IN REQUIREMENT:
    This benchmark is strictly opt-in because it requires live network access and a valid
    GROQ_API_KEY. It consumes tokens on the Groq Cloud platform.

DEFINITIONS:
    - Elapsed Time: Measured wall-clock time from HTTP request dispatch until full response parsing.
    - Completion Tokens: Number of generated completion tokens reported by Groq API's usage metadata.
    - Throughput: completion_tokens / elapsed_time_seconds.

USAGE:
    python benchmarks/benchmark_throughput.py
    (Shows explanation and exits cleanly if GROQ_API_KEY is not provided)

    python benchmarks/benchmark_throughput.py --live --samples 5
"""

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone

# Add ai-service to sys.path
AI_SERVICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-service")
sys.path.insert(0, AI_SERVICE_DIR)


BENCHMARK_PROMPTS = [
    (
        "You are an expert Data Protection Officer. Rewrite this compliance description professionally "
        "under India's DPDP Act: Customer phone numbers and addresses stored in unencrypted Google Drive folders "
        "accessible by all marketing interns without 2FA or access logs."
    ),
    (
        "Provide 3 actionable compliance recommendations under the DPDP Act for an enterprise deploying "
        "biometric fingerprint scanners for 10,000 factory workers with vendor cloud sync."
    ),
    (
        "Generate an executive compliance audit report for a healthcare provider that suffered an unauthorized "
        "export of 50,000 patient diagnostic records to a third-party analytics provider without consent."
    )
]


def run_throughput_benchmark(samples: int = 3, live: bool = False):
    print("=" * 70)
    print("DPDP Act Compliance Centre — Model Token Throughput Benchmark")
    print("=" * 70)
    print(f"Date:         {datetime.now(timezone.utc).isoformat()}")
    print(f"Platform:     {platform.platform()} (Python {platform.python_version()})")
    print(f"Model:        llama-3.3-70b-versatile (Groq Cloud)")
    print("=" * 70)

    api_key = os.environ.get("GROQ_API_KEY")

    if not live or not api_key or api_key.startswith("gsk_REPLACE"):
        print("\n[NOTE] Live Throughput Benchmark is OPT-IN.")
        print("To run this benchmark, provide a valid Groq API key and specify --live:")
        print("   $env:GROQ_API_KEY=\"gsk_...\"")
        print("   python benchmarks/benchmark_throughput.py --live --samples 3\n")
        print("Skipping live benchmark execution. No fabricated or simulated numbers will be generated.")
        print("=" * 70)
        return None

    try:
        from groq import Groq
    except ImportError:
        print("ERROR: groq Python library not installed. Run: pip install groq")
        return None

    client = Groq(api_key=api_key)
    results = []

    print(f"\nRunning {samples} live completion requests to Groq Cloud API...\n")

    for i in range(samples):
        prompt = BENCHMARK_PROMPTS[i % len(BENCHMARK_PROMPTS)]
        print(f"Sample {i+1}/{samples}: Dispatching request...", end="", flush=True)

        start_time = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            elapsed_sec = time.perf_counter() - start_time

            usage = getattr(response, "usage", None)
            if usage and hasattr(usage, "completion_tokens"):
                comp_tokens = usage.completion_tokens
                prompt_tokens = getattr(usage, "prompt_tokens", 0)
                total_tokens = getattr(usage, "total_tokens", comp_tokens + prompt_tokens)
                throughput_tps = round(comp_tokens / elapsed_sec, 2) if elapsed_sec > 0 else 0.0

                record = {
                    "sample_index": i + 1,
                    "elapsed_sec": round(elapsed_sec, 3),
                    "completion_tokens": comp_tokens,
                    "prompt_tokens": prompt_tokens,
                    "total_tokens": total_tokens,
                    "throughput_tokens_per_sec": throughput_tps
                }
                results.append(record)
                print(f" DONE in {elapsed_sec:.2f}s ({comp_tokens} tokens @ {throughput_tps} tok/sec)")
            else:
                print(f" DONE in {elapsed_sec:.2f}s (Token usage metadata unavailable)")

        except Exception as e:
            print(f" FAILED: {e}")

    if not results:
        print("\nERROR: No benchmark samples completed successfully.")
        return None

    # Summary
    all_tps = [r["throughput_tokens_per_sec"] for r in results]
    avg_tps = round(sum(all_tps) / len(all_tps), 2)
    max_tps = max(all_tps)
    min_tps = min(all_tps)

    print("\n" + "=" * 70)
    print("LIVE THROUGHPUT BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Samples Completed:             {len(results)}")
    print(f"Average Measured Throughput:   {avg_tps} tokens/sec")
    print(f"Range:                         {min_tps} – {max_tps} tokens/sec")
    print("=" * 70)

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "benchmark_throughput_results.json")
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "llama-3.3-70b-versatile",
        "samples": results,
        "average_tokens_per_second": avg_tps,
        "min_tokens_per_second": min_tps,
        "max_tokens_per_second": max_tps,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version()
        }
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Saved live benchmark results to: {output_file}\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live model token throughput benchmark.")
    parser.add_argument("--live", action="store_true", help="Explicitly enable live Groq Cloud API calls")
    parser.add_argument("--samples", type=int, default=3, help="Number of benchmark samples (default: 3)")
    args = parser.parse_args()

    run_throughput_benchmark(samples=args.samples, live=args.live)
