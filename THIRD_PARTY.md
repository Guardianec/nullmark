# Third-party implementations

NullMark is Apache-2.0 licensed. It imports the following watermark implementations;
it does not vendor their processor or detector source files.

| Component | Source | License / use |
| --- | --- | --- |
| Transformers 4.57.6 | https://github.com/huggingface/transformers/tree/v4.57.6 | Apache-2.0; SynthID and KGW generation, g-value extraction, masks, KGW detector |
| SynthID-Text reference | https://github.com/google-deepmind/synthid-text | Apache-2.0; mean-scoring mathematical definition and design reference |
| Original KGW implementation | https://github.com/jwkirchenbauer/lm-watermarking | Apache-2.0; provenance of the Transformers implementation |
| GPT-2 model/tokenizer | https://huggingface.co/openai-community/gpt2 | MIT; downloaded separately, not redistributed in this repository |
| PyTorch | https://github.com/pytorch/pytorch | BSD-3-Clause; tensor operations, model inference, RNG |
| Tokenizers | https://github.com/huggingface/tokenizers | Apache-2.0; imported through Transformers' dependency for offline tokenizer |
| Pydantic | https://github.com/pydantic/pydantic | MIT; config validation |
| PyYAML | https://github.com/yaml/pyyaml | MIT; YAML parsing |
| FastAPI | https://github.com/fastapi/fastapi | MIT; optional local GUI server |
| Starlette | https://github.com/encode/starlette | BSD-3-Clause; optional ASGI routing/middleware |
| llama-cpp-python / llama.cpp | https://github.com/abetlen/llama-cpp-python | MIT; optional direct GGUF inference, native sampler and chat formatting |
| Ollama | https://github.com/ollama/ollama | MIT; separately installed local model discovery; no inference API generation |
| Uvicorn | https://github.com/encode/uvicorn | BSD-3-Clause; optional local ASGI serving |

Copyright in Transformers' watermarking modules belongs to their upstream
contributors, including Hugging Face and Google DeepMind; the original KGW authors
retain their copyright. NullMark's mean statistic is an independent short
expression of the published mathematical definition, not a copied detector module.
No external dataset is bundled. The original built-in prompts and tiny random model
construction are project material. Dependency and model licenses continue to apply
independently; installing NullMark does not relicense those components.
