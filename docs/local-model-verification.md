# Local GGUF verification for v0.1.1

The [completed Experiment 002 report](detector-calibration-results.md) contains
the final 128/100-prompt study, all seven frozen operating points and public
aggregate evidence. Recommended exploratory Qwen configuration: SynthID depth 20,
weighted mean, score > **0.5236017624956073**. Held-out TPR **97/98**, observed
FPR **3/99**, target FPR **1%**, overall abstention **3/200**. The observed rate
exceeds the target; this is not a validated 1% population-FPR claim. The run took
114.60 minutes, excluding model loading, without downloading another checkpoint.

The five-prompt observations below are retained as historical diagnostics of
embedding signal and the old demo thresholds. Experiment 002 adds independent
clean calibration and held-out evaluation, with upstream weighted mean, depth
10/20/30, length abstention, and native/visible scoring diagnostics. See
[the detector protocol](detector-calibration.md) for the decision rule and finite
sample limitations. An elevated marked score alone is not a calibrated decision.

Verified on Windows x86-64, Python 3.12.8, Ollama **0.40.6** and
llama-cpp-python **0.3.36**, on 2026-10-20. The machine has an NVIDIA RTX 4070
SUPER (12 GB VRAM) and approximately 32 GB RAM. PyTorch 2.6.0+cpu and the
existing Transformers 4.57.6 processors perform the watermark transformation.

## Installed model and inference

The selected model was **`qwen3.5:9b-q4_K_M`**, quantization **Q4_K_M**,
vocabulary **248,320**. Ollama also listed `qwen3.5:4b-q8_0` and
`qwen3.6:35b-a3b-q4_K_M`; these other models were not loaded or validated.

- Ollama model digest: `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`.
- Language GGUF SHA-256: `02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d`.
- Embedded chat-template SHA-256: `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715`.

Discovery used the fixed localhost API and `ollama show --modelfile`. The local
manifest distinguished the language weights from the vision projector. The
existing language GGUF was opened directly and its full content hash verified.
**No model weights were downloaded or copied.** The optional native runtime wheel
was installed; that is software, not a second model checkpoint.

Before integration, a standalone capability check loaded the existing GGUF,
round-tripped tokenization, reproduced seeded plain generation, forced a known
token through the custom logits hook, and restored ordinary generation when the
hook was removed. The diagnostic CLI subsequently passed these checks plus
three paired seeds for KGW and SynthID. Callback prefix IDs, vocabulary shape,
and callback counts were checked against the actual sampled native token IDs.

Inference runs directly through llama.cpp; Ollama's chat/generate endpoints are
not used. The same HF KGW/SynthID processors used by the Transformers backend
transform native logits before native sampling. Processor state is fresh for
each generation. Native sampler references are released afterward. Full GPU
offload and a separate CPU generation both passed. An experiment run and replay
reproduced public sample text and detector results exactly; formatted prompt IDs
were retained privately, with no model path or secret in the public artifacts.

The embedded Jinja chat template receives a user message and assistant prefix,
with **`enable_thinking=False`**. This model supports that parameter. No generated
reasoning text is deleted afterward. Other templates may retain their own default
behavior if they do not expose this parameter.

Interactive settings were temperature **0.8**, top-k **40**, top-p **0.95**,
context **2048**, threads **8**, repeat penalty **1.0**, min-p **0.0**. Sampling
seed and resolved settings are recorded. Experiment 001 explicitly retains
temperature **1.0**, top-k **0**, top-p **1.0**. Its saved GPT-2 continuations and
original token IDs replayed exactly for plain, KGW and SynthID.

## Five paired prompts

One local private master key, seeds 11/22/33/44/55, a 192-token maximum and the
interactive settings above were used. Each prompt generated plain, KGW and
SynthID continuations with the same public seed. Prompts covered photosynthesis,
the blue sky, database indexes, public libraries and a forgotten-letter story.
Detector scores below use retokenized visible continuations, as in the existing
harness. The wrong-key column scores the KGW continuation with a different key.
Actual native continuation lengths ranged from 78 to 170 tokens, including EOG;
all detector comparisons had sufficient text rather than abstaining.

