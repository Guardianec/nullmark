# Baseline attacks — v0.2

Experiment 003 asks how four simple text transformations affect locally controlled
KGW and SynthID watermarks, and how much text preservation they sacrifice.
It is a baseline study, not a universal watermark removal claim or minimum-budget search.

## Threat model and process boundary

All four attacks are **keyless and detector-blind**. `AttackInput` contains exactly
`sample_id`, `prompt`, and `text`. It never contains keys/references, watermark
settings, native generation IDs, detector scores, thresholds, calibration artifacts,
membership information or g-values. `AttackOutput` contains transformed text and
public transformation provenance only. The trusted evaluator adds detector results
after transformation and quality measurement.

`evaluation.attack_worker.AttackWorker` starts `attacks.worker` as a subprocess with
isolated Python mode (`-I`), a fresh temporary working directory and an allowlisted
environment. Public JSON requests travel over stdin; stdout carries public outputs
or sanitized failure types. Worker arguments contain no evaluator-private path.
The optional model specification supplies only the installed GGUF weight path,
its SHA-256 and public inference settings. The worker verifies the weight digest.
It constructs a restricted, unwatermarked llama.cpp transformation wrapper;
it does not construct the NullMark generation backend, watermark or detector.

The reviewed `common.runtime` module only loads the optional native runtime and
selects offload. AST import allowlists continue to prohibit evaluator, watermark,
secret and generation-backend imports in attack modules. CI checks both the static
boundary and a worker subprocess followed by trusted evaluation.

This is **scientific isolation, not a hostile-code security sandbox**. Python and
the OS account can still access files outside the temporary directory. The boundary
prevents accidental coupling in the shipped, reviewed attack implementation; it does
not safely execute arbitrary third-party attack code. Use OS/container filesystem
and network restrictions for that different threat model. Private files are never
needed by the worker or mounted/copied into its working directory.

## Four families

|Name|Transformation|Selection|Budget|
|---|---|---|---|
|`random_edit`|Single-word substitutions from a small conservative lexicon|Seeded uniform shuffle of safe replaceable positions|1, 2, 5, 10, 20% upper bounds|
|`synonym_replace`|Qwen proposes context-aware single-word alternatives, skipping ambiguous terms|Seeded shuffle; no detector feedback|Same sweep|
|`paraphrase`|One Qwen rewrite preserving claims, numbers, names, negations and tone|Single seeded generation; no retries based on outcomes|Measured actual edits; no fixed sparse budget|
|`entropy_rewrite`|Same contextual alternatives as local replacement|Descending ordinary unwatermarked next-token entropy at candidate word starts|Same sweep|

Sparse substitutions preserve capitalization-sensitive names, quoted spans, URLs,
emails, numbers, negation words, inline/fenced code and explicit formula/code lines
where practical. Protection is heuristic, not named-entity recognition or a grammar
guarantee. Requested edits are `floor(original_word_count × budget)`, capped by safe
available candidates. Sparse budgets are upper bounds; no-op outputs and candidate
exhaustion remain visible. Random Edit does not compute entropy or optimize damage.

For Entropy Rewrite, the restricted model computes full-vocabulary
`H = -sum(p * log(p))` from ordinary next-token logits. Word positions use the
last preceding prefix token (trailing whitespace excluded). This is a replaceability
heuristic; it does not use keys, green/red membership or SynthID g-values. Ties
retain seeded shuffled order. No context leverage, tokenizer instability, combined
SKD score, detector search or iterative minimum-budget optimization is implemented.

Qwen receives `enable_thinking=False` through the embedded chat template.
Transformation sampling is temperature 0.2 / top-k 40 / top-p .95, repeat penalty
1, min-p 0, up to 768 tokens, context 4096, with an explicit seed. Generation of
watermarked baselines retains the frozen .8 / 40 / .95 configuration and 192-token
limit. These are different tasks and deliberately separate settings.

Qwen proposes a minimally edited contextual copy. Only isolated single-word
substitutions at protected-safe positions are extracted; phrase restructuring is
ignored. This keeps proposals grounded in complete grammatical sentences. Grammar
function words are excluded. It remains a heuristic and can still introduce errors.
Contextual alternatives (and analysis failures) are computed once per input/seed and reused across budgets
and entropy selection within a worker. Final outputs use an immutable content-addressed
cache keyed by the public sample, attack/version/template, seed, requested budget,
model digest and operational inference settings. Cache contents include an integrity
checksum, never detector feedback. Runtime is recorded but is not deterministic.
Deterministic replay requires the recorded runtime/hardware as well as model and seed.
Sweep timings are amortized: the first uncached budget pays for linguistic analysis,
later budgets reuse it, and Entropy Rewrite reuses Local Replacement proposals.
The first request may also include native model loading. These are measured sweep
wall times, not independent cold-start costs for each attack/budget.

Output validation rejects empty text, exact prompt echo, excessive expansion or
contraction, known model commentary/preambles, control tags and truncated model
completions. Invalid output is a failure. Text is never silently cleaned or rewritten
after transformation. Successful identity transformations remain completed no-ops.

## Eligibility and outcomes

The trusted process first generates and evaluates the original visible continuation
with its matching frozen evaluator. Only **DETECTED** originals are eligible.
`require_detected_baseline()` enforces that guard. Baseline misses and baseline
abstentions are reported per scheme and never enter evasion denominators.

For each eligible original: blind transformation → quality measurement → the same
frozen detector. **EVASION** requires original DETECTED and attacked NOT DETECTED.
Post-attack INSUFFICIENT EVIDENCE is **ABSTENTION**. Crashes, timeouts and invalid
outputs are **ATTACK FAILURE**. Neither counts as evasion. Failures stay in the
all-eligible denominator for completion/evasion/detection/abstention rates.

