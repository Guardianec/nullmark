"""Continuous text-preservation metrics, independent of watermark scores."""

from difflib import SequenceMatcher

from nullmark.attacks.text import anchors, distance, words

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"


class SemanticSimilarity:
    def __init__(self, *, local_files_only=True):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ValueError(
                "Install the optional evaluation extra: nullmark[evaluation]"
            ) from None
        self.model = SentenceTransformer(
            EMBEDDING_MODEL,
            revision=EMBEDDING_REVISION,
            device="cpu",
            local_files_only=local_files_only,
            trust_remote_code=False,
        )
        self.cache = {}

    def embedding(self, text):
        import numpy as np

        if text not in self.cache:
            ids = self.model.tokenizer.encode(text, add_special_tokens=False)
            size = self.model.max_seq_length - 2
            blocks = [ids[i : i + size] for i in range(0, len(ids), size)] or [[]]
            chunks = [self.model.tokenizer.decode(block) for block in blocks]
            vectors = self.model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
            vector = np.average(vectors, axis=0, weights=[max(1, len(b)) for b in blocks])
            self.cache[text] = vector / max(np.linalg.norm(vector), 1e-12)
        return self.cache[text]

    def compare(self, original, transformed):
        import numpy as np

        return float(np.clip(self.embedding(original) @ self.embedding(transformed), -1, 1))


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