| Seed | Plain KGW z | Marked KGW z | Wrong-key KGW z | Plain SynthID mean-g | Marked SynthID mean-g |
| --- | ---: | ---: | ---: | ---: | ---: |
| 11 | 0.1348 | 2.3163 | 0.0000 | 0.4839 | 0.5559 |
| 22 | 0.0969 | 2.6336 | 0.1549 | 0.4892 | 0.5483 |
| 33 | 0.0000 | 2.7393 | -0.1191 | 0.5027 | 0.5742 |
| 44 | 0.3558 | 6.1389 | 0.3961 | 0.4810 | 0.5505 |
| 55 | 0.0483 | 7.9078 | -1.3850 | 0.5100 | 0.5845 |

All five correct-key KGW scores exceeded their plain and wrong-key controls.
All five SynthID scores exceeded their paired plain controls. These are smoke
observations, not calibrated error rates or research conclusions. **2/5** marked
KGW samples crossed z=3; **0/5** marked SynthID samples crossed the existing
uncalibrated mean-g=0.6 threshold. Thresholds were not changed to obtain positives.
No positive detector claim is made for the remaining samples.

## Human-visible quality comparison

The same five prompts/seeds were also tested with pinned GPT-2: historical plain
sampling, interactive plain sampling, and interactive KGW/SynthID. The interactive
settings sometimes produced more regular sentences, but GPT-2 remained prone to
irrelevant continuation, invented facts and repetition. Qwen's plain and marked
responses were broadly coherent across these prompts, with occasional wording
or factual imperfections. No automated semantic-quality metric was introduced.

For “Explain photosynthesis in one clear paragraph for a high-school student”,
seed 11, representative exact excerpts are:

**GPT-2, interactive plain:**

> The article discusses the chemistry of carbon, nitrogen and oxygen in living cells, and discusses how they work, and how it can be used for different activities.

**Qwen, interactive plain:**

> Photosynthesis is the fundamental biological process by which plants, algae, and certain bacteria convert light energy into chemical energy to fuel their growth.

These excerpts illustrate instruction-following differences, not a factual
accuracy guarantee. The full local verification outputs remain in ignored local
artifacts; private keys are not published.

## Experiment 002 qualitative inspection

The first calibration prompt encountered in each of the eight styles was inspected
across plain, KGW, and SynthID depths 10/20/30: **40 continuations**. Selection was
by deterministic prompt order, before threshold fitting, rather than score. Prompt
IDs were `argument-24`, `essay-13`, `factual-12`, `instructions-27`, `knowledge-21`,
`narrative-25`, `science-22`, and `technical-13`, with the `cal-v1-` prefix.

All depths produced readable, topical prose in this small qualitative inspection.
The short boat-builder narrative completed in each condition. The longer essay,
argument and technical answers frequently ended mid-sentence at the predeclared
192-token cap, including the plain control. Some science/general-knowledge answers
contained questionable explanations or broad assertions, and phrasing varied among
conditions. These observations do not establish factual accuracy or quality
non-inferiority, and are not a blinded human preference study. No automated
semantic-quality model or quality score was introduced. Detectability alone must
not determine the future configuration recommendation.

## Browser and practical limits

The browser exercised Qwen plain, paired KGW and paired SynthID, token selection,
exact generation contexts and detector traces. Refresh listed the three installed
models with size/quantization, requiring explicit selection rather than loading
the largest automatically. One-active-model eviction and missing native-runtime
errors have automated coverage. See [the playground guide](playground.md) for
installation and offload behavior.

The native callback path is version-sensitive and is pinned to the tested
llama-cpp-python release. Other architectures, OSes, accelerators and models need
their own diagnostic run. Auto offload uses a conservative NVIDIA free-memory
check and otherwise selects CPU; explicit GPU may still exhaust memory. Native
and Transformers sampler ordering differs, so equal settings do not imply equal
token streams across backends. Identical seeds are only expected to replay in a
compatible local runtime/hardware configuration. No cloud generation, attacks,
semantic metrics or v0.2 implementation was added.
