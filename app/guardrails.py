"""
Guardrails: перевірка вхідного запиту і редагування вихідної відповіді
від витоку персональних даних / секретів — крок 4.

TODO: check_input() і redact_output().
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import Settings

settings = Settings()

# Евристики виявлення prompt injection / jailbreak. Список свідомо
# неповний — його межі аналізуються в кроці 5. Можете доповнювати.
INJECTION_RULES: list[tuple[str, re.Pattern]] = [
    ("ignore-previous",
     re.compile(r"(ignore|disregard|forget).{0,25}(previous|above|all|prior).{0,15}(instruction|prompt|rule)", re.I)),
    ("ignore-previous-ua",
     re.compile(r"(забудь|проігноруй|не зважай).{0,25}(попередн|інструкц|вказівк|правил)", re.I)),
    ("reveal-secret",
     re.compile(r"(reveal|print|output|show|вивед|розкрий|покажи|дай).{0,25}(secret|system prompt|секрет|систем\w* промпт|token|токен|пароль)", re.I)),
    ("role-override", re.compile(r"\b(you are now|ти тепер|ты теперь|act as|pretend to be|уяви що ти)\b", re.I)),
    ("jailbreak-name", re.compile(r"\b(DAN|jailbreak|developer mode|do anything now)\b", re.I)),
    ("system-marker", re.compile(r"(^|\n)\s*(system|assistant|user)\s*:", re.I)),
    ("prompt-delimiter",
     re.compile(r"(\[/?INST\]|<\|.*?\|>|###\s*instruction)", re.I)),
]

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(
    r"(?<!\d)(?:\+?38)?[\s-]?\(?0\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_SECRET = re.compile(re.escape(settings.system_secret))


@dataclass
class GuardResult:
    allowed: bool
    reason: str
    matched_rule: str | None = None


def check_input(text: str) -> GuardResult:
    if len(text) > settings.max_input_chars:
        return GuardResult(
            False,
            "Перевищено максимальну довжину запиту",
            "too-long"
        )

    for rule_name, pattern in INJECTION_RULES:
        if pattern.search(text):
            return GuardResult(
                False,
                "Виявлено ознаки атаки",
                rule_name
            )

    return GuardResult(True, "ok")


def redact_output(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[phone]", text)
    text = _CARD.sub("[card]", text)
    text = _SECRET.sub("[redacted]", text)

    return text
