#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
import tempfile
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.log_analyzer import analyze


def generate_log(path: Path, rows: int, seed: int = 42) -> None:
    rng = random.Random(seed)
    statuses = [200] * 88 + [301] * 3 + [404] * 6 + [500] * 2 + [502]
    targets = ["/", "/health", "/items", "/metrics", "/missing"]
    suspicious = ["/.env", "/../../etc/passwd", "/?id=1%20UNION%20SELECT%20password"]

    with path.open("w", encoding="utf-8") as handle:
        for index in range(rows):
            ip = f"10.{(index // 65536) % 256}.{(index // 256) % 256}.{index % 256}"
            target = rng.choice(suspicious) if index % 10000 == 0 else rng.choice(targets)
            status = rng.choice(statuses)
            ua = "sqlmap/1.8" if index % 25000 == 0 else "benchmark-client/1.0"
            handle.write(
                f'{ip} - - [29/Jul/2026:17:10:41 -0700] '
                f'"GET {target} HTTP/1.1" {status} 42 "-" "{ua}"\n'
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the access-log analyzer.")
    parser.add_argument("--rows", type=int, default=1_000_000)
    parser.add_argument("--file", type=Path, help="Use or create this benchmark file.")
    args = parser.parse_args()

    if args.rows < 1:
        parser.error("--rows must be greater than zero")

    temporary = args.file is None
    path = args.file or Path(tempfile.gettempdir()) / f"access-{args.rows}.log"

    started = time.perf_counter()
    generate_log(path, args.rows)
    generation_seconds = time.perf_counter() - started

    started = time.perf_counter()
    with path.open("r", encoding="utf-8") as handle:
        report = analyze(handle, top=10)
    analysis_seconds = time.perf_counter() - started

    size_mb = path.stat().st_size / (1024 * 1024)
    rate = args.rows / analysis_seconds if analysis_seconds else float("inf")

    print(f"Rows:              {args.rows:,}")
    print(f"File:              {path}")
    print(f"Size:              {size_mb:.2f} MiB")
    print(f"Generation time:   {generation_seconds:.3f} s")
    print(f"Analysis time:     {analysis_seconds:.3f} s")
    print(f"Throughput:        {rate:,.0f} lines/s")
    print(f"Error rate:        {report['summary']['error_rate_percent']:.2f}%")
    print(f"Suspicious:        {report['summary']['suspicious_requests']}")

    if temporary:
        path.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
