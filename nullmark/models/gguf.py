"""Direct GGUF inference with exact IDs and HF watermarking before sampling."""

import ctypes
import hashlib
import importlib
import importlib.util
import mmap
import os
import shutil
import subprocess
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from transformers import PretrainedConfig

from nullmark.config import ModelConfig
from nullmark.models.causal import Generation
from nullmark.models.ollama import LocalGGUF, LocalModelError

_runtime_handles = []


def llama_module():
    spec = importlib.util.find_spec("llama_cpp")
    if spec is None:
        raise LocalModelError(
            'Direct GGUF requires optional dependencies: pip install -e ".[gguf]"'
        )
    # Official Windows CUDA wheels need cuBLAS at import time. Reuse a matching
    # installed Ollama runtime; never copy DLLs or substitute llama/ggml binaries.
    executable = shutil.which("ollama")
    if os.name == "nt" and executable and spec.origin:
        cuda = Path(spec.origin).parent / "lib" / "ggml-cuda.dll"
        if cuda.is_file() and not _runtime_handles:
            with (
                cuda.open("rb") as handle,
                mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data,
            ):
                for version in ("13", "12"):
                    filename = f"cublas64_{version}.dll"
                    runtime = Path(executable).parent / "lib" / "ollama" / f"cuda_v{version}"
                    if data.find(filename.encode()) >= 0 and (runtime / filename).is_file():
                        try:
                            _runtime_handles.extend(
                                [
                                    os.add_dll_directory(str(runtime)),
                                    ctypes.CDLL(str(runtime / filename)),
                                ]
                            )
                        except OSError:
                            pass
    try:
        return importlib.import_module("llama_cpp")
    except (ImportError, RuntimeError, OSError):
        raise LocalModelError(
            "The GGUF native runtime could not load. Install a compatible llama-cpp-python "
            "CPU/CUDA build and its runtime; see docs/playground.md."
        ) from None


def gpu_layers(offload: str, size: int, supported: bool) -> int:
    if offload == "cpu":
        return 0
    if offload == "gpu":
        if not supported:
            raise LocalModelError("This llama-cpp-python build does not support GPU offload.")
        return -1
    if supported and shutil.which("nvidia-smi"):
        try:
            run = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                capture_output=True,
                encoding="utf-8",
                timeout=5,
                check=True,
            )
            free = int(run.stdout.splitlines()[0].strip()) * 1024**2
            if size + 1536 * 1024**2 < free:
                return -1
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return 0


