from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from nullmark.attacks.base import AttackInput
from nullmark.attacks.skd import settings, transform
from nullmark.playground.app import create_app
from nullmark.playground.service import AttackSettings, PlaygroundSettings


def test_skd_controls_and_evaluator_boundary_label():
    client = TestClient(create_app(), base_url="http://127.0.0.1")
    page = client.get("/").text
    for text in (
        'value="skd"',
        'id="skd-edits"',
        'id="skd-candidate"',
        'id="skd-source"',
        'id="skd-selected-edits"',
        "Evaluator result — not available to SKD",
    ):
        assert text in page
    script = client.get("/assets/app.js").text
    assert "CandidateInspector(data)" in script and "normalized_${key}" in script
    assert "candidate exhaustion" in script


def test_skd_api_with_fixture_worker_and_ineligible_baseline(monkeypatch, tmp_path):
    from nullmark.evaluation.attack_worker import AttackWorker
    from nullmark.playground import service

    seen = {}

    def fake(self, sample, **kwargs):
        seen.update(kwargs)
        return transform(
            AttackInput(sample.sample_id, sample.prompt, sample.text),
            method=kwargs["attack"],
            k=kwargs["budget"],
            seed=kwargs["seed"],
            model=SimpleNamespace(digest="a" * 64, sampling={}, tokenize=list),
            artifact=dict(
                config=settings(),
                candidates=[],
                coverage=dict(selectable=0, unique=0, proposed=0),
                selected_ids=[],
                pool_sha256="b" * 64,
            ),
        )

    monkeypatch.setattr(AttackWorker, "transform", fake)
    monkeypatch.setattr(
        service,
        "resolve_model",
        lambda *a: SimpleNamespace(path=Path("model.gguf"), blob_sha256="a" * 64),
    )
    monkeypatch.chdir(tmp_path)
    app = create_app()
    client = TestClient(app, base_url="http://127.0.0.1")
    generated = client.post("/api/generate", json=dict(prompt="word1", max_new_tokens=32)).json()
    response = client.post(
        "/api/attack",
        json=dict(
            generation_id=generated["generation_id"],
            attack="skd",
            edits=5,
            selection="entropy_only",
        ),
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert seen["attack"] == "entropy_only" and seen["budget"] == 5
    assert data["attack"]["skd"]["candidate_exhaustion"]
    assert not data["eligible"] and data["outcome"] == "BASELINE ABSTENTION"


def test_skd_settings_reject_invalid_edit_counts():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AttackSettings(generation_id="a" * 32, attack="skd", edits=4)
    assert PlaygroundSettings(prompt="x").scheme == "kgw"