Unsupported usable lengths remain an important reason for abstention. A short or
greatly expanded text does not become a successful evasion by leaving the calibrated
length range. Detector scores are measured on retokenized visible continuation text,
with no original native generation state exposed to an attack.

## Quality metrics

- Exact Levenshtein word and generation-token edit distances, divided by original
  sequence lengths. Words include numeric tokens and apostrophe contractions.
- Length ratio: transformed/original word count. Lexical similarity: Jaccard similarity
  of case-folded word sets. These are separate, continuous observations.
- Semantic similarity: cosine of pinned `sentence-transformers/all-MiniLM-L6-v2`,
  revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`, using
  `sentence-transformers==3.4.1` on CPU, without remote code. Long inputs are split
  into model-length token chunks; normalized chunk embeddings are averaged with
  token-count weights and normalized again. The entire text contributes.
- Anchor preservation: multiset retention of literal numbers, numeric dates,
  percentages, URLs and email-like strings; added anchors are also counted.
  Zero-anchor texts report `0 / 0` with null preservation fraction, not perfect facts.

**Embedding cosine is not factual correctness.** A cosine of .97 does not mean
97% of facts are correct. Anchor preservation is not full factual consistency.
Neither reliably catches changed relationships, unsupported assertions, lost
negations or subtle meaning drift. The GUI does not combine these into a fabricated
quality score. Random Edit's worker-side token counter uses regex lexical tokens;
the authoritative quality artifact always retokenizes with the generation model.

All metrics remain continuous. Descriptive quality-conditioned evasion at cosine
≥.90 and ≥.95 reports its own numerator, denominator and coverage of all eligible
samples. Those bands are exploratory, not universal scientific quality thresholds.
Summaries include count, mean and 5/25/50/75/95 percentiles, plus per-sample rows
and Pareto CSV data. Missing optional semantic evaluation remains null, never an
invented similarity score.

## Corpus, frozen detector and reproduction

`configs/benchmarks/attacks-v1.jsonl` contains 240 original prompts, 30 each in
factual, technical, essay, argument, narrative, instructions, science and general
knowledge styles. Styles are interleaved. Both IDs and normalized text are checked
for uniqueness and disjointness against `configs/calibration/prompts-v1.jsonl`.
The benchmark seed is 20261021; the default local run uses the first 128 prompts,
16 per style, for each watermark family.

Frozen evaluators are the unchanged v0.1.1 KGW and SynthID depth-20 weighted-mean
artifacts. They require the matching local private master. The 1% **target FPR**
must be distinguished from SynthID's **3/99 (3.03%) observed held-out FPR**.
Compatibility checks bind the model, sampling, watermark settings and key reference;
artifact hashes are checked again after a run. Experiment 003 never fits calibration.

```sh
pip install -e ".[gui,gguf,evaluation]"
# Prepare the optional pinned embedding cache once (no text leaves this machine):
python -c "from nullmark.evaluation.quality import SemanticSimilarity; SemanticSimilarity(local_files_only=False)"
nullmark benchmark-attacks configs/benchmarks/qwen-baselines.yaml \
  --output results/003-baseline-attacks/my-run \
  --secrets results/002-qwen-128/private/secrets.json
```

The generation and attack GGUFs reuse installed `qwen3.5:9b-q4_K_M` weights;
the command never downloads another language model. Optional MiniLM weights are a
separate small evaluation dependency. Set `HF_HOME` consistently when preparing
and using a custom local cache. Evaluation is local and cache-only by default.
CI uses deterministic offline fixtures and does not need Ollama, Qwen or MiniLM.

`--stage generate|attack|evaluate` and `--resume` allow staged execution with identical
config/dataset/calibration/key identity. Successful cached transformations are reused
without inference; failed attempts remain explicitly recorded. Generation and attack
runtimes are closed between stages so the GPU does not need two model copies.

Run files: resolved config and identity/manifest; public `source_samples.jsonl` and
eligible `attack_inputs.jsonl`; public per-family `attacks/*.jsonl`; evaluator-only
`baselines.jsonl`, `evaluation.jsonl`, `quality.jsonl`, `metrics.json`; summary, plots
and Pareto CSV; a local `private/` master for replay. The worker sees only serialized
public requests, never the enclosing run directory or evaluator files. Results and
caches are ignored by Git; curated public research exports must omit `private/`.

## Literature and limits

Paraphrasing attacks, entropy-guided rewriting and watermark robustness tests are
established research directions, not inventions of NullMark. Relevant context:
[Kirchenbauer et al., A Watermark for Large Language Models](https://arxiv.org/abs/2301.10226),
[Kirchenbauer et al., On the Reliability of Watermarks for Large Language Models](https://arxiv.org/abs/2306.04634),
[Krishna et al., Paraphrasing evades detectors of AI-generated text](https://arxiv.org/abs/2303.13408),
and [Dathathri et al., Scalable watermarking for identifying large language model outputs](https://doi.org/10.1038/s41586-024-08025-4).

Measured conclusions are conditional on one Qwen quantization, specific keys and
configurations, this corpus and the frozen operating points. Prompt generation length,
candidate exhaustion, model output failures, grammar mistakes and embedding limitations
are part of the results. Manually inspect deterministic examples across all styles,
families, schemes and representative budgets. No commercial detector integration,
production provenance querying or public watermark-removal endpoint is provided.

**v0.3 Sparse Keyless Disruption has NOT been started.**
