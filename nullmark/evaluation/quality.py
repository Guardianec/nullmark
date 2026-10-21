"""Continuous text-preservation metrics, independent of watermark scores."""

from difflib import SequenceMatcher

from nullmark.attacks.text import anchors, distance, words
from nullmark.common.semantic import (
    EMBEDDING_MODEL as EMBEDDING_MODEL,
)
from nullmark.common.semantic import (
    EMBEDDING_REVISION as EMBEDDING_REVISION,
)
from nullmark.common.semantic import (
    SemanticSimilarity as SemanticSimilarity,
)


def text_diff(original, transformed):
    import re

    a, b = (re.findall(r"\s+|\w+|[^\w\s]", text) for text in (original, transformed))
    return [
        {"operation": tag, "before": "".join(a[i:j]), "after": "".join(b[k:end])}
        for tag, i, j, k, end in SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    ]


def quality_metrics(original, transformed, *, tokenize, semantic=None):
    a, b = words(original), words(transformed)
    ta, tb = tokenize(original), tokenize(transformed)
    word_edits, token_edits = distance(a, b), distance(ta, tb)
    wa, wb = set(w.lower() for w in a), set(w.lower() for w in b)
    aa, ab = anchors(original), anchors(transformed)
    retained, total = sum((aa & ab).values()), sum(aa.values())
    return {
        "word_edits": word_edits,
        "word_edit_fraction": word_edits / max(1, len(a)),
        "token_edits": token_edits,
        "token_edit_fraction": token_edits / max(1, len(ta)),
        "length_ratio": len(b) / max(1, len(a)),
        "lexical_similarity": len(wa & wb) / max(1, len(wa | wb)),
        "semantic_similarity": semantic.compare(original, transformed) if semantic else None,
        "semantic_model": EMBEDDING_MODEL if semantic else None,
        "semantic_revision": EMBEDDING_REVISION if semantic else None,
        "anchors_retained": retained,
        "anchors_total": total,
        "anchor_preservation": retained / total if total else None,
        "anchors_added": sum((ab - aa).values()),
        "token_metric": "visible text retokenized with generation model",
    }
