# ЛР8 · Надійність, безпека та навантажувальне тестування сервісу ШІ

Повний текст інструкції — у файлі `OK11_LR8_Metodychni_vkazivky.docx`
поруч із цим репозиторієм. Цей README — лише навігація по коду.

Робота має **два рівні**:

- **Базовий (обов'язковий)** — кроки 1–8: guardrails на вході, циркуляр-
  ний запобіжник, резервна модель (graceful degradation), редагування
  виходу, простий навантажувальний драйвер. `pytest -m "not advanced"`,
  `bash verify.sh`.
- **Поглиблений (додатково)** — кроки 9–13: rate limiting (token bucket),
  Locust, model card, карта відповідності EU AI Act. `pytest -m advanced`,
  `bash verify.sh advanced`.

## Структура

```
app/
  config.py            — ГОТОВО: налаштування (режим основної моделі, параметри breaker/rate limit)
  schemas.py           — ГОТОВО: контракт /ask
  assistant.py         — ГОТОВО: PrimaryAssistant (вразлива, керовано падає/гальмує) + FallbackAssistant
  guardrails.py        — TODO: check_input(), redact_output()                         (крок 4)
  circuit_breaker.py   — TODO: CircuitBreaker.call/_on_success/_on_failure            (крок 3)
  reliability.py       — TODO: answer_with_resilience()                               (крок 6)
  rate_limit.py        — TODO [поглиблений]: TokenBucketLimiter                       (крок 9)
  main.py              — TODO: тіло ендпоінта /ask                                    (кроки 7, 9)
scripts/
  generate_attacks.py  — ГОТОВО: data/attacks.csv (40, за класами) + data/benign.csv (40)
  eval_guardrails.py   — ГОТОВО: precision/recall/FPR детектора + leak rate
  loadtest.py          — ГОТОВО: простий навантажувальний драйвер (base)
  build_model_card.py  — ГОТОВО [поглиблений]: MODEL_CARD.md із шаблону + метрик
loadtest/locustfile.py — TODO [поглиблений]: сценарій Locust                          (крок 10)
MODEL_CARD.template.md — ГОТОВО [поглиблений]
compliance_map.md      — ГОТОВО [поглиблений]: карта EU AI Act (стовпець «прогалина» — заповнити)
tests/                 — контрактні тести (conftest.py не редагувати)
verify.sh
requirements.txt
pytest.ini
```

## Порядок виконання

**Базовий рівень**

1. `pip install -r requirements.txt`, `python scripts/generate_attacks.py`.
2. `pytest -m "not advanced" -q` — тести падають з `NotImplementedError`.
3. Реалізувати: `circuit_breaker.py` → `guardrails.py` → `reliability.py` → `main.py`.
4. `python scripts/eval_guardrails.py` — метрики детектора й leak rate.
5. `uvicorn app.main:app`, перевірити `/ask` (benign / injection / `OK11_PRIMARY_MODE=fail`).
6. `python scripts/loadtest.py --n 300 --c 20` двічі: з `OK11_PRIMARY_MODE=ok` і `=slow`.
7. `bash verify.sh`.

**Поглиблений рівень (додатково)**

8. Реалізувати `rate_limit.py`, вмикання в `/ask`, `loadtest/locustfile.py`.
9. `locust -f loadtest/locustfile.py --headless -u 50 -r 10 -t 30s -H http://127.0.0.1:8000 --csv results/lr8`.
10. `python scripts/build_model_card.py`, заповнити стовпець «прогалина» в `compliance_map.md`.
11. `bash verify.sh advanced`.

## Типові проблеми

Див. «Типові помилки» методички. Коротко: `_on_failure` має відкривати
коло і в стані HALF_OPEN (не лише в CLOSED при досягненні порогу),
інакше після відновлення одна невдача не поверне сервіс у OPEN.
