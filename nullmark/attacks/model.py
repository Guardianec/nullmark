"""Unwatermarked GGUF transformation-only wrapper. Never constructs a detector."""

import hashlib
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

from nullmark.attacks.baselines import validate_output
from nullmark.attacks.text import WORD
from nullmark.common.runtime import gpu_layers, llama_module


class TransformationModel:
    def __init__(self, config):
        path = Path(config["model_path"])
        self.digest = config["model_digest"]
        with path.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != self.digest:
                raise ValueError("attack model digest mismatch")
        api = llama_module()
        context_length = 8192 if config.get("skd_mode") else 4096
        self.sampling = {
            "temperature": 0.2,
            "top_k": 40,
            "top_p": 0.95,
            "max_tokens": 1536 if config.get("skd_mode") else 768,
            "enable_thinking": False,
            "repeat_penalty": 1.0,
            "min_p": 0.0,
            "backend_version": api.__version__,
            "context_length": context_length,
            "chat_template_sha256": None,
        }
        self.llm = api.Llama(
            model_path=str(path),
            n_ctx=context_length,
            n_batch=256,
            n_threads=8,
            n_gpu_layers=gpu_layers(
                config.get("offload", "auto"), path.stat().st_size, api.llama_supports_gpu_offload()
            ),
            logits_all=True,
            verbose=False,
        )
        template = self.llm.metadata["tokenizer.chat_template"]
        self.sampling["chat_template_sha256"] = hashlib.sha256(template.encode()).hexdigest()
        self.formatter = api.llama_chat_format.Jinja2ChatFormatter(
            template,
            eos_token=self.llm.detokenize([self.llm.token_eos()]).decode(),
            bos_token="",
        )
        self.analysis = {}
        self.entropy_cache = {}

    def tokenize(self, text):
        return self.llm.tokenize(text.encode(), add_bos=False, special=False)

    def complete(self, instruction, seed):
        prompt = self.formatter(
            messages=[{"role": "user", "content": instruction}], enable_thinking=False
        ).prompt
        if (
            len(self.tokenize(prompt)) + self.sampling["max_tokens"]
            > self.sampling["context_length"]
        ):
            raise ValueError("attack prompt exceeds context")
        response = self.llm.create_completion(
            prompt=prompt,
            seed=seed,
            temperature=0.2,
            top_k=40,
            top_p=0.95,
            max_tokens=self.sampling["max_tokens"],
            repeat_penalty=1.0,
            min_p=0.0,
        )
        if response["choices"][0]["finish_reason"] == "length":
            raise ValueError("truncated model output")
        return response["choices"][0]["text"]

    def paraphrase(self, text, seed):
        return self.complete(
            "Rewrite the following text naturally while preserving all factual meaning, "
            "claims, numbers, names, negations and tone. Do not summarize or add information. "
            "Return only the rewritten text, with no preamble or explanation.\n\n" + text,
            seed,
        )

    def replacements(self, text, pool, seed):
        identity = (text, seed)
        if identity not in self.analysis:
            self.analysis[identity] = None  # Cache failed analysis too; never retry per budget.
            raw = self.complete(
                "Copy the following text with local lexical edits. Aim to replace about one "
                "word in five with natural single-word contextual alternatives, spread across "
                "the text. Keep each change separated by unchanged words. Make more than one "
                "edit when safe alternatives exist. Preserve each word's grammatical role "
                "and inflection, all meaning, "
                "tone, numbers, names and negations. Do not reorder, insert or delete words. "
                "Do not alter pronouns, conjunctions or prepositions. If an alternative is "
                "ambiguous, keep the original. Return only the complete edited text, with "
                "no explanation, heading or markdown wrapper.\n\n" + text,
                seed,
            )
            validate_output(text, raw)
            original, edited = list(WORD.finditer(text)), list(WORD.finditer(raw))
            safe = {m.start() for m in pool}
            value = {}
            for tag, i, j, k, end in SequenceMatcher(
                None,
                [m.group() for m in original],
                [m.group() for m in edited],
                autojunk=False,
            ).get_opcodes():
                # Isolated substitutions only; phrase restructuring cannot leak into local edits.
                if tag == "replace" and j - i == end - k == 1:
                    before, after = original[i], edited[k].group()
                    if before.start() in safe and after.isalpha() and after.islower():
                        value[before.start()] = after
            self.analysis[identity] = value
        if self.analysis[identity] is None:
            raise ValueError("contextual analysis previously failed")
        return self.analysis[identity]

    def entropies(self, text, pool):
        if text not in self.entropy_cache:
            ids = self.tokenize(text)
            if len(ids) >= 4096:
                raise ValueError("entropy text exceeds context")
            self.llm.reset()
            self.llm.eval(ids)
            scores = self.llm.scores[: len(ids)]
            result = {}
            for m in pool:
                index = len(self.tokenize(text[: m.start()].rstrip())) - 1
                if index < 0:
                    result[m.start()] = 0.0
                    continue
                logits = np.array(scores[index], dtype=np.float64)
                logits -= logits.max()
                probabilities = np.exp(logits)
                probabilities /= probabilities.sum()
                result[m.start()] = float(
                    -np.sum(probabilities * np.log(np.maximum(probabilities, np.finfo(float).tiny)))
                )
            self.entropy_cache[text] = result
        return self.entropy_cache[text]

    def close(self):
        self.llm.close()

    def skd_entropies(self, text, pool):
        """Mean ordinary next-token entropy across source span token positions."""
        ids = self.tokenize(text)
        if len(ids) >= self.sampling["context_length"]:
            raise ValueError("SKD entropy text exceeds context")
        self.llm.reset()
        self.llm.eval(ids)
        # Prefix byte lengths preserve multibyte character alignment at span boundaries.
        ends = [len(self.llm.detokenize(ids[:i])) for i in range(1, len(ids) + 1)]
        starts = [0, *ends[:-1]]
        needed = set()
        indices = {}
        for c in pool:
            left, right = len(text[: c["start"]].encode()), len(text[: c["end"]].encode())
            indices[(c["start"], c["end"])] = [
                i - 1
                for i, (a, b) in enumerate(zip(starts, ends, strict=True))
                if a < right and b > left and i > 0
            ]
            needed.update(indices[(c["start"], c["end"])])
        entropies = {}
        for i in needed:
            logits = np.array(self.llm.scores[i], dtype=np.float64)
            logits -= logits.max()
            p = np.exp(logits)
            p /= p.sum()
            entropies[i] = float(-np.sum(p * np.log(np.maximum(p, np.finfo(float).tiny))))
        return {
            start: float(np.mean([entropies[i] for i in positions])) if positions else 0.0
            for start, positions in indices.items()
        }
