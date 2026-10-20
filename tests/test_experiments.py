import json

import pytest

from nullmark.config import DatasetConfig, ExperimentConfig, ModelConfig
from nullmark.evaluation.metrics import detection_metrics
from nullmark.experiments.runner import read_jsonl, run, run_experiment


def test_end_to_end_and_private_replay(tmp_path):
    config = ExperimentConfig(
        random_keys=2,
        dataset=DatasetConfig(sample_count=1),
        model=ModelConfig(max_new_tokens=64),
    )
    first = run(config, base=tmp_path, output=tmp_path / "first")
    replay = run_experiment(
        first / "config.resolved.yaml",
        output=tmp_path / "replay",
        secrets_path=first / "private" / "secrets.json",
    )
    assert read_jsonl(first / "public_samples.jsonl") == read_jsonl(replay / "public_samples.jsonl")
    assert read_jsonl(first / "evaluation.jsonl") == read_jsonl(replay / "evaluation.jsonl")
    samples = read_jsonl(first / "public_samples.jsonl")
    assert len(samples) == 6
    assert len(read_jsonl(first / "evaluation.jsonl")) == 8
    assert all(set(s) == {"sample_id", "prompt", "text"} for s in samples)
    metrics = json.loads((first / "metrics.json").read_text())
    assert metrics["samples"] == 6 and metrics["generation_failures"] == 0
    assert metrics["detection_failures"] == metrics["roundtrip_mismatches"] == 0
    for data in metrics["detectors"].values():
        assert data["watermarked"] == data["unwatermarked"] == 2
        assert len(data["by_key"]) == 2
    from nullmark.evaluation.secrets import KeyStore

    keys = KeyStore.load(first / "private" / "secrets.json")
    public = "\n".join(p.read_text("utf-8") for p in first.iterdir() if p.is_file())
    assert keys.master.hex() not in public
    for i in range(2):
        for name in ("synthid", "kgw"):
            for value in keys.derive(name, i).values():
                for scalar in value if isinstance(value, list) else [value]:
                    assert str(scalar) not in public
    assert "\nkeys:" not in (first / "config.resolved.yaml").read_text()
    with pytest.raises(FileExistsError):
        run(config, base=tmp_path, output=first)


def test_failures_are_counted_without_secret_exception_text(tmp_path, monkeypatch):
    from nullmark.models import CausalModel

    def fail(*args, **kwargs):
        raise RuntimeError("private secret 123456789")

    monkeypatch.setattr(CausalModel, "generate", fail)
    path = run(
        ExperimentConfig(random_keys=1, dataset=DatasetConfig(sample_count=1)),
        base=tmp_path,
        output=tmp_path / "failed",
    )
    metrics = json.loads((path / "metrics.json").read_text())
    assert metrics["generation_failures"] == 3
    assert metrics["samples"] == 0
    assert "123456789" not in (path / "failures.jsonl").read_text()


def test_metrics_include_abstentions_and_empty_groups():
    assert detection_metrics([])["accuracy"] is None
    result = detection_metrics(
        [
            {"watermarked": True, "detection": {"prediction": True, "score": 5}},
            {"watermarked": False, "detection": {"prediction": False, "score": 0}},
            {"watermarked": True, "detection": {"prediction": None, "score": None}},
        ]
    )
    assert result["true_positive_rate"] == result["accuracy"] == 1
    assert result["false_positive_rate"] == 0
    assert result["abstentions"] == 1
