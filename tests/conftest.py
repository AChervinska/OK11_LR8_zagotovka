"""
Фікстури тестів ЛР8. Сервіс і моделі детерміновані й офлайн, тому
тести не потребують ні мережі, ні запущеного uvicorn.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.main as main_module
from app.assistant import FallbackAssistant, PrimaryAssistant
from app.circuit_breaker import CircuitBreaker
from app.config import PrimaryMode


class FakeClock:
    """Керований годинник для тестів circuit breaker / rate limiter."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_client(monkeypatch):
    """Фабрика TestClient із заданим режимом основної моделі та свіжим
    circuit breaker."""

    def _make(primary_mode: PrimaryMode = PrimaryMode.ok, rate_limit: bool = False,
              slow_ms: int = 50):
        monkeypatch.setattr(main_module, "primary", PrimaryAssistant(mode=primary_mode, slow_ms=slow_ms))
        monkeypatch.setattr(main_module, "fallback", FallbackAssistant())
        monkeypatch.setattr(main_module, "breaker", CircuitBreaker(fail_threshold=3, cooldown_s=5.0))
        monkeypatch.setattr(main_module.settings, "rate_limit_enabled", rate_limit)
        return TestClient(main_module.app)

    return _make


@pytest.fixture
def client(make_client):
    return make_client()
