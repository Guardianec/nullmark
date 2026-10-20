import sys
from types import SimpleNamespace

from nullmark.evaluation.quality import (
    EMBEDDING_MODEL,
    EMBEDDING_REVISION,
    SemanticSimilarity,
)


def test_semantic_model_is_pinned_local_and_has_no_remote_code(monkeypatch):
    seen = {}

    def model(name, **kwargs):
        seen.update(name=name, **kwargs)
        return SimpleNamespace()

    monkeypatch.setitem(
        sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=model)
    )
    SemanticSimilarity()
    assert seen == {
        "name": EMBEDDING_MODEL,
        "revision": EMBEDDING_REVISION,
        "device": "cpu",
        "local_files_only": True,
        "trust_remote_code": False,
    }


def test_semantic_long_text_is_chunked_and_embeddings_cached(monkeypatch):
    import numpy as np

    calls = []
    tokenizer = SimpleNamespace(
        encode=lambda text, **kw: list(range(600)), decode=lambda ids: str(len(ids))
    )
    model = SimpleNamespace(
        tokenizer=tokenizer,
        max_seq_length=256,
        encode=lambda chunks, **kw: calls.append(chunks) or np.array([[1.0, 0.0]] * len(chunks)),
    )
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=lambda *a, **kw: model),
    )
    metric = SemanticSimilarity()
    assert metric.compare("long text", "long text") == 1.0
    assert calls == [["254", "254", "92"]]
