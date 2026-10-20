"""Native runtime loading shared by generation and isolated transformations."""

import ctypes
import importlib
import importlib.util
import mmap
import os
import shutil
import subprocess
from pathlib import Path

from nullmark.common.errors import LocalModelError

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
