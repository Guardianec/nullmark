"""One causal-model adapter, with a genuinely offline random-weight smoke model."""

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

import torch
from tokenizers import Tokenizer, decoders, models, pre_tokenizers
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    GPT2Config,
    GPT2LMHeadModel,
    PreTrainedTokenizerFast,
)

from nullmark.config import ModelConfig


@dataclass(frozen=True)
class Generation:
    text: str
    token_ids: list[int]
    seconds: float
    prompt_token_ids: list[int] | None = None
    processor_calls: int = 0
    watermark_seconds: float | None = None


class TextGenerator(Protocol):
    def generate(self, prompt: str, *, seed: int, watermark: Any = None) -> Generation: ...


class CausalModel:
    def __init__(self, config: ModelConfig):
        self.settings = config
        torch.set_num_threads(config.threads)
        torch.use_deterministic_algorithms(True)
        if config.device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA requested but unavailable")
        if config.name == "builtin-tiny":
            vocab = {"[UNK]": 0, **{f"word{i}": i + 1 for i in range(511)}}
            tokenizer = Tokenizer(models.WordLevel(vocab, unk_token="[UNK]"))
            tokenizer.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
            tokenizer.decoder = decoders.WordPiece(prefix="##", cleanup=False)
            self.tokenizer = PreTrainedTokenizerFast(tokenizer_object=tokenizer, unk_token="[UNK]")
            model_config = GPT2Config(
                vocab_size=512,
                n_positions=8192,
                n_embd=32,
                n_layer=2,
                n_head=2,
                bos_token_id=None,
                eos_token_id=None,
                pad_token_id=0,
            )
            # Model initialization is independent of the generation and secret seeds.
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(1729)
                self.model = GPT2LMHeadModel(model_config)
            self.revision = "builtin-tiny-v1-init1729"
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(
                config.name,
                revision=config.revision,
                trust_remote_code=False,
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                config.name,
                revision=config.revision,
                trust_remote_code=False,
                use_safetensors=True,
                attn_implementation="eager",
            )
            self.revision = config.revision
        self.model.to(config.device).eval()

    def encode(self, text: str) -> list[int]:
        return self.tokenizer.encode(text, add_special_tokens=False)

    def encode_prompt(self, text: str) -> list[int]:
        return self.encode(text)

    def decode(self, ids: list[int]) -> str:
        return self.tokenizer.decode(ids, clean_up_tokenization_spaces=False)

    @property
    def vocab_size(self) -> int:
        return self.model.config.vocab_size

    @property
    def detector_config(self):
        return self.model.config

    @property
    def watermark_device(self) -> str:
        return self.settings.device

    @property
    def eos_token_ids(self) -> frozenset[int]:
        eos = self.tokenizer.eos_token_id
        return frozenset([eos]) if eos is not None else frozenset()

    @property
    def special_token_ids(self) -> frozenset[int]:
        return frozenset(self.tokenizer.all_special_ids)

    def close(self) -> None:
        self.model = None
        if self.settings.device == "cuda":
            torch.cuda.empty_cache()

    def metadata(self) -> dict:
        return {
            "name": self.settings.name,
            "revision": self.revision,
            "tokenizer": self.tokenizer.name_or_path or "builtin-wordlevel-v1",
            "vocab_size": self.model.config.vocab_size,
            "device": self.settings.device,
            "trained": self.settings.name != "builtin-tiny",
            "backend": "transformers",
            "sampling": {k: getattr(self.settings, k) for k in ("temperature", "top_k", "top_p")},
        }

    @torch.inference_mode()
    def generate(self, prompt: str, *, seed: int, watermark: Any = None) -> Generation:
        inputs = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
        inputs = {k: v.to(self.settings.device) for k, v in inputs.items()}
        length = inputs["input_ids"].shape[-1]
        if (
            length == 0
            or length + self.settings.max_new_tokens > self.model.config.max_position_embeddings
        ):
            raise ValueError("empty prompt or prompt + continuation exceeds model context")
        devices = [torch.cuda.current_device()] if self.settings.device == "cuda" else []
        start = perf_counter()
        with torch.random.fork_rng(devices=devices):
            torch.manual_seed(seed)
            output = self.model.generate(
                **inputs,
                do_sample=True,
                top_k=self.settings.top_k,
                top_p=self.settings.top_p,
                temperature=self.settings.temperature,
                max_new_tokens=self.settings.max_new_tokens,
                pad_token_id=self.model.config.pad_token_id or self.tokenizer.eos_token_id or 0,
                watermarking_config=watermark,
            )
        ids = output[0, length:].tolist()
        text = self.tokenizer.decode(
            ids, skip_special_tokens=False, clean_up_tokenization_spaces=False
        )
        return Generation(text, ids, perf_counter() - start, inputs["input_ids"][0].tolist())
