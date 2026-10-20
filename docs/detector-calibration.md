# Detector calibration — v0.1.1

A watermark score and a detector decision answer different questions. Higher
marked scores than paired controls demonstrate signal separation. They do not
establish a false-positive rate. SynthID's historical 0.60 mean-g threshold and
KGW's z=3 comparison remain **legacy/demo operating points** in Experiment 001.
Neither is an empirical calibration for Qwen. Experiment 001's GPT-2 settings,
depth 10, prompts and generation behavior remain the historical smoke protocol.

## Reproducible Experiment 002

```sh
nullmark calibrate configs/calibration/qwen.yaml --output results/002-qwen
```

This opens the existing `qwen3.5:9b-q4_K_M` language GGUF directly with llama.cpp,
checks its SHA-256, and uses temperature 0.8, top-k 40 and top-p 0.95. It never
downloads another checkpoint. A compatible optional GGUF runtime is required;
see [local setup](playground.md#ollama-installed-gguf). GPU offload is explicit in
the supplied configuration. Change it to CPU only for a separately identified run.

The supplied dataset contains 240 original prompts, with 30 each for factual
explanation, technical explanation, essay, argument, narrative, instructions,
science and general knowledge. Five instructions per style and varied topics
avoid relying on a single template. Predeclared requested lengths vary from
60 to 230 words; generation caps continuations at 192 native tokens. Some long
answers will therefore be incomplete. These are local research prompts, not a
representative sample of all human or model text. The Qwen configuration reserves
128 calibration prompts and 100 evaluation prompts, leaving 12 unused. The extra
calibration prompts allow for clean outputs below the minimum usable length;
the usable clean count in the artifact, not the prompt count, determines support.

The public seed 20261020 shuffles prompts within style, balances style counts
across independent calibration/evaluation partitions, and derives generation
seeds. IDs **and exact prompt texts** must be unique. Corresponding plain, KGW,
and SynthID depth 10/20/30 generations share the same prompt and sampling seed.
Raw and weighted SynthID scores reuse each depth's generation. Plain text is
generated once and scored by all configurations. These shared controls make
comparisons paired; detector rows are not independent additional samples.

Thresholds are fitted on **clean calibration continuations only**, before any
held-out continuations are generated. Marked calibration scores are descriptive.
The entire artifact, including length support, is frozen at that point. No
evaluation score chooses or updates its threshold. Changing a future default
after comparing this study's configurations makes that choice exploratory;
confirm the selected default on a fresh dataset before broader performance claims.

Artifacts include:

- `config.resolved.yaml`, a portable prompt snapshot, deterministic `splits.json`,
  dataset hashes, split seed, model/runtime identity and environment provenance;
- `samples.jsonl` for manual quality inspection and `scores.jsonl` with all raw
  scores, lengths, native/visible diagnostics, generation latency and callback time;
- one `*.calibration.json` per detector/depth/target FPR, frozen before evaluation;
- `metrics.json`, `summary.md` and lightweight held-out distribution SVGs;
- `evaluation.jsonl` with each held-out frozen decision and calibration identity;
- evaluator-only `private/secrets.json` and `private/tokens.jsonl` for exact replay.

Resolved configurations and public artifacts contain no private watermark keys
or model filesystem paths. The master is independent of the public sampling seed.
Replay with the resolved configuration and `--secrets RUN/private/secrets.json`;
use a new output directory. Never give the private directory, scores, or native
token diagnostics to future blind attack implementations; their existing input
boundary remains text only.

For a shorter exploratory run, copy the YAML and reduce `calibration_count` and
`evaluation_count`, retaining independent prompts. A small run is **exploratory**,
not evidence that its requested FPR has been estimated precisely. `target_fprs`
accepts, for example, `[0.001, 0.01, 0.05]`; the default is `[0.01]`.

## Finite-sample threshold rule

For n usable clean calibration scores sorted ascending, target alpha, select
the one-based order index `k = ceil((n + 1) * (1 - alpha))`. Use the k-th score
as the threshold and declare positive only when **score > threshold**. Ties are
negative. There is no interpolated quantile or hand-picked constant. Decimal
arithmetic prevents binary floating-point rounding from moving an integer rank.

If k exceeds n, record the maximum observed score as an exploratory threshold
and mark the artifact unsupported. NullMark also requires at least `ceil(1/alpha)`
usable clean samples before enabling a decision. Thus 20 clean samples cannot
support a 1% decision, and 100 cannot support a 0.1% decision. Every artifact records
target FPR, usable clean count, order index, threshold, observed calibration FPR,
support flag and warnings. Fewer than five expected clean tail samples triggers
an uncertainty warning even when the rank is resolvable.

At n=100 and alpha=1%, this conservative rule selects the maximum clean score,
with observed calibration FPR zero. **Zero observed positives does not establish
a zero population FPR.** Under exchangeable clean scores, the order-statistic rule
has a marginal tail probability bounded by alpha. It is not a 95% guarantee for
this one fitted threshold. Heterogeneous prompts, fixed key, repeated n-grams,
token dependence and length selection limit that idealization. In particular,
conditional TPR/FPR after length abstention must be measured, not inferred from
that marginal argument. A hundred clean samples offers very limited tail
resolution; larger independent calibration/evaluation sets remain necessary for
precise low-FPR claims. With zero positives among 100 independent clean evaluation
samples, the exact one-sided 95% binomial upper bound is about 2.95%, not 1%.

## SynthID statistics

`raw_mean` retains the historical mean over unmasked g-values and all layers.
`weighted_mean` follows the upstream reference's default descending linear layer
weights from **10 to 1**, normalized by their sum. Earlier layers receive higher
weight. For one sample it is `sum(mask * g * weights) / (sum(mask) * sum(weights))`.
The PyTorch adaptation uses the existing pinned HF g-values, context repetition
mask and EOS mask; it does not import JAX or change generation.

Reference: [Google DeepMind detector_mean.py at a6ec02c](https://github.com/google-deepmind/synthid-text/blob/a6ec02c22ce87177c061643503e14a7cc839dc2b/src/synthid_text/detector_mean.py),
Apache-2.0. [Upstream guidance](https://github.com/google-deepmind/synthid-text/blob/a6ec02c22ce87177c061643503e14a7cc839dc2b/README.md)
also cautions that weighted-mean thresholds depend on text length. No trained
Bayesian detector or additional detector family is introduced.

## Length, states and frozen evaluators

Reports retain visible retokenized counts and usable detector counts separately.
They show score distributions, TPR, FPR and abstention for `<64`, `64–127`,
`128–255`, `256–511` and `512+` in both visible and usable token units. Empty
buckets remain empty. A 192-token generation cap provides no evidence about
256+ lengths; never extrapolate those buckets from this study.

There is one pooled threshold per compatible configuration, not a threshold
tuned for each bucket. Only clean scores meeting the configured minimum usable
length (64 by default) enter the fit. Its reusable length regime is bounded by
the minimum/maximum usable length actually observed in those clean samples.
This conservative refusal to extrapolate can abstain even on visibly long text
when repeated contexts leave too few usable tokens. The target FPR describes the
pooled experiment population, not every conditional length bucket.

The evaluator returns **DETECTED**, **NOT DETECTED**, or **INSUFFICIENT EVIDENCE**.
It abstains on impossible scores, unsupported calibration sample counts, and
lengths outside the frozen regime. Uncalibrated GUI scores have no binary
prediction; incompatible artifacts also disable classification. Historical core
`detect()` predictions remain available for Experiment 001 compatibility and are
explicitly marked `decision_scope: legacy_demo`; use the calibrated evaluator
for research decisions, not those demo booleans.

`CalibratedDetector` is immutable, serializable and integrity checked. It binds
scheme/statistic, public watermark config (including depth), model/blob/runtime
and template identity, generation/sampling settings, key reference, dataset hash,
length support, timestamp/version and threshold. It rejects incompatible reuse.
The integrity digest detects accidental edits; it is not an authenticity signature.
`require_frozen_evaluator()` guards future attack-success code.
`require_detected_baseline()` additionally restricts evasion eligibility to
originally detected samples. Future attack metrics must report that eligibility
rate; a pre-existing detector miss is not successful evasion. No attack is
implemented here. An attacked sample returning INSUFFICIENT EVIDENCE must be
reported as abstention, not silently counted as successful evasion.

## Native versus visible diagnostics

Both paths score continuation only, excluding the prompt. The native path uses
the exact generated IDs, including any retained EOG. The authoritative path
retokenizes the actual displayed text with the same backend. Each row records
native score, visible score, native-minus-visible delta, exact-roundtrip flag,
native count, retokenized count and usable detector count. EOS masking means an
extra native EOG can break exact roundtrip while leaving the score unchanged.

Reports give mean/median delta, the 95th percentile absolute delta, exact-roundtrip
fraction and native/visible frozen-threshold disagreements, separately for each
detector and clean/marked condition. These diagnostics remain evaluator data.
Generation throughput counts native sampled tokens, including EOG. Callback time
measures the native logits hook, including its validation/copy overhead; it excludes
processor construction, model loading and detector work. Total generation latency
includes prompt processing. Transformer runs leave callback time null rather than
invent a measurement. Matched-seed latency differences also include output length
and model execution differences; they are not pure callback overhead.

## Reading results

The primary operating metric is **held-out TPR at the frozen target-FPR threshold**,
alongside observed held-out FPR and its denominator. Reports include specificity,
abstention (overall and by class), usable sample count, class balance, score
distributions, and marked detection yield including abstentions. TPR/FPR condition
on non-abstained observations; yield prevents abstention from hiding weak overall
coverage. Reported Wilson 95% intervals are standard binomial approximations,
not watermark posterior probabilities; dependence/paired comparisons limit their
interpretation. No deployment precision is reported without an explicit prevalence.

The saved ROC-style threshold sweep uses held-out scorable scores descriptively;
it never updates the frozen threshold. KGW also reports the legacy z=3 comparison
on the same held-out scorable population, with separate denominators. Do not compare
that rate directly with a calibrated rate without checking length eligibility.

Inspect the continuation samples manually for coherence, factual problems,
repetition and truncation. This release introduces no semantic-quality model.
See [the local validation report](local-model-verification.md) for measured Qwen
results and the practical configuration recommendation. v0.2 attack implementation
has NOT started.
