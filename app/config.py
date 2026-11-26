"""
Конфігурація через змінні середовища — той самий підхід, що в ЛР1-ЛР7.
Цей файл видається готовим — редагувати не потрібно.
"""

from __future__ import annotations

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class PrimaryMode(str, Enum):
    ok = "ok"        # звичайна робота
    fail = "fail"    # основна модель завжди кидає виняток
    slow = "slow"    # основна модель відповідає повільно (slow_ms)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OK11_", env_file=".env", extra="ignore")

    data_dir: str = "data"

    # --- поведінка основної моделі (для демонстрації fallback / circuit breaker) ---
    primary_mode: PrimaryMode = PrimaryMode.ok
    primary_slow_ms: int = 800

    # --- circuit breaker (крок 3) ---
    breaker_fail_threshold: int = 3     # скільки поспіль невдач відкриває коло
    breaker_cooldown_s: float = 5.0     # скільки коло лишається відкритим

    # --- вхідні guardrails (крок 4) ---
    max_input_chars: int = 1000

    # --- rate limiting (крок 9, поглиблений рівень) ---
    rate_limit_enabled: bool = False
    rate_limit_capacity: int = 10       # місткість «відра» токенів на один ключ
    rate_limit_refill_per_s: float = 5.0

    # --- «секрет», який основна (вразлива) модель не має розкривати ---
    system_secret: str = "ADMIN-42"
