"""
Pydantic-схеми контракту захищеного сервісу ЛР8.
Цей файл видається готовим — редагувати не потрібно.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=4000,  # жорсткіша межа — у guardrails (Settings.max_input_chars)
        description="Запит користувача природною мовою.",
        examples=["Які документи потрібні для вступу?"],
    )


class AskResponse(BaseModel):
    answer: str = Field(..., description="Відповідь сервісу (уже після редагування виходу).")
    degraded: bool = Field(
        ..., description="True, якщо відповідь дала резервна модель (основна недоступна)."
    )
    source: str = Field(..., description="Хто відповів: 'primary' або 'fallback'.")


class BlockedResponse(BaseModel):
    detail: str = Field(..., description="Причина, з якої запит відхилено guardrails.")
    matched_rule: str | None = Field(None, description="Яке саме правило спрацювало.")


class HealthResponse(BaseModel):
    status: str
    primary_mode: str
    breaker_state: str
