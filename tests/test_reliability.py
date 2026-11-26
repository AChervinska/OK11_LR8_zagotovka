"""Тести app/reliability.py — крок 6."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assistant import FallbackAssistant, PrimaryAssistant
from app.circuit_breaker import CircuitBreaker
from app.config import PrimaryMode
from app.reliability import answer_with_resilience


def test_primary_ok_returns_primary_answer(fake_clock):
    r = answer_with_resilience(
        "Які документи потрібні для вступу?",
        PrimaryAssistant(mode=PrimaryMode.ok),
        FallbackAssistant(),
        CircuitBreaker(clock=fake_clock),
    )
    assert r.degraded is False
    assert r.source == "primary"
    assert "вступу" in r.answer


def test_primary_failure_degrades_to_fallback(fake_clock):
    r = answer_with_resilience(
        "будь-що", PrimaryAssistant(mode=PrimaryMode.fail),
        FallbackAssistant(), CircuitBreaker(clock=fake_clock),
    )
    assert r.degraded is True
    assert r.source == "fallback"


def test_breaker_opens_and_serves_fallback_without_calling_primary(fake_clock):
    breaker = CircuitBreaker(fail_threshold=3, cooldown_s=5, clock=fake_clock)
    primary = PrimaryAssistant(mode=PrimaryMode.fail)
    fallback = FallbackAssistant()

    for _ in range(5):
        r = answer_with_resilience("q", primary, fallback, breaker)
        assert r.degraded is True
    assert breaker.state == CircuitBreaker.OPEN
