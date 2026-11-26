"""
Простий навантажувальний драйвер (базовий рівень, крок 8).

Надсилає N запитів до /ask з паралельністю C, збирає латентність і
коди відповідей. Виводить p50/p95/p99, RPS, розподіл статусів і частку
degraded-відповідей.

Це не заміна повноцінному інструменту (Locust — крок 10), а мінімум,
щоб ПОБАЧИТИ ефект circuit breaker / fallback числом.

Готовий скрипт (не редагувати).

    # спершу підняти сервіс в іншому терміналі:
    #   uvicorn app.main:app
    python scripts/loadtest.py --n 300 --c 20
    #   а тепер сервіс з повільною основною моделлю:
    #   OK11_PRIMARY_MODE=slow OK11_PRIMARY_SLOW_MS=800 uvicorn app.main:app
    python scripts/loadtest.py --n 300 --c 20
"""

from __future__ import annotations

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

QUESTIONS = [
    "Які документи потрібні для вступу?",
    "Коли публікується розклад занять?",
    "Як подати заяву на гуртожиток?",
    "Скільки триває навчання на магістратурі?",
]


def one_request(client: httpx.Client, url: str, q: str) -> tuple[int, float, bool]:
    start = time.perf_counter()
    try:
        r = client.post(url, json={"question": q}, timeout=10.0)
        elapsed = (time.perf_counter() - start) * 1000
        degraded = r.status_code == 200 and r.json().get("degraded", False)
        return r.status_code, elapsed, degraded
    except httpx.HTTPError:
        return 0, (time.perf_counter() - start) * 1000, False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000/ask")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--c", type=int, default=20)
    args = ap.parse_args()

    results: list[tuple[int, float, bool]] = []
    started = time.perf_counter()
    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=args.c) as pool:
            futures = [
                pool.submit(one_request, client, args.url, QUESTIONS[i % len(QUESTIONS)])
                for i in range(args.n)
            ]
            for f in futures:
                results.append(f.result())
    wall = time.perf_counter() - started

    latencies = sorted(r[1] for r in results)
    statuses: dict[int, int] = {}
    for code, _, _ in results:
        statuses[code] = statuses.get(code, 0) + 1
    degraded = sum(1 for _, _, d in results if d)

    def pct(p: float) -> float:
        return latencies[min(int(len(latencies) * p), len(latencies) - 1)]

    print(f"запитів: {args.n}  паралельність: {args.c}  час: {wall:.1f} с")
    print(f"RPS: {args.n / wall:.1f}")
    print(f"латентність, мс: p50={statistics.median(latencies):.0f}  "
          f"p95={pct(0.95):.0f}  p99={pct(0.99):.0f}  max={latencies[-1]:.0f}")
    print(f"статуси: {dict(sorted(statuses.items()))}")
    print(f"degraded-відповіді (fallback): {degraded}/{args.n} ({degraded / args.n:.0%})")


if __name__ == "__main__":
    main()