class GGUFBackend:
    watermark_device = "cpu"

    def __init__(self, config: ModelConfig, local: LocalGGUF):
        self.settings = config
        self.local = local
        self._api = llama_module()
        torch.set_num_threads(config.threads)
        # Verify provenance without copying weights or placing their path in exports.
        with local.path.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != local.blob_sha256:
                raise LocalModelError("The local GGUF content does not match its blob SHA-256.")
        self._layers = gpu_layers(
            config.offload, local.path.stat().st_size, self._api.llama_supports_gpu_offload()
        )
        try:
            self.llm = self._api.Llama(
                model_path=str(local.path),
                n_ctx=config.context_length,
                n_batch=min(256, config.context_length),
                n_gpu_layers=self._layers,
                n_threads=config.threads,
                verbose=False,
            )
        except (ValueError, RuntimeError, OSError):
            raise LocalModelError(
                "GGUF load failed: the architecture may be unsupported or memory insufficient. "
                "Try CPU offload or a smaller installed model."
            ) from None
        try:
            self.vocab_size = self.llm.n_vocab()
            vocab = self.llm._model.vocab
            self.eos_token_ids = frozenset(
                i for i in range(self.vocab_size) if self._api.llama_vocab_is_eog(vocab, i)
            )
            self.special_token_ids = frozenset(
                i for i in range(self.vocab_size) if self._api.llama_vocab_is_control(vocab, i)
            )
            bos = self.llm.token_bos()
            self.detector_config = PretrainedConfig(
                vocab_size=self.vocab_size,
                bos_token_id=bos if bos >= 0 else None,
                eos_token_id=self.llm.token_eos(),
            )
            template = self.llm.metadata.get("tokenizer.chat_template")
            if not template or not self.eos_token_ids:
                raise LocalModelError(
                    "This GGUF needs an embedded chat template and EOG token IDs."
                )
            self._formatter = self._api.llama_chat_format.Jinja2ChatFormatter(
                template,
                eos_token=self.decode([self.llm.token_eos()]),
                bos_token=self.decode([bos]) if bos >= 0 else "",
            )
            self._template_hash = hashlib.sha256(template.encode()).hexdigest()
            self._thinking_disabled = "enable_thinking" in template
        except Exception:
            self.close()
            raise

    def encode(self, text: str) -> list[int]:
        return self.llm.tokenize(text.encode("utf-8"), add_bos=False, special=True)

    def encode_prompt(self, text: str) -> list[int]:
        prompt = self._formatter(
            messages=[{"role": "user", "content": text}],
            enable_thinking=False,
        ).prompt
        return self.encode(prompt)

    def decode(self, ids: list[int]) -> str:
        return self.llm.detokenize(ids, special=True).decode("utf-8", errors="replace")

    def metadata(self) -> dict:
        return {
            "name": self.local.model.name,
            "backend": "llama-cpp-python",
            "backend_version": self._api.__version__,
            "revision": self.local.blob_sha256,
            "blob_sha256": self.local.blob_sha256,
            "ollama_model_digest": self.local.model.digest,
            "quantization": self.local.model.quantization,
            "vocab_size": self.vocab_size,
            "device": "gpu" if self._layers else "cpu",
            "trained": True,
            "context_length": self.settings.context_length,
            "gpu_layers": self._layers,
            "watermark_device": "cpu",
            "chat_template_sha256": self._template_hash,
            "thinking": "enable_thinking=False passed to template"
            if self._thinking_disabled
            else "model template default",
            "sampling": {k: getattr(self.settings, k) for k in ("temperature", "top_k", "top_p")},
            "repeat_penalty": 1.0,
            "min_p": 0.0,
            "threads": self.settings.threads,
            "logits_order": "HF watermark, then native top-k/top-p/temperature sampling",
        }

    def generate(self, prompt: str, *, seed: int, watermark=None, processor=None) -> Generation:
        if not 0 <= seed < 2**32 - 1:
            raise LocalModelError(
                "GGUF sampling seed must be 0–4294967294; llama.cpp reserves 4294967295."
            )
        prompt_ids = self.encode_prompt(prompt)
        if (
            not prompt_ids
            or len(prompt_ids) + self.settings.max_new_tokens > self.settings.context_length
        ):
            raise LocalModelError(
                "Prompt plus continuation exceeds the GGUF context. Shorten the prompt/output."
            )
        if watermark is not None:
            if processor is not None:
                raise ValueError("choose one logits transformation")
            processor = watermark.construct_processor(self.vocab_size, self.watermark_device)
        ids, errors = [], []
        calls = 0

        def transform(input_ids, scores):
            nonlocal calls
            calls += 1
            try:
                if len(scores) != self.vocab_size or list(map(int, input_ids)) != prompt_ids + ids:
                    raise ValueError("native token/logit layout mismatch")
                tensor = torch.from_numpy(np.array(scores, dtype=np.float32, copy=True))[None, :]
                with torch.inference_mode():
                    output = processor(torch.tensor([input_ids.tolist()], dtype=torch.long), tensor)
                values = output[0].numpy()
                if (
                    values.shape != scores.shape
                    or np.isnan(values).any()
                    or not np.isfinite(values).any()
                ):
                    raise ValueError("invalid watermark logits")
                return values
            except Exception as exc:
                # Exceptions crossing ctypes callbacks can be swallowed. Force EOG and
                # raise outside native code; never silently return an unmarked sample.
                errors.append(type(exc).__name__)
                safe = np.full(scores.shape, -np.inf, dtype=np.float32)
                safe[min(self.llm.token_eos(), len(scores) - 1)] = 0
                return safe

        self.llm.reset()
        self.llm.set_seed(seed)
        started = perf_counter()
        stream = self.llm.generate(
            prompt_ids,
            temp=self.settings.temperature,
            top_k=self.settings.top_k,
            top_p=self.settings.top_p,
            min_p=0.0,
            repeat_penalty=1.0,
            reset=True,
            logits_processor=self._api.LogitsProcessorList([transform]) if processor else None,
        )
        try:
            for token in stream:
                if errors:
                    raise LocalModelError(
                        "The native watermark logits callback failed; no sample was returned."
                    )
                ids.append(int(token))
                if token in self.eos_token_ids or len(ids) >= self.settings.max_new_tokens:
                    break
        finally:
            stream.close()
            # Release native callback references and their per-generation HF state.
            self.llm._sampler = None
        if errors or processor is not None and calls != len(ids):
            raise LocalModelError(
                "The backend did not apply watermark processing at every sampled token."
            )
        # Original IDs retain EOG; visible text excludes controls.
        # Detector retokenization remains separate.
        text = self.llm.detokenize(ids, special=False).decode("utf-8", errors="replace")
        return Generation(text, ids, perf_counter() - started, prompt_ids, calls)

    def close(self) -> None:
        self.llm._sampler = None
        self.llm.close()
