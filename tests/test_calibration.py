import json
import math
import warnings
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import torch
import yaml

from nullmark.datasets import Prompt
from nullmark.evaluation.calibration import (
    CalibratedDetector,
    conditions,
    empirical_threshold,
    require_detected_baseline,
    require_frozen_evaluator,
    token_diagnostic,
    uncalibrated,
)
from nullmark.evaluation.inspection import inspect_tokens
from nullmark.evaluation.secrets import key_reference
from nullmark.experiments.calibration import (
    CalibrationConfig,
    evaluate_rows,
    rate,
    run_calibration,
    split_prompts,
)
from nullmark.models import Generation
from nullmark.watermark.base import DetectionResult
from nullmark.watermark.registry import load_scheme
from nullmark.watermark.synthid import mean_score


def result(score, count=128, statistic="raw_mean"):
    return DetectionResult(score, None, 0.6, statistic, count)


def fitted(context=None, **kwargs):
    with pytest.warns(UserWarning, match="tail samples"):
        return CalibratedDetector.fit(
            scheme="synthid",
            statistic="raw_mean",
            clean=[result(i / 200) for i in range(100)],
            target_fpr=0.01,
            context=context or {"model": "test"},
            dataset_hash="a" * 64,
            **kwargs,
        )


@pytest.mark.parametrize(
    "alpha,n,threshold", [(0.01, 100, 99), (0.05, 100, 95), (0.001, 1000, 999)]
)
def test_finite_sample_order_statistic(alpha, n, threshold):
    with warnings.catch_warnings(record=True) as emitted:
        op = empirical_threshold(list(map(float, range(n))), alpha)
    assert bool(emitted) == (n * alpha < 5)
    assert op.supported
    assert op.empirical_threshold == threshold
    assert op.observed_calibration_fpr <= alpha
    with warnings.catch_warnings(record=True):
        assert empirical_threshold(list(reversed(list(map(float, range(n))))), alpha) == op


def test_ties_are_conservative_and_small_sets_are_not_supported():
    with pytest.warns(UserWarning):
        assert empirical_threshold([0.5] * 100, 0.01).observed_calibration_fpr == 0
    with pytest.warns(UserWarning, match="Too few"):
        op = empirical_threshold([0.1] * 20, 0.01)
    assert not op.supported and op.empirical_threshold == 0.1


@pytest.mark.parametrize(
    "scores,alpha",
    [([], 0.01), ([math.nan], 0.01), ([math.inf], 0.01), ([1.0], 0), ([1.0], 1), ([1.0], -1)],
)
def test_invalid_calibration_rejected(scores, alpha):
    with pytest.raises(ValueError):
        empirical_threshold(scores, alpha)


def test_frozen_artifact_roundtrip_integrity_and_conditions(tmp_path):
    artifact = fitted()
    path = tmp_path / "calibration.json"
    artifact.save(path)
    restored = CalibratedDetector.load(path)
    assert restored == artifact
    assert restored.to_dict()["operating_point"]["number_of_clean_samples"] == 100
    with pytest.raises(FrozenInstanceError):
        restored.minimum_usable_tokens = 1
    with pytest.raises(ValueError, match="does not match"):
        restored.evaluate(result(0.8), context={"model": "other"})
    with pytest.raises(ValueError, match="statistic"):
        restored.evaluate(result(0.8, statistic="weighted_mean"), context={"model": "test"})
    data = restored.to_dict()
    data["operating_point"]["empirical_threshold"] = 0.1
    with pytest.raises(ValueError, match="integrity"):
        CalibratedDetector.from_dict(data)


@pytest.mark.parametrize(
    "score,count,state",
    [
        (0.8, 128, "DETECTED"),
        (0.1, 128, "NOT DETECTED"),
        (0.495, 128, "NOT DETECTED"),
        (0.8, 10, "INSUFFICIENT EVIDENCE"),
        (0.8, 512, "INSUFFICIENT EVIDENCE"),
        (None, 128, "INSUFFICIENT EVIDENCE"),
    ],
)
def test_three_state_and_observed_length_support(score, count, state):
    d = fitted().evaluate(result(score, count), context={"model": "test"})
    assert d["state"] == state
    assert (
        d["prediction"] is None if state == "INSUFFICIENT EVIDENCE" else d["prediction"] is not None
    )


