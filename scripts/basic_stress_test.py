#!/usr/bin/env python3
import argparse
import concurrent.futures
import statistics
import time
import urllib.request


def fetch(url: str) -> tuple[bool, float]:
    start = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            ok = 200 <= response.status < 500
    except Exception:
        ok = False
    return ok, time.monotonic() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://denuncia.canaldenunciaonline.com.br")
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()
    urls = [f"{args.base_url}/health", f"{args.base_url}/triton", f"{args.base_url}/acompanhar"]
    jobs = [urls[index % len(urls)] for index in range(args.requests)]
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(fetch, jobs))
    elapsed = time.monotonic() - started
    latencies = [latency for _, latency in results]
    failures = sum(1 for ok, _ in results if not ok)
    print(
        {
            "requests": args.requests,
            "failures": failures,
            "avg_ms": round(statistics.mean(latencies) * 1000, 2),
            "throughput_rps": round(args.requests / elapsed, 2),
        }
    )


if __name__ == "__main__":
    main()
