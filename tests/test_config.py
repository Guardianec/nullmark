import json

import pytest
from pydantic import ValidationError

from nullmark.config import ExperimentConfig, load_config
from nullmark.datasets import load_prompts
from nullmark.experiments.runner import sample_seed


def test_documented_configs():
    from pathlib import Path

    for path in Path("configs/experiments").glob("*.yaml"):
        assert load_config(path).random_keys >= 2


@pytest.mark.parametrize(
    "data",
    [
        {"random_keys": 0},
        {"random_keys": "2"},
        {"seed": -1},
        {"unknown": 1},
        {"model": {"temperature": 0}},
        {"model": {"max_new_tokens": 0}},
        {"model": {"name": "gpt2"}},
        {"model": {"name": "gpt2", "revision": "main"}},
        {"dataset": {"source": "jsonl"}},
        {"dataset": {"path": "prompts.jsonl"}},
        {"synthid": {"threshold": float("nan")}},
        {"kgw": {"bias": float("inf")}},
        {"kgw": {"threshold": float("inf")}},
        {"kgw": {"greenlist_ratio": 1.0}},
        {"synthid": {"keys": [123]}},
        {"purpose": "benchmark"},
    ],
)
def test_invalid_configs(data):
    with pytest.raises(ValidationError):
        ExperimentConfig.model_validate(data)


def test_seed_derivation_is_stable():
    assert sample_seed(42, "essay", 0) == sample_seed(42, "essay", 0)
    assert len({sample_seed(42, p, i) for p in ("a", "b") for i in range(3)}) == 6


def test_prompts_are_identified_and_extensible(tmp_path):
    from nullmark.config import DatasetConfig

    prompts, digest = load_prompts(DatasetConfig(sample_count=8), tmp_path)
    assert len({p.style for p in prompts}) == 8
    assert len(digest) == 64
    (tmp_path / "prompts.jsonl").write_text(json.dumps({"id": "a", "style": "x", "text": "Hello"}))
    selected, _ = load_prompts(
        DatasetConfig(source="jsonl", path="prompts.jsonl", sample_count=1),
        tmp_path,
    )
    assert selected[0].text == "Hello"
    (tmp_path / "prompts.jsonl").write_text(json.dumps({"id": 123, "style": "x", "text": "Hi"}))
    with pytest.raises(ValueError, match="string id"):
        load_prompts(DatasetConfig(source="jsonl", path="prompts.jsonl", sample_count=1), tmp_path)
    with pytest.raises(ValueError, match="dataset size"):
        load_prompts(DatasetConfig(sample_count=9), tmp_path)