def test_uncalibrated_and_future_guard():
    d = uncalibrated(result(0.9))
    assert d["prediction"] is None and d["threshold"] is None
    assert d["state"] == "INSUFFICIENT EVIDENCE" and d["decision_scope"] == "score_only"
    with pytest.raises(ValueError, match="calibration"):
        require_frozen_evaluator(None, context={})
    detector = fitted()
    assert require_frozen_evaluator(detector, context={"model": "test"}) is detector
    with pytest.warns(UserWarning):
        small = CalibratedDetector.fit(
            scheme="synthid",
            statistic="raw_mean",
            clean=[result(0.5)],
            target_fpr=0.01,
            context={},
            dataset_hash="x",
        )
    with pytest.raises(ValueError):
        require_frozen_evaluator(small, context={})
    assert small.evaluate(result(0.9), context={})["status"] == "calibration_sample_count"


@pytest.mark.parametrize(
    "score,count,eligible",
    [(0.8, 128, True), (0.1, 128, False), (0.8, 1, False), (None, 128, False)],
)
def test_future_evasion_requires_a_detected_baseline(score, count, eligible):
    detector = fitted()
    if eligible:
        assert (
            require_detected_baseline(detector, result(score, count), context={"model": "test"})[
                "state"
            ]
            == "DETECTED"
        )
    else:
        with pytest.raises(ValueError, match="originally detected"):
            require_detected_baseline(detector, result(score, count), context={"model": "test"})
    legacy = DetectionResult(0.9, True, 0.6, "raw_mean", 128)
    assert legacy.state == "INSUFFICIENT EVIDENCE"


def test_split_replay_disjoint_text_and_style_coverage():
    prompts = [
        Prompt(f"{style}-{i}", str(style), f"topic {style} {i}")
        for style in range(8)
        for i in range(25)
    ]
    splits = split_prompts(prompts, 100, 100, 42)
    assert splits == split_prompts(list(reversed(prompts)), 100, 100, 42)
    assert {p.id for p in splits["calibration"]}.isdisjoint(p.id for p in splits["evaluation"])
    assert {p.text for p in splits["calibration"]}.isdisjoint(p.text for p in splits["evaluation"])
    for selected in splits.values():
        assert len(selected) == 100 and len({p.style for p in selected}) == 8
    with pytest.raises(ValueError, match="duplicate"):
        split_prompts([*prompts, Prompt("duplicate", "x", prompts[0].text)], 2, 2, 42)
    with pytest.raises(ValueError, match="not enough"):
        split_prompts(prompts, 101, 100, 42)


def test_weighted_mean_matches_upstream_formula():
    # Explicit independent layer weights, masking a deliberately extreme token.
    values = torch.tensor([[[1, 0, 0], [0, 0, 0], [0, 1, 1]]])
    mask = torch.tensor([[True, False, True]])
    assert mean_score(values, mask, "raw_mean") == pytest.approx(0.5)
    assert mean_score(values, mask, "weighted_mean") == pytest.approx((10 + 5.5 + 1) / (2 * 16.5))
    assert mean_score(
        torch.tensor([[[1, 0, 0]]]), torch.tensor([[True]]), "weighted_mean"
    ) == pytest.approx(10 / 16.5)
    with pytest.raises(ValueError):
        mean_score(values, mask, "invented")


@pytest.mark.parametrize("statistic", ["raw_mean", "weighted_mean"])
def test_synthid_modes_and_trace(statistic, model, config, keys):
    config = config.model_copy(
        update={"synthid": config.synthid.model_copy(update={"statistic": statistic})}
    )
    scheme = load_scheme("synthid", model, config, keys.derive("synthid", 0))
    marked = scheme.generate(model, "word1 word2 word3", seed=123)
    plain = model.generate("word1 word2 word3", seed=123)
    positive = scheme.detect(marked.text)
    assert positive.statistic == statistic
    assert positive.score > scheme.detect(plain.text).score
    assert (
        "weighted mean" in scheme.metadata()["detector"]
        if statistic == "weighted_mean"
        else "raw mean-g" in scheme.metadata()["detector"]
    )
    trace = inspect_tokens(model, scheme, model.encode(marked.text))
    assert trace[-1].synthid.cumulative_score == pytest.approx(positive.score, abs=1e-7)


