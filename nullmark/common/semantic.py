"""Pinned public semantic resources, shared by isolated linguistic analysis and quality."""

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"


class SemanticSimilarity:
    def __init__(self, *, local_files_only=True, cache_folder=None):
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
            **({"cache_folder": cache_folder} if cache_folder else {}),
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
