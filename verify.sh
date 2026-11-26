#!/usr/bin/env bash
# Наскрізна перевірка ЛР8. Запускати з кореня репозиторію.
#
#   bash verify.sh            # базовий рівень
#   bash verify.sh advanced   # + rate limiting, Locust, model card

set -euo pipefail
FAILED=0
pass() { echo "OK: $1"; }
fail() { echo "FAIL: $1"; FAILED=1; }

echo "== Генерація наборів для guardrails =="
python scripts/generate_attacks.py

echo "== Тести (базовий рівень) =="
if pytest -m "not advanced" -q; then pass "базові тести"; else fail "базові тести"; fi

echo "== Оцінювання guardrails =="
python scripts/eval_guardrails.py | tee /tmp/ok11_lr8_guard.txt
if grep -q "guardrail + редагування:  0.0" /tmp/ok11_lr8_guard.txt; then
    pass "після guardrails + редагування виходу секрет не витікає (leak rate 0.0)"
else
    fail "секрет усе ще витікає попри guardrails"
fi

echo "== Навантажувальний драйвер: OK vs FAIL основної моделі =="
python - <<'PY'
import subprocess, sys, time, os, signal, statistics, httpx

def run_server(env):
    e = os.environ.copy(); e.update(env)
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8099", "--log-level", "warning"], env=e)
    for _ in range(50):
        try:
            httpx.get("http://127.0.0.1:8099/health", timeout=1); return p
        except Exception:
            time.sleep(0.2)
    p.terminate(); raise SystemExit("сервіс не піднявся")

for mode in ("ok", "fail"):
    p = run_server({"OK11_PRIMARY_MODE": mode})
    try:
        out = subprocess.run([sys.executable, "scripts/loadtest.py", "--url", "http://127.0.0.1:8099/ask", "--n", "120", "--c", "12"], capture_output=True, text=True)
        print(f"--- primary_mode={mode} ---"); print(out.stdout.strip())
    finally:
        p.terminate(); p.wait()
PY
pass "навантажувальний драйвер відпрацював для обох режимів"

if [ "${1:-}" = "advanced" ]; then
    echo "== Тести (поглиблений рівень) =="
    if pytest -m advanced -q; then pass "поглиблені тести"; else fail "поглиблені тести"; fi

    echo "== Model card =="
    if python scripts/build_model_card.py && [ -f MODEL_CARD.md ] && ! grep -q "{{" MODEL_CARD.md; then
        pass "MODEL_CARD.md згенеровано без незаповнених плейсхолдерів"
    else
        fail "MODEL_CARD.md не згенеровано коректно"
    fi

    echo "== Locust (10 с, headless) =="
    python -m uvicorn app.main:app --port 8098 --log-level warning &
    UV=$!
    sleep 3
    if locust -f loadtest/locustfile.py --headless -u 20 -r 10 -t 10s -H http://127.0.0.1:8098 --only-summary; then
        pass "Locust-сценарій виконався"
    else
        fail "Locust-сценарій впав"
    fi
    kill $UV 2>/dev/null || true
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "УСІ АВТОМАТИЧНІ ПЕРЕВІРКИ ПРОЙДЕНО"; exit 0
else
    echo "Є ПОМИЛКИ — див. FAIL вище"; exit 1
fi