@pytest.mark.parametrize("name", ["synthid", "kgw"])
def test_native_visible_diagnostic_and_authority(name, model, config, keys):
    scheme = load_scheme(name, model, config, keys.derive(name, 0))
    generated = scheme.generate(model, "word1 word2", seed=123)
    exact = token_diagnostic(scheme, generated, model)
    assert exact["token_roundtrip_exact"] and exact["score_delta"] == 0
    changed = Generation("word1 word2 word3 word4 word5 word6", generated.token_ids, 1.0)
    diag = token_diagnostic(scheme, changed, model)
    assert not diag["token_roundtrip_exact"]
    assert diag["native_score"] == exact["native_score"]
    assert diag["visible_score"] == scheme.detect(changed.text).score
    assert diag["detection"]["score"] == diag["visible_score"]


@pytest.mark.parametrize("change", ["temperature", "depth", "key", "model"])
def test_model_key_sampling_depth_specificity(change, model, config, keys):
    scheme = load_scheme("synthid", model, config, keys.derive("synthid", 0))
    context = conditions(model, scheme, key_reference(keys, "synthid", 0))
    artifact = fitted(context)
    other = json.loads(json.dumps(context))
    if change == "temperature":
        other["generation"]["temperature"] = 0.8
    elif change == "depth":
        other["watermark"]["depth"] = 20
    elif change == "key":
        other["key_ref"] = key_reference(keys, "synthid", 1)
    else:
        other["model"]["revision"] = "other"
    with pytest.raises(ValueError):
        artifact.require_compatible(other)
    public = json.dumps(artifact.to_dict())
    assert keys.master.hex() not in public and '"keys"' not in public


def test_metrics_do_not_count_abstentions_as_negatives():
    artifact = fitted()
    rows = [
        {"watermarked": marked, "detection": result(score, count).to_dict()}
        for marked, score, count in [
            (True, 0.8, 128),
            (True, 0.8, 1),
            (False, 0.1, 128),
            (False, 0.9, 1),
        ]
    ]
    metrics = evaluate_rows(rows, artifact, {"model": "test"})
    assert metrics["tpr"]["value"] == 1 and metrics["fpr"]["value"] == 0
    assert metrics["abstention_rate"]["value"] == 0.5
    assert metrics["marked_detection_yield"]["value"] == 0.5
    assert metrics["usable_sample_count"] == 2 and metrics["precision"] is None
    assert rate(0, 100)["wilson95"][1] > 0.03
    assert rate(0, 0)["value"] is None


def test_calibration_cli_workflow_and_no_eval_leakage(tmp_path, monkeypatch, model):
    import nullmark.experiments.calibration as module

    # Fast real offline generation; no native dependency or downloads in CI.
    monkeypatch.setattr(module, "load_model", lambda _: model)
    monkeypatch.setattr(model, "close", lambda: None)
    dataset = [dict(id=f"p{i}", style=str(i % 8), text=f"word{i} word2") for i in range(16)]
    (tmp_path / "prompts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in dataset))
    cfg = CalibrationConfig(
        calibration_count=8,
        evaluation_count=8,
        depths=[10],
        minimum_usable_tokens=1,
        dataset={"source": "jsonl", "path": "prompts.jsonl", "sample_count": 16},
    )
    path = tmp_path / "study.yaml"
    path.write_text(yaml.safe_dump(cfg.model_dump()))
    fits = []
    original = CalibratedDetector.fit.__func__

    def fit(cls, **kwargs):
        # The first fit happens before any held-out generation is written.
        rows = (tmp_path / "output/scores.jsonl").read_text().splitlines()
        assert all(json.loads(r)["split"] == "calibration" for r in rows)
        fits.append(len(kwargs["clean"]))
        return original(cls, **kwargs)

    monkeypatch.setattr(CalibratedDetector, "fit", classmethod(fit))
    with pytest.warns(UserWarning):
        output = run_calibration(path, output=tmp_path / "output")
    assert fits == [8, 8, 8]
    assert json.loads((output / "manifest.json").read_text())["completed"]
    reports = json.loads((output / "metrics.json").read_text())["reports"]
    assert len(reports) == 3
    assert all(r["tpr"]["value"] is None for r in reports.values())
    assert len((output / "samples.jsonl").read_text().splitlines()) == 48
    assert len(list(output.glob("*.calibration.json"))) == 3
    decisions = [
        json.loads(line) for line in (output / "evaluation.jsonl").read_text().splitlines()
    ]
    assert len(decisions) == 48
    assert all(r["detection"]["prediction"] is None for r in decisions)
    assert all(r["detection"]["calibration_id"] for r in decisions)
    assert (
        Path("configs/experiments/001_watermark_reproducibility.yaml").read_text().find("depth: 10")
        >= 0
    )
