import hashlib
import json
from dataclasses import asdict

import pytest

from nullmark.evaluation.inspection import inspect_sample, inspect_tokens, paired_generation
from nullmark.evaluation.secrets import KeyStore, key_reference
from nullmark.models import Generation
from nullmark.watermark.registry import load_scheme


def test_master_bound_references(keys, monkeypatch):
    other = KeyStore(bytes(reversed(range(32))))
    # Even a collision in the tiny derived keyspace must not produce the same reference.
    monkeypatch.setattr(KeyStore, "_number", lambda self, label: 7)
    assert keys.derive("kgw", 0) == other.derive("kgw", 0)
    ref = key_reference(keys, "kgw", 0)
    assert ref == key_reference(KeyStore(keys.master), "kgw", 0)
    assert (
        len(
            {
                ref,
                key_reference(other, "kgw", 0),
                key_reference(keys, "kgw", 1),
                key_reference(keys, "synthid", 0),
            }
        )
        == 4
    )

    def old(n):
        return hashlib.sha256(json.dumps({"hashing_key": n}, sort_keys=True).encode()).hexdigest()

    # Direct fingerprints reveal a small secret by exhaustive offline comparison.
    assert next(n for n in range(1, 33) if old(n) == old(7)) == 7
    assert ref not in {old(n) for n in range(1, 33)}
    assert keys.master.hex() not in ref


@pytest.mark.parametrize("name", ["kgw", "synthid"])
def test_inspection_matches_detector_and_replays(name, model, config, keys):
    scheme = load_scheme(name, model, config, keys.derive(name, 0))
    sample = scheme.generate(model, "word1 word2 word3 word4 word5", seed=42)
    result = inspect_sample(model, scheme, "word1 word2 word3 word4 word5", sample)
    assert len(result.tokens) == len(sample.token_ids)
    assert result.token_count == len(sample.token_ids)
    assert sum(t.scored for t in result.detector_tokens) == result.detection.tokens_scored
    last = result.detector_tokens[-1]
    score = last.kgw.cumulative_z if name == "kgw" else last.synthid.cumulative_mean_g
    assert score == pytest.approx(result.detection.score, abs=1e-7)
    assert result.tokens == inspect_tokens(
        model, scheme, sample.token_ids, prompt_ids=model.encode("word1 word2 word3 word4 word5")
    )
    serialized = json.dumps(asdict(result))
    for forbidden in ("hashing_key", "sampling_table_seed", '"keys"', keys.master.hex()):
        assert forbidden not in serialized
    if name == "kgw":
        assert result.tokens[0].context == [model.encode("word5")[0]]
        assert result.tokens[0].kgw is not None
        assert result.detector_tokens[0].scored is False
    else:
        assert all(t.synthid is None for t in result.tokens[: config.synthid.ngram_len - 1])
        assert len(last.synthid.g_values) == config.synthid.depth
        assert set(last.synthid.g_values) <= {0, 1}


@pytest.mark.parametrize("name", ["kgw", "synthid"])
@pytest.mark.parametrize("text", ["", "word1", "word1 " * 30])
def test_inspection_short_and_repeated(name, text, model, config, keys):
    scheme = load_scheme(name, model, config, keys.derive(name, 0))
    sample = Generation(text, model.encode(text), 0)
    result = inspect_sample(model, scheme, "word2", sample)
    assert sum(t.scored for t in result.detector_tokens) == result.detection.tokens_scored
    if len(model.encode(text)) <= 1:
        assert result.detection.status == "insufficient_text"


@pytest.mark.parametrize("name", ["kgw", "synthid", "none"])
def test_pair_uses_same_seed(name, model, config, keys):
    scheme = None if name == "none" else load_scheme(name, model, config, keys.derive(name, 0))
    result = paired_generation(model, scheme, "word1 word2", seed=19)
    assert result.seed == 19
    if scheme:
        assert result.plain.text == model.generate("word1 word2", seed=19).text
        assert result.marked.text == scheme.generate(model, "word1 word2", seed=19).text
        assert result.first_divergence is not None
    else:
        assert result.plain is None and result.marked.detection is None
    assert keys.master.hex() not in json.dumps(asdict(result))


def test_text_retokenization_is_explicit(model, config, keys):
    scheme = load_scheme("kgw", model, config, keys.derive("kgw", 0))
    result = inspect_sample(model, scheme, "word1", Generation("word2 word3", [3, 4, 5], 0))
    assert not result.roundtrip_exact
    assert len(result.tokens) == 3 and len(result.detector_tokens) == 2


@pytest.mark.parametrize("width", [1, 3])
@pytest.mark.parametrize("ignore_repeated", [True, False])
def test_kgw_prefix_trace_matches_reference(width, ignore_repeated, model, config, keys):
    config = config.model_copy(
        update={
            "kgw": config.kgw.model_copy(
                update={
                    "context_width": width,
                    "ignore_repeated_ngrams": ignore_repeated,
                }
            )
        }
    )
    scheme = load_scheme("kgw", model, config, keys.derive("kgw", 0))
    ids = model.encode("word1 word2 word3 word1 word2 word3 word4 word1 word2")
    tokens = inspect_tokens(model, scheme, ids)
    for i in range(width, len(ids)):
        text = model.tokenizer.decode(ids[: i + 1], clean_up_tokenization_spaces=False)
        assert tokens[i].kgw.cumulative_z == pytest.approx(scheme.detect(text).score)


@pytest.mark.parametrize("ngram,depth", [(2, 3), (5, 10)])
def test_synthid_prefix_trace_matches_reference(ngram, depth, model, config, keys):
    config = config.model_copy(
        update={
            "synthid": config.synthid.model_copy(
                update={
                    "ngram_len": ngram,
                    "depth": depth,
                }
            )
        }
    )
    scheme = load_scheme("synthid", model, config, keys.derive("synthid", 0, depth))
    ids = model.encode("word1 word2 word3 word4 word5 word1 word2 word3 word4 word5 word6")
    tokens = inspect_tokens(model, scheme, ids)
    for i in range(ngram - 1, len(ids)):
        text = model.tokenizer.decode(ids[: i + 1], clean_up_tokenization_spaces=False)
        assert tokens[i].synthid.cumulative_mean_g == pytest.approx(scheme.detect(text).score)


def test_special_tokens_neutral_but_detector_accounting_preserved(model, config, keys):
    for name in ("kgw", "synthid"):
        scheme = load_scheme(name, model, config, keys.derive(name, 0))
        ids = model.encode("word1 word2 word3 word4 [UNK] word5 word6")
        tokens = inspect_tokens(model, scheme, ids)
        assert tokens[4].special
        assert (
            sum(t.scored for t in tokens)
            == scheme.detect("word1 word2 word3 word4 [UNK] word5 word6").tokens_scored
        )
