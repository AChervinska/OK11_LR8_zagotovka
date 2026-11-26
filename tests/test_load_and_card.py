"""
Структурні тести навантажувального сценарію та model card — крок 10-12
(поглиблений рівень). Реальний load-тест виконує verify.sh advanced.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.advanced

ROOT = Path(__file__).resolve().parent.parent


def test_locustfile_defines_httpuser_with_task():
    import importlib.util

    spec = importlib.util.spec_from_file_location("locustfile", ROOT / "loadtest" / "locustfile.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    from locust import HttpUser

    user_classes = [
        obj for obj in vars(mod).values()
        if isinstance(obj, type) and issubclass(obj, HttpUser) and obj is not HttpUser
    ]
    assert user_classes, "у locustfile немає жодного HttpUser"
    tasks = getattr(user_classes[0], "tasks", None) or [
        m for m in vars(user_classes[0]).values() if getattr(m, "locust_task_weight", None)
    ]
    assert tasks, "у класі користувача немає жодного @task"


def test_build_model_card_fills_template(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    # дані для eval_guardrails
    import subprocess

    subprocess.run([sys.executable, "scripts/generate_attacks.py"], check=True, cwd=ROOT)
    subprocess.run([sys.executable, "scripts/build_model_card.py"], check=True, cwd=ROOT)

    card = (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")
    assert "{{" not in card, "у картці лишились незаповнені плейсхолдери"
    assert "recall" in card
    assert "EU AI Act" in card


def test_compliance_map_covers_key_articles():
    text = (ROOT / "compliance_map.md").read_text(encoding="utf-8")
    for article in ["Ст. 9", "Ст. 12", "Ст. 13", "Ст. 14", "Ст. 15"]:
        assert article in text
