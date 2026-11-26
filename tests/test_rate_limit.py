"""Тести app/rate_limit.py — крок 9 (поглиблений рівень)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.advanced

from app.rate_limit import TokenBucketLimiter


def test_allows_up_to_capacity_then_blocks(fake_clock):
    rl = TokenBucketLimiter(capacity=5, refill_per_s=1, clock=fake_clock)
    allowed = [rl.take("k").allowed for _ in range(7)]
    assert allowed == [True] * 5 + [False] * 2


def test_retry_after_is_positive_when_blocked(fake_clock):
    rl = TokenBucketLimiter(capacity=1, refill_per_s=2, clock=fake_clock)
    assert rl.take("k").allowed is True
    decision = rl.take("k")
    assert decision.allowed is False
    assert decision.retry_after_s == pytest.approx(0.5, abs=1e-6)


def test_bucket_refills_over_time(fake_clock):
    rl = TokenBucketLimiter(capacity=5, refill_per_s=1, clock=fake_clock)
    for _ in range(5):
        rl.take("k")
    assert rl.take("k").allowed is False
    fake_clock.advance(3)               # +3 токени
    assert [rl.take("k").allowed for _ in range(4)] == [True, True, True, False]


def test_keys_are_independent(fake_clock):
    rl = TokenBucketLimiter(capacity=2, refill_per_s=1, clock=fake_clock)
    assert rl.take("a").allowed and rl.take("a").allowed
    assert rl.take("a").allowed is False
    assert rl.take("b").allowed is True   # інший ключ — власне відро
