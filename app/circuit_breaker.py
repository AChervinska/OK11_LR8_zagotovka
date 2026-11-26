"""
Circuit breaker (запобіжник) — крок 3.

Три стани: CLOSED (виклики проходять, рахуємо поспіль невдачі),
OPEN (виклики миттєво відхиляються протягом cooldown_s),
HALF_OPEN (після cooldown — один пробний виклик: успіх -> CLOSED,
невдача -> OPEN).

TODO: call(), _on_success(), _on_failure().
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.config import Settings

settings = Settings()


class CircuitOpen(RuntimeError):
    """Коло розімкнуте — виклик не виконувався."""


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        fail_threshold: int | None = None,
        cooldown_s: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.fail_threshold = fail_threshold or settings.breaker_fail_threshold
        self.cooldown_s = cooldown_s if cooldown_s is not None else settings.breaker_cooldown_s
        self._clock = clock
        self.state = self.CLOSED
        self._consecutive_failures = 0
        self._opened_at = 0.0

    def call(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        if self.state == self.OPEN:
            if self._clock() - self._opened_at < self.cooldown_s:
                raise CircuitOpen("Circuit breaker is open")

            self.state = self.HALF_OPEN

        try:
            result = fn(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise

        self._on_success()
        return result

    def _on_success(self) -> None:
        self._consecutive_failures = 0
        self.state = self.CLOSED

    def _on_failure(self) -> None:
        self._consecutive_failures += 1

        if (
            self.state == self.HALF_OPEN
            or self._consecutive_failures >= self.fail_threshold
        ):
            self.state = self.OPEN
            self._opened_at = self._clock()
