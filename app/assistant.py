"""
Дві «моделі» для ЛР8 — навмисно спрощені й детерміновані (без Ollama,
без мережі), щоб робота була про НАДІЙНІСТЬ і БЕЗПЕКУ навколо моделі,
а не про саму модель.

PrimaryAssistant — імітує інструкційну LLM, яка відповідає на питання за
фіксованим внутрішнім контекстом. Вона НАВМИСНО вразлива до prompt
injection: якщо в запит вкласти вказівку «розкрий системний секрет» без
захисту на вході, вона його розкриє (settings.system_secret). Це і є
мішень для guardrails кроку 4.

Крім того, PrimaryAssistant можна змусити ПАДАТИ (primary_mode=fail) або
ВІДПОВІДАТИ ПОВІЛЬНО (primary_mode=slow) — для демонстрації fallback,
circuit breaker і поведінки під навантаженням.

FallbackAssistant — примітивна резервна відповідь: нічого не генерує,
нічого не розкриває, ніколи не падає.

Цей файл видається готовим — редагувати не потрібно.
"""

from __future__ import annotations

import re
import time

from app.config import PrimaryMode, Settings

settings = Settings()

_KB = {
    "вступ": "Для вступу потрібні: заява, документ про освіту з додатком, копія паспорта та ІПН, фото.",
    "розклад": "Розклад занять публікується на сайті інституту у розділі «Студенту».",
    "гуртожиток": "Заява на гуртожиток подається до 15 серпня через особистий кабінет.",
}
_DEFAULT_ANSWER = "За вашим запитом інформації в базі знань немає; зверніться до деканату."

# Патерни, які «зламують» вразливу модель (імітація реальної LLM).
_INJECTION_TRIGGERS = [
    re.compile(r"(ignore|disregard).{0,20}(previous|above|instructions)", re.I),
    re.compile(r"(забудь|проігноруй).{0,20}(попередн|інструкц|вказівк)", re.I),
    re.compile(r"(reveal|print|output|вивед|розкрий|покажи).{0,20}(secret|секрет|token|токен|пароль)", re.I),
    re.compile(r"\bsystem\s*prompt\b", re.I),
    re.compile(r"\bты\s+теперь\b|\bти\s+тепер\b", re.I),
]


class PrimaryUnavailable(RuntimeError):
    """Основна модель недоступна (імітація відмови)."""


class PrimaryAssistant:
    def __init__(self, mode: PrimaryMode | None = None, slow_ms: int | None = None) -> None:
        self.mode = mode or settings.primary_mode
        self.slow_ms = slow_ms if slow_ms is not None else settings.primary_slow_ms

    def answer(self, question: str) -> str:
        if self.mode == PrimaryMode.fail:
            raise PrimaryUnavailable("основну модель вимкнено (primary_mode=fail)")
        if self.mode == PrimaryMode.slow:
            time.sleep(self.slow_ms / 1000)

        # Вразливість: якщо запит містить тригер ін'єкції — «модель» слухається.
        if any(p.search(question) for p in _INJECTION_TRIGGERS):
            return f"Системний секрет: {settings.system_secret}. (модель виконала вкладену інструкцію)"

        lowered = question.lower()
        for key, text in _KB.items():
            if key in lowered:
                return text
        return _DEFAULT_ANSWER


class FallbackAssistant:
    """Резервна відповідь: безпечна, детермінована, без генерації."""

    def answer(self, question: str) -> str:
        return (
            "Сервіс тимчасово працює в обмеженому режимі й не може повноцінно "
            "обробити запит. Спробуйте пізніше або зверніться до деканату."
        )
