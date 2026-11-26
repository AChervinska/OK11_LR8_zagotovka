"""Тести app/circuit_breaker.py — крок 3."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.circuit_breaker import CircuitBreaker, CircuitOpen


def _boom():
    raise RuntimeError("fail")


def _ok():
    return "ok"


def test_stays_closed_on_success(fake_clock):
    cb = CircuitBreaker(fail_threshold=3, cooldown_s=5, clock=fake_clock)
    for _ in range(10):
        assert cb.call(_ok) == "ok"
    assert cb.state == CircuitBreaker.CLOSED


def test_opens_after_threshold_consecutive_failures(fake_clock):
    cb = CircuitBreaker(fail_threshold=3, cooldown_s=5, clock=fake_clock)
    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.call(_boom)
    assert cb.state == CircuitBreaker.OPEN
    # у відкритому стані виклик навіть не доходить до функції
    with pytest.raises(CircuitOpen):
        cb.call(_ok)


def test_one_success_resets_failure_count(fake_clock):
    cb = CircuitBreaker(fail_threshold=3, cooldown_s=5, clock=fake_clock)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(_boom)
    cb.call(_ok)  # скидає лічильник
    with pytest.raises(RuntimeError):
        cb.call(_boom)
    assert cb.state == CircuitBreaker.CLOSED


def test_half_open_after_cooldown_then_close_on_success(fake_clock):
    cb = CircuitBreaker(fail_threshold=2, cooldown_s=5, clock=fake_clock)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(_boom)
    assert cb.state == CircuitBreaker.OPEN

    fake_clock.advance(6)  # cooldown минув
    assert cb.call(_ok) == "ok"   # пробний виклик проходить
    assert cb.state == CircuitBreaker.CLOSED


def test_half_open_failure_reopens(fake_clock):
    cb = CircuitBreaker(fail_threshold=2, cooldown_s=5, clock=fake_clock)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(_boom)
    fake_clock.advance(6)
    with pytest.raises(RuntimeError):
        cb.call(_boom)   # пробний виклик знову невдалий
    assert cb.state == CircuitBreaker.OPEN
