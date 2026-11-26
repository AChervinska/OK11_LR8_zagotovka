"""
Стійкий виклик моделі: circuit breaker + резервна модель (graceful
degradation) — крок 6.

TODO: answer_with_resilience().
"""

from __future__ import annotations

from dataclasses import dataclass

from app.assistant import FallbackAssistant, PrimaryAssistant
from app.circuit_breaker import CircuitBreaker, CircuitOpen


@dataclass
class ResilientAnswer:
    answer: str
    degraded: bool          # True, якщо відповіла резервна модель
    source: str             # "primary" | "fallback"


def answer_with_resilience(
    question: str,
    primary: PrimaryAssistant,
    fallback: FallbackAssistant,
    breaker: CircuitBreaker,
) -> ResilientAnswer:

    try:
        text = breaker.call(primary.answer, question)

        return ResilientAnswer(
            answer=text,
            degraded=False,
            source="primary"
        )

    except Exception:
        return ResilientAnswer(
            answer=fallback.answer(question),
            degraded=True,
            source="fallback"
        )
