"""Opt-in check of a real pretrained model, never downloaded in default CI."""

import os
from pathlib import Path

import pytest

from nullmark.config import load_config
from nullmark.models import CausalModel
from nullmark.watermark.registry import load_scheme


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("NULLMARK_PRETRAINED") != "1", reason="set NULLMARK_PRETRAINED=1"
)
def test_pretrained_generation_and_detection(keys):
    config = load_config(Path("configs/experiments/001_watermark_reproducibility.yaml"))
    model = CausalModel(config.model)
    prompt = "The history of public libraries begins with"
    plain = model.generate(prompt, seed=123)
    for name in ("synthid", "kgw"):
        scheme = load_scheme(name, model, config, keys.derive(name, 0))
        marked = scheme.generate(model, prompt, seed=123)
        assert scheme.detect(marked.text).score > scheme.detect(plain.text).score
