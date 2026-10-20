import hashlib
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from nullmark.config import ModelConfig
from nullmark.evaluation.inspection import inspect_sample
from nullmark.models import gguf
from nullmark.models.ollama import InstalledModel, LocalGGUF, LocalModelError
from nullmark.watermark.kgw import KGWScheme
from nullmark.watermark.synthid import SynthIDScheme


class FakeLlama:
    def __init__(self, **kwargs):
        self.load_settings = kwargs
        self.metadata = {"tokenizer.chat_template": "enable_thinking"}
        self._model = SimpleNamespace(vocab="vocab")
        self.closed = False
        self.ignore_callback = False

    def n_vocab(self):
        return 32

    def token_eos(self):
        return 31

    def token_bos(self):
        return 0

    def tokenize(self, text, **kwargs):
        return [int(w[4:]) for w in text.decode().split()]

    def detokenize(self, ids, **kwargs):
        return " ".join(f"word{i}" for i in ids).encode()

    def reset(self):
        pass

    def set_seed(self, seed):
        self.seed = seed

    def close(self):
        self.closed = True

    def generate(self, tokens, **kwargs):
        self.sampling = kwargs
        prefix = list(tokens)
        for i in range(32):
            scores = np.full(32, -10, dtype=np.float32)
            scores[1 + i % 8] = 0
            if kwargs["logits_processor"] and not self.ignore_callback:
                for processor in kwargs["logits_processor"]:
                    scores = processor(np.array(prefix), scores)
            token = int(np.argmax(scores))
            yield token
            prefix.append(token)


@pytest.fixture
def backend(tmp_path, monkeypatch):
    raw = b"GGUF test weights"
    digest = hashlib.sha256(raw).hexdigest()
    path = tmp_path / ("sha256-" + digest)
    path.write_bytes(raw)

    class Formatter:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, **kwargs):
            assert kwargs["enable_thinking"] is False
            return SimpleNamespace(prompt="word20 word21 " + kwargs["messages"][0]["content"])

    api = SimpleNamespace(
        Llama=FakeLlama,
        LogitsProcessorList=list,
        __version__="mock",
        llama_supports_gpu_offload=lambda: False,
        llama_vocab_is_eog=lambda vocab, i: i in (30, 31),
        llama_vocab_is_control=lambda vocab, i: i in (0, 30, 31),
        llama_chat_format=SimpleNamespace(Jinja2ChatFormatter=Formatter),
    )
    monkeypatch.setattr(gguf, "llama_module", lambda: api)
    local = LocalGGUF(
        InstalledModel("test:local", "a" * 64, len(raw), "Q4", "tiny", True, "local"), digest, path
    )
    config = ModelConfig(
        backend="ollama-gguf",
        name="test:local",
        revision=digest,
        max_new_tokens=16,
        temperature=0.8,
        top_k=7,
        top_p=0.9,
        offload="cpu",
    )
    model = gguf.GGUFBackend(config, local)
    yield model
    model.close()
    assert model.llm.closed


def test_exact_ids_sampling_metadata_and_cleanup(backend):
    def force(ids, scores):
        output = torch.full_like(scores, float("-inf"))
        output[:, 9] = 0
        return output

    sample = backend.generate("word22", seed=42, processor=force)
    assert sample.token_ids == [9] * 16 and sample.processor_calls == 16
    assert sample.prompt_token_ids == [20, 21, 22]
    assert backend.llm.seed == 42
    assert backend.llm.sampling["top_k"] == 7 and backend.llm.sampling["top_p"] == 0.9
    assert backend.llm.sampling["temp"] == 0.8 and backend.llm.sampling["min_p"] == 0
    assert backend.metadata()["blob_sha256"] == backend.local.blob_sha256
    assert "path" not in backend.metadata()


@pytest.mark.parametrize("scheme_name", ["kgw", "synthid"])
def test_existing_processors_cross_backend(backend, config, keys, scheme_name):
    scheme = (
        KGWScheme(backend, config.kgw, keys.derive("kgw", 0))
        if scheme_name == "kgw"
        else SynthIDScheme(backend, config.synthid, keys.derive("synthid", 0))
    )
    generated = scheme.generate(backend, "word22", seed=42)
    assert generated.processor_calls == len(generated.token_ids)
    result = inspect_sample(backend, scheme, "word22", generated)
    assert sum(t.scored for t in result.detector_tokens) == result.detection.tokens_scored
    # Cross-check the bridge's sampled IDs with the same HF processor directly.
    processor = scheme.generation_config().construct_processor(backend.vocab_size, "cpu")
    prefix = generated.prompt_token_ids[:]
    for i, token in enumerate(generated.token_ids):
        logits = torch.full((1, 32), -10.0)
        logits[0, 1 + i % 8] = 0
        expected = int(processor(torch.tensor([prefix]), logits).argmax())
        assert token == expected
        prefix.append(token)


def test_callback_errors_fail_closed(backend):
    def broken(ids, scores):
        raise RuntimeError("PRIVATE KEY")

    with pytest.raises(LocalModelError, match="callback failed") as error:
        backend.generate("word22", seed=42, processor=broken)
    assert "PRIVATE" not in str(error.value)


def test_ignored_callback_is_rejected(backend):
    backend.llm.ignore_callback = True
    with pytest.raises(LocalModelError, match="every sampled token"):
        backend.generate("word22", seed=42, processor=lambda ids, scores: scores)


def test_gguf_context_and_special_ids(backend):
    assert backend.eos_token_ids == {30, 31}
    backend.settings = backend.settings.model_copy(update={"context_length": 16})
    with pytest.raises(LocalModelError, match="exceeds"):
        backend.generate("word22", seed=42)


def test_alternate_eog_and_reserved_seed(backend):
    def end(ids, scores):
        output = torch.full_like(scores, float("-inf"))
        output[:, 30] = 0
        return output

    sample = backend.generate("word22", seed=1, processor=end)
    assert sample.token_ids == [30] and sample.processor_calls == 1
    with pytest.raises(LocalModelError, match="reserves"):
        backend.generate("word22", seed=2**32 - 1)


def test_gpu_build_capability_check():
    assert gguf.gpu_layers("cpu", 100, True) == 0
    with pytest.raises(LocalModelError, match="does not support"):
        gguf.gpu_layers("gpu", 100, False)


def test_missing_optional_runtime(monkeypatch):
    monkeypatch.setattr(gguf.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(LocalModelError, match=r"\[gguf\]"):
        gguf.llama_module()
