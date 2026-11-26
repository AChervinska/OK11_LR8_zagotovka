"""
Обмеження частоти запитів методом «відра токенів» (token bucket) —
крок 9, поглиблений рівень.

Кожен ключ (IP / API-ключ) має відро місткістю capacity, що
поповнюється зі швидкістю refill_per_s токенів/с. Запит проходить, якщо
у відрі є >= 1 токен (і забирає його).

TODO: _tokens_for(), take().
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from app.config import Settings

settings = Settings()


@dataclass
class RateDecision:
    allowed: bool
    retry_after_s: float  # 0.0, якщо allowed


class TokenBucketLimiter:
    def __init__(
        self,
        capacity: int | None = None,
        refill_per_s: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.capacity = capacity or settings.rate_limit_capacity
        self.refill_per_s = refill_per_s if refill_per_s is not None else settings.rate_limit_refill_per_s
        self._clock = clock
        # key -> (tokens, last_ts)
        self._state: dict[str, tuple[float, float]] = {}

    def _tokens_for(self, key: str) -> tuple[float, float]:
        now = self._clock()

        tokens, last = self._state.get(
            key,
            (float(self.capacity), now)
        )

        tokens = min(
            self.capacity,
            tokens + (now - last) * self.refill_per_s
        )

        return tokens, now

    def take(self, key: str) -> RateDecision:
        tokens, now = self._tokens_for(key)

        if tokens >= 1.0:
            self._state[key] = (tokens - 1.0, now)
            return RateDecision(True, 0.0)

        self._state[key] = (tokens, now)

        deficit = 1.0 - tokens

        return RateDecision(
            False,
            round(deficit / self.refill_per_s, 3)
        )
