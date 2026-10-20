import math

import pytest

from nullmark.watermark.base import WatermarkScheme
from nullmark.watermark.registry import SCHEMES, load_scheme


@pytest.mark.parametrize("name", SCHEMES)
def test_generated_signal_exceeds_plain_and_wrong_key(name, model, config, keys):
    adapter = load_scheme(name, model, config, keys.derive(name, 0))
    wrong_key = load_scheme(name, model, config, keys.derive(name, 1))
    assert isinstance(adapter, WatermarkScheme)
    marked = adapter.generate(model, "Explain a public library.", seed=123)
    plain = model.generate("Explain a public library.", seed=123)
    positive = adapter.detect(marked.text)
    negative = adapter.detect(plain.text)
    wrong = wrong_key.detect(marked.text)
    assert positive.score > negative.score
    assert positive.score > wrong.score
    assert positive.prediction is True
    assert negative.prediction is False
    assert positive.tokens_scored > 0
    assert positive.status == "ok"
    assert math.isfinite(positive.score)
    assert positive.p_value is None or 0 <= positive.p_value <= 1
    assert "hashing_key" not in adapter.metadata()
    assert "keys" not in adapter.metadata()


@pytest.mark.parametrize("name", SCHEMES)
def test_generation_replays_and_resets_processor(name, model, config, keys):
    adapter = load_scheme(name, model, config, keys.derive(name, 0))
    first = adapter.generate(model, "Write an essay.", seed=73)
    adapter.generate(model, "Unrelated prompt.", seed=8)
    replay = adapter.generate(model, "Write an essay.", seed=73)
    assert first.token_ids == replay.token_ids
    assert first.text == replay.text
    assert first.token_ids == model.encode(first.text)


@pytest.mark.parametrize("name", SCHEMES)
def test_short_text_abstains(name, model, config, keys):
    scheme = load_scheme(name, model, config, keys.derive(name, 0))
    for text in ("", "word1"):
        result = scheme.detect(text)
        assert result.prediction is None and result.score is None
        assert result.status == "insufficient_text"


def test_repeated_contexts_are_masked(model, config, keys):
    scheme = load_scheme("synthid", model, config, keys.derive("synthid", 0))
    result = scheme.detect(" ".join(["word1"] * 30))
    assert result.tokens_scored == 1


def test_unknown_registry_entry(model, config):
    with pytest.raises(ValueError, match="unknown watermark"):
        load_scheme("missing", model, config, {})
