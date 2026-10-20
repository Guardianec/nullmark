import json
import os
import subprocess
import sys
from dataclasses import asdict, fields
from pathlib import Path

import pytest

from nullmark.attacks.base import AttackInput, AttackOutput
from nullmark.attacks.baselines import BaselineAttack, validate_output
from nullmark.attacks.text import candidates, distance, words
from nullmark.evaluation.attack_metrics import aggregate, outcome
from nullmark.evaluation.attack_worker import AttackWorker, cache_identity
from nullmark.evaluation.quality import quality_metrics, text_diff
from nullmark.experiments.attacks import validate_disjoint

TEXT = (
    "The useful method often helps people quickly understand important changes. "
    "A simple method usually shows different results because small groups also learn. "
) * 8


class LinguisticModel:
    digest = "a" * 64
    sampling = {"temperature": 0.2}

    def tokenize(self, text):
        return words(text)

    def replacements(self, text, pool, seed):
        from nullmark.attacks.baselines import ALTERNATIVES

        return {m.start(): ALTERNATIVES[m.group()] for m in pool if m.group() in ALTERNATIVES}

    def entropies(self, text, pool):
        return {m.start(): m.start() / 100 for m in pool}

    def paraphrase(self, text, seed):
        return text.replace("useful method", "helpful approach")


@pytest.mark.parametrize("name", ["random_edit", "synonym_replace", "entropy_rewrite"])
@pytest.mark.parametrize("budget", [0.01, 0.02, 0.05, 0.1, 0.2])
def test_sparse_attacks_are_deterministic_and_budgeted(name, budget):
    attack = BaselineAttack(name, budget, None if name == "random_edit" else LinguisticModel())
    sample = AttackInput("x", "Explain changes", TEXT)
    a, b = (attack.transform(sample, seed=7) for _ in range(2))
    assert a.text == b.text
    assert 0 < a.actual_word_edits <= int(len(words(TEXT)) * budget)
    assert a.actual_word_edits == distance(words(TEXT), words(a.text))
    assert a.input_sha256 == b.input_sha256
    assert "score" not in asdict(a)


def test_paraphrase_has_no_fixed_budget():
    out = BaselineAttack("paraphrase", model=LinguisticModel()).transform(
        AttackInput("x", "p", TEXT), seed=3
    )
    assert out.requested_budget is None
    assert out.text != TEXT
    with pytest.raises(ValueError):
        BaselineAttack("paraphrase", 0.05)


def test_high_risk_spans_are_protected():
    text = (
        'Alice said "important useful method". The useful method is not simple. '
        "`important method` https://example.org 2026-10-20 18% test@host.org\n"
        "The useful method often helps people."
    )
    selected = [m.group() for m in candidates(text)]
    assert selected == ["useful", "method", "often", "helps", "people"]


@pytest.mark.parametrize(
    "output",
    [
        "",
        " ",
        "Here is the rewritten text: abc",
        "```abc```",
        "Sure, abc",
        "<think>abc",
        "x" * 1000,
    ],
)
def test_invalid_attack_outputs_rejected(output):
    with pytest.raises(ValueError):
        validate_output("original prose", output)


def test_prompt_echo_rejected_and_valid_text_unchanged():
    with pytest.raises(ValueError):
        validate_output("original prose", "my prompt", "my prompt")
    assert validate_output("original prose", " changed prose \n") == " changed prose \n"


def test_attack_output_contains_only_public_transformation_metadata():
    names = {f.name for f in fields(AttackOutput)}
    assert not names & {"detector", "threshold", "key", "key_ref", "calibration", "score"}


