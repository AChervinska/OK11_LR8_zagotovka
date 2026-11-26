"""
Складання model card із шаблону MODEL_CARD.template.md і результатів
scripts/eval_guardrails.py — крок 12, поглиблений рівень.

Готовий скрипт (не редагувати).

    python scripts/build_model_card.py   # -> MODEL_CARD.md
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings
from scripts.eval_guardrails import evaluate


def main() -> None:
    settings = Settings()
    report = evaluate()
    template = Path("MODEL_CARD.template.md").read_text(encoding="utf-8")

    values = {
        "date": dt.date.today().isoformat(),
        "n_attacks": report["n_attacks"],
        "n_attack_classes": len(report["recall_per_class"]),
        "n_benign": report["n_benign"],
        "recall": report["recall"],
        "precision": report["precision"],
        "fpr": report["fpr"],
        "leak_none": report["leak_rate_no_defense"],
        "leak_input": report["leak_rate_input_guard_only"],
        "leak_full": report["leak_rate_input_guard_plus_output_redaction"],
        "breaker_threshold": settings.breaker_fail_threshold,
        "breaker_cooldown": settings.breaker_cooldown_s,
    }
    for key, val in values.items():
        template = template.replace("{{" + key + "}}", str(val))

    Path("MODEL_CARD.md").write_text(template, encoding="utf-8")
    print("MODEL_CARD.md згенеровано:")
    print("  recall =", report["recall"], " precision =", report["precision"], " fpr =", report["fpr"])
    print("  leak:", report["leak_rate_no_defense"], "->",
          report["leak_rate_input_guard_only"], "->",
          report["leak_rate_input_guard_plus_output_redaction"])


if __name__ == "__main__":
    main()
