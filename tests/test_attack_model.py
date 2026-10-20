from types import SimpleNamespace

import numpy as np
import pytest

from nullmark.attacks.model import TransformationModel
from nullmark.attacks.text import candidates, words


def bare_model():
    model = TransformationModel.__new__(TransformationModel)
    model.analysis = {}
    model.entropy_cache = {}
    return model


def test_contextual_copy_extracts_only_isolated_safe_substitutions_and_reuses_analysis():
    model = bare_model()
    text = "The useful method often helps people protect 26 boats."
    calls = []
    model.complete = lambda instruction, seed: calls.append(seed) or (
        "The helpful method often assists people protect 27 boats."
    )
    pool = candidates(text)
    first = model.replacements(text, pool, 9)
    assert {text[start : start + 6]: replacement for start, replacement in first.items()} == {
        "useful": "helpful",
        "helps ": "assists",
    }
    assert model.replacements(text, pool, 9) == first
    assert calls == [9]


def test_contextual_analysis_failure_is_not_repeated_at_every_budget():
    model = bare_model()
    calls = []
    model.complete = lambda instruction, seed: calls.append(seed) or "Here is the rewritten text: x"
    text = "The useful method often helps people."
    for _ in range(2):
        with pytest.raises(ValueError):
            model.replacements(text, candidates(text), 9)
    assert calls == [9]


def test_entropy_uses_unwatermarked_probabilities_and_caches_analysis():
    model = bare_model()
    text = "The useful method often helps people."
    pool = candidates(text)[:2]
    calls = []
    model.tokenize = words
    model.llm = SimpleNamespace(
        reset=lambda: None,
        eval=lambda ids: calls.append(ids),
        scores=np.array(
            [[0.0, 0.0], [12.0, -12.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
        ),
    )
    entropy = model.entropies(text, pool)
    assert entropy[pool[0].start()] == pytest.approx(np.log(2))
    assert entropy[pool[1].start()] < 0.001
    assert model.entropies(text, pool) == entropy
    assert len(calls) == 1
