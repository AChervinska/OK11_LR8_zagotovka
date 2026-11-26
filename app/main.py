"""
Захищений сервіс ЛР8: rate limit -> вхідні guardrails -> стійкий виклик
моделі (circuit breaker + fallback) -> редагування виходу.

TODO: тіло ендпоінта /ask — крок 7 (базовий) і крок 9 (rate limit,
поглиблений).
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from app.assistant import FallbackAssistant, PrimaryAssistant
from app.circuit_breaker import CircuitBreaker
from app.config import Settings
from app.guardrails import check_input, redact_output
from app.rate_limit import TokenBucketLimiter
from app.reliability import answer_with_resilience
from app.schemas import AskRequest, AskResponse, HealthResponse

settings = Settings()
logging.basicConfig(level="INFO")
logger = logging.getLogger("ok11.lr8")

primary = PrimaryAssistant()
fallback = FallbackAssistant()
breaker = CircuitBreaker()
limiter = TokenBucketLimiter()


def client_key(request: Request) -> str:
    return request.headers.get("x-api-key") or (request.client.host if request.client else "anon")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("primary_mode=%s breaker(threshold=%s, cooldown=%ss)",
                settings.primary_mode.value, settings.breaker_fail_threshold, settings.breaker_cooldown_s)
    yield


app = FastAPI(title="ЛР8 · Надійність та безпека сервісу ШІ",
              version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok", primary_mode=settings.primary_mode.value, breaker_state=breaker.state
    )


@app.post("/ask", response_model=AskResponse, responses={403: {}, 429: {}})
async def ask(
    request: AskRequest,
    response: Response,
    http_request: Request
) -> AskResponse:

    request_id = str(uuid.uuid4())[:8]

    if settings.rate_limit_enabled:
        decision = limiter.take(client_key(http_request))

        if not decision.allowed:
            raise HTTPException(
                status_code=429,
                detail="Перевищено ліміт запитів",
                headers={
                    "Retry-After": str(decision.retry_after_s)
                }
            )

    guard = check_input(request.question)

    if not guard.allowed:
        logger.warning("request_id=%s blocked", request_id)
        raise HTTPException(
            status_code=403,
            detail=guard.reason
        )

    result = await run_in_threadpool(
        answer_with_resilience,
        request.question,
        primary,
        fallback,
        breaker
    )

    safe_answer = redact_output(result.answer)

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request_id=%s degraded=%s source=%s",
        request_id,
        result.degraded,
        result.source
    )

    return AskResponse(
        answer=safe_answer,
        degraded=result.degraded,
        source=result.source
    )