def test_subprocess_worker_cache_and_evaluator_smoke(tmp_path, monkeypatch):
    monkeypatch.setenv("NULLMARK_PRIVATE_MASTER", "must-not-be-forwarded")
    original = subprocess.Popen
    seen = {}

    def capture(*args, **kwargs):
        seen.update(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", capture)
    sample = AttackInput("x", "p", TEXT)
    with AttackWorker(cache=tmp_path / "cache") as worker:
        output = worker.transform(sample, attack="random_edit", budget=0.1, seed=8)
        assert worker.process.pid != os.getpid()
        assert "NULLMARK_PRIVATE_MASTER" not in seen["env"]
        assert Path(seen["cwd"]) != Path.cwd()
        assert not (Path(seen["cwd"]) / "results").exists()
    # Trusted evaluation begins after the worker exits.
    assert quality_metrics(TEXT, output.text, tokenize=words)["word_edits"] > 0
    with AttackWorker(cache=tmp_path / "cache") as worker:
        assert worker.transform(sample, attack="random_edit", budget=0.1, seed=8) == output
        assert worker.process is None
    path = next((tmp_path / "cache").glob("*.json"))
    value = json.loads(path.read_text())
    value["output"]["text"] += " tampered"
    path.write_text(json.dumps(value))
    with AttackWorker(cache=tmp_path / "cache") as worker, pytest.raises(ValueError):
        worker.transform(sample, attack="random_edit", budget=0.1, seed=8)


def test_worker_module_loads_without_evaluator_or_watermark_imports():
    code = (
        "import sys; import nullmark.attacks.worker; "
        "assert not any(n.startswith(('nullmark.evaluation','nullmark.watermark',"
        "'nullmark.models')) for n in sys.modules)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_worker_rejects_private_or_unknown_fields():
    request = {
        "sample": {"sample_id": "x", "prompt": "p", "text": TEXT, "key": "no"},
        "attack": "random_edit",
        "budget": 0.1,
        "seed": 1,
        "model": None,
    }
    run = subprocess.run(
        [sys.executable, "-m", "nullmark.attacks.worker"],
        input=json.dumps(request) + "\n",
        capture_output=True,
        text=True,
        check=True,
    )
    assert "failure" in json.loads(run.stdout)


@pytest.mark.parametrize(
    "field,value",
    [("seed", 2), ("budget", 0.2), ("attack", "paraphrase"), ("model", {"model_digest": "a" * 64})],
)
def test_cache_identity_covers_public_settings(field, value):
    request = {
        "sample": {"sample_id": "x", "prompt": "p", "text": TEXT},
        "seed": 1,
        "budget": 0.1,
        "attack": "random_edit",
        "model": None,
    }
    assert cache_identity(request) != cache_identity({**request, field: value})


def test_quality_metrics_anchors_and_exact_edit_counts():
    original = "In 2026, the useful method retained 18% at https://example.org."
    changed = original.replace("useful", "helpful").replace("18%", "19%")
    quality = quality_metrics(original, changed, tokenize=lambda t: list(t))
    assert quality["word_edits"] == 1
    assert quality["token_edits"] > 1
    assert quality["length_ratio"] == 1
    assert quality["anchors_retained"] == 2 and quality["anchors_total"] == 3
    assert quality["anchors_added"] == 1
    assert quality["semantic_similarity"] is None


def test_diff_reconstructs_original_and_after_with_insert_delete_replace():
    a, b = "The small boat is here.", "A big boat arrived here!"
    diff = text_diff(a, b)
    assert "".join(r["before"] for r in diff) == a
    assert "".join(r["after"] for r in diff) == b
    assert any(r["operation"] == "replace" for r in diff)
    assert text_diff("hello", "hello")[0]["operation"] == "equal"


@pytest.mark.parametrize(
    "before,after,expected",
    [
        ("DETECTED", "NOT DETECTED", "EVASION"),
        ("DETECTED", "INSUFFICIENT EVIDENCE", "ABSTENTION"),
        ("NOT DETECTED", "NOT DETECTED", "BASELINE MISS"),
        ("INSUFFICIENT EVIDENCE", "NOT DETECTED", "BASELINE ABSTENTION"),
    ],
)
def test_evasion_definition(before, after, expected):
    assert outcome({"state": before}, {"state": after}) == expected


def test_aggregate_keeps_failures_and_abstention_and_quality_denominators():
    before = {"state": "DETECTED", "score": 5.0}
    baseline = [{"scheme": "kgw", "before": before}] * 4
    rows = []
    for state, sim in (
        ("NOT DETECTED", 0.96),
        ("DETECTED", 0.93),
        ("INSUFFICIENT EVIDENCE", 0.99),
        (None, None),
    ):
        after = {"state": state, "score": 1.0} if state else None
        rows.append(
            {
                "scheme": "kgw",
                "attack": "paraphrase",
                "budget": None,
                "before": before,
                "after": after,
                "runtime_seconds": 1.0,
                "outcome": outcome(before, after, failure=not state),
                "quality": {
                    "semantic_similarity": sim,
                    "word_edit_fraction": 0.2,
                    "token_edit_fraction": 0.3,
                    "length_ratio": 1.0,
                    "lexical_similarity": 0.8,
                    "anchor_preservation": 1.0,
                },
            }
        )
    group = aggregate(baseline, rows)["groups"][0]
    assert group["evasion_rate"] == group["abstention_rate"] == 0.25
    assert group["completion_rate"] == 0.75
    assert group["quality_conditioned"]["0.95"]["denominator"] == 2
    assert group["quality_conditioned"]["0.95"]["rate"] == 0.5
    assert "p25" in group["distributions"]["word_edit_fraction"]


def test_new_corpus_is_unique_and_disjoint():
    from nullmark.config import DatasetConfig
    from nullmark.datasets import load_prompts

    prompts, _ = load_prompts(
        DatasetConfig(source="jsonl", path="attacks-v1.jsonl", sample_count=240),
        Path("configs/benchmarks"),
    )
    calibration = [
        json.loads(line)
        for line in Path("configs/calibration/prompts-v1.jsonl").read_text("utf-8").splitlines()
    ]
    validate_disjoint(prompts, calibration)
    assert len(prompts) == 240 and len({p.style for p in prompts}) == 8
    with pytest.raises(ValueError):
        validate_disjoint(prompts, [asdict(prompts[0])])
