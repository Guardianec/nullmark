"""Unwatermarked GGUF transformation-only wrapper. Never constructs a detector."""

import hashlib
import json
from pathlib import Path

import numpy as np

from nullmark.common.runtime import gpu_layers, llama_module


class TransformationModel:
    def __init__(self, config):
        path = Path(config["model_path"])
        self.digest = config["model_digest"]
        with path.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != self.digest:
                raise ValueError("attack model digest mismatch")
        api = llama_module()
        self.sampling = {
            "temperature": 0.2,
            "top_k": 40,
            "top_p": 0.95,
            "max_tokens": 768,
            "enable_thinking": False,
            "repeat_penalty": 1.0,
            "min_p": 0.0,
            "backend_version": api.__version__,
            "context_length": 4096,
            "chat_template_sha256": None,
        }
        self.llm = api.Llama(
            model_path=str(path),
            n_ctx=4096,
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
        if len(self.tokenize(prompt)) + self.sampling["max_tokens"] > 4096:
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
            # One linguistic analysis reused across budgets and entropy selection.
            vocabulary = sorted({m.group() for m in pool})
            raw = self.complete(
                "Suggest conservative context-aware single-word substitutions for the text. "
                "Preserve meaning, grammar, tone, factual claims and negations. Only use words "
                "from the candidate list as JSON keys. Skip ambiguous or unsafe words. "
                "Each value must be one lowercase word different from its key. "
                "Return ONLY a JSON object, no markdown.\nCandidates: "
                + json.dumps(vocabulary)
                + "\nText:\n"
                + text,
                seed,
            )
            value = json.loads(raw)
            if not isinstance(value, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()
            ):
                raise ValueError("invalid contextual alternatives")
            self.analysis[identity] = value
        value = self.analysis[identity]
        return {
            m.start(): value[m.group()]
            for m in pool
            if m.group() in value
            and value[m.group()].isalpha()
            and value[m.group()].islower()
            and value[m.group()] != m.group()
        }

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
