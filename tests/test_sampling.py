import json
from pathlib import Path

import pytest
import torch
import yaml
from pydantic import ValidationError

from nullmark.config import DatasetConfig, ExperimentConfig, ModelConfig, load_config
from nullmark.experiments.runner import run


@pytest.mark.parametrize(
    "update",
    [{"top_k": -1}, {"top_k": 1.5}, {"top_p": 0.0}, {"top_p": 1.01}, {"top_p": float("nan")}],
)
def test_sampling_validation(update):
    with pytest.raises(ValidationError):
        ModelConfig(**update)


def test_historical_defaults_and_explicit_experiment_pins():
    defaults = ModelConfig()
    assert (defaults.temperature, defaults.top_k, defaults.top_p) == (1.0, 0, 1.0)
    config = load_config(Path("configs/experiments/001_watermark_reproducibility.yaml"))
    assert (config.model.temperature, config.model.top_k, config.model.top_p) == (1.0, 0, 1.0)
    explicit = yaml.safe_load(
        Path("configs/experiments/001_watermark_reproducibility.yaml").read_text()
    )
    assert {k: explicit["model"][k] for k in ("temperature", "top_k", "top_p")} == {
        "temperature": 1.0,
        "top_k": 0,
        "top_p": 1.0,
    }


def test_sampling_reaches_transformers_and_metadata(model, monkeypatch):
    settings = model.settings.model_copy(update={"temperature": 0.8, "top_k": 40, "top_p": 0.95})
    monkeypatch.setattr(model, "settings", settings)

    def generate(**kwargs):
        assert kwargs["temperature"] == 0.8 and kwargs["top_k"] == 40 and kwargs["top_p"] == 0.95
        return torch.cat((kwargs["input_ids"], torch.tensor([[2, 3]])), dim=1)

    monkeypatch.setattr(model.model, "generate", generate)
    result = model.generate("word1", seed=123)
    assert result.token_ids == [2, 3] and result.prompt_token_ids == [2]
    assert model.metadata()["sampling"] == {"temperature": 0.8, "top_k": 40, "top_p": 0.95}


def test_resolved_sampling_provenance(tmp_path):
    config = ExperimentConfig(
        random_keys=1,
        dataset=DatasetConfig(sample_count=1),
        model=ModelConfig(max_new_tokens=16, temperature=0.8, top_k=40, top_p=0.95),
    )
    output = run(config, base=tmp_path, output=tmp_path / "run")
    resolved = load_config(output / "config.resolved.yaml")
    assert resolved.model.top_k == 40 and resolved.model.top_p == 0.95
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["model"]["backend"] == "transformers"
    assert manifest["sampling"] == {"temperature": 0.8, "top_k": 40, "top_p": 0.95, "seed": 42}
    for row in map(json.loads, (output / "generation.jsonl").read_text().splitlines()):
        assert row["sampling"] == manifest["model"]["sampling"]
        assert isinstance(row["seed"], int)


def test_gguf_config_requires_stable_digest():
    with pytest.raises(ValidationError):
        ModelConfig(backend="ollama-gguf", name="local:qwen", revision="main")
    config = ModelConfig(
        backend="ollama-gguf",
        name="local:qwen",
        revision="a" * 64,
        temperature=0.8,
        top_k=40,
        top_p=0.95,
    )
    assert ModelConfig.model_validate_json(config.model_dump_json()) == config
