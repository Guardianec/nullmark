# Sparse Keyless Disruption — v0.3 protocol

This is an explicit research hypothesis, not a theoretically optimal score or a
claim of universal watermark removal. Work is restricted to open implementations,
locally controlled Qwen, controlled data and local keys.

The worker receives only an opaque sample ID, prompt, visible continuation and
public linguistic resources. Benchmark IDs are hashed before export, hiding the
scheme prefix. No key, key reference, detector, threshold, calibration, greenlist,
g-values, native generation IDs or post-attack feedback enters the worker. Python
process/environment isolation is an architectural boundary, not an OS security
sandbox against malicious code. AST import guards cover all attack modules.

## Candidate generation and validation

The installed `qwen3.5:9b-q4_K_M` is asked for three independent batches of up to 12
localized edits. Enumerate valid 1–4 word source spans using the structural anchor
filters, shuffle with the public sample seed, and target at most 36 distinct spans
in three disjoint batches of 12. Each target has canonical character offsets,
original text and an integer span ID. Qwen returns only span ID and replacement;
it never calculates source offsets. Validate the canonical span against actual
source text again before accepting the replacement. No synonym dictionary is
used. Each batch uses seed + batch index, temperature .2, top-k 40, top-p .95,
1536 output tokens, no thinking, context 8192. A bounded JSON-schema grammar
enforces an array of at most 12 objects with exactly span ID and replacement.
The ID is an enum of that batch's public targets; replacements are bounded to
120 characters. The schema hash is saved in sampling
metadata. Offsets must match source text
exactly; malformed batches are rejected without repair or outcome-driven retry.

Source spans contain 1–4 lowercase words; replacements contain 1–6 and at most
source length + 2 words. Numbers, dates, URLs, emails, quoted text, code/formula
lines, proper-name capitals and explicit negations are protected. Replacements
cannot add protected anchors, sentence punctuation, model control text or empty
content. Logical conjunctions/scope words are protected; isolated function words,
short words and partial hyphen/apostrophe compounds are rejected. The development
inspection exposed an `or` → `and` proposal and partial `high-speed` proposals;
these structural filters were added before any benchmark detector outcomes.
Actual proposal counts are recorded. A protocol-v1 attempt only requested this
format and let Qwen calculate offsets; it rejected all three batches in its first
real samples. It was stopped
and invalidated with zero post-attack detector evaluations. Protocol v2 enforces
the promised format and canonical source references in ordinary Qwen decoding.
Feature definitions, weights,
filters, seeds and fixed budgets are unchanged; frozen baseline generations are
reused with a recorded provenance link. See [the protocol amendment](skd-protocol-amendment.md).
Final-text hashes deduplicate equivalent edits. Multiple alternatives at
one span remain alternatives, never multiple selectable edits.

Local MiniLM similarity uses the replacement plus up to four unchanged words on
each side. Reject cosine below **.85**, pre-registered without detector feedback.
Use the same public MiniLM model/revision as v0.2:
`sentence-transformers/all-MiniLM-L6-v2` at
`c9745ed1d9f207416be6d2e6f8de32d1f16199bf`, local cache only. Similarity is
not factual correctness and can miss scope or factual changes.

Every artifact reports source words, proposals, valid/safe/unique candidates,
rejections and maximum non-overlapping interval capacity. Valid/safe counts are
before deduplication; unique and capacity counts are after it. Candidate coverage
denominators are all eligible baselines, with failed pools counted as unavailable.
Ineligible baseline states are reported separately.
Generation metadata preserves the public sample seed, attack-model digest,
targeted canonical spans and each batch's schema hash and parse status.

## Five features and fixed score

|Feature|Reproducible raw definition|Weight|
|---|---|---:|
|E — entropy opportunity|Mean next-token Shannon entropy in nats at token positions overlapping the original span, from ordinary unwatermarked Qwen logits. The first token has no preceding distribution and is omitted.|+1.0|
|L — context leverage|Retokenize final single-edit text; align equal token blocks with deterministic SequenceMatcher. Count aligned unchanged tokens whose preceding **8-token** histories differ. Inspect the first 8 tokens of each equal block; later histories have reconverged.|+1.25|
|T — tokenizer instability|Levenshtein distance between ordinary Qwen token IDs for the local before/after window, including four boundary words on either side.|+1.0|
|R — replaceability|Minimality proxy: `1 / (1 + word Levenshtein distance(original span, replacement))`. This measures how small the linguistic replacement is, not proposal probability or model confidence. Naturalness is requested from Qwen; this proxy does not certify grammar.|+1.0|
|D — distortion risk|`1 - local cosine + .25 * abs(replacement_words-source_words)/max(source_words,replacement_words)`; anchors/negations are hard-filtered first.|−1.5|

Normalize each feature independently inside one sample's validated pool using
midrank percentiles: `(number below + (number tied - 1)/2)/(n-1)`.
Singletons and constant columns receive .5. Missing/nonfinite features fail the
analysis; no invented zero fallback. Score is the weighted sum of normalized
features. Candidate identity breaks ties deterministically. These choices are
frozen before benchmark outcomes; no detector-guided tuning or search occurs.

## Selection and matched ablations

One edit is one non-overlapping source-span replacement. Budgets are exactly
**1, 2, 3, 5**. All selectors reuse the same scored candidate pool and public seed:
`random_pool`, `entropy_only`, `context_only`, `tokenizer_only`, `skd`.
Random uses a deterministic shuffle; other methods rank their indicated feature.
Select the highest-ranked feasible candidate, preserving sufficient remaining
interval capacity to realize k whenever possible. This feasibility constraint is
identical for every selector. Apply source spans from right to left, once.
No recomputation, detector query loop, proximity penalty or adaptive stopping.

If capacity is below k, apply the available edits and explicitly record requested
count, actual count and exhaustion. Report all-eligible results and exact-k
comparable subsets separately. Comparable subsets require capacity ≥ k and all
five selectors actually realizing k. Failures are retained in all-eligible
denominators and separately reported among coverage losses.

## Experiment 004 and pre-registration

The new `skd-v1.jsonl` corpus has **240 prompts, 30 in each of eight styles**,
seed **20261023**, with ID and normalized-text disjointness from calibration,
v0.2 and the eight-prompt `skd-dev-v1.jsonl` development corpus. The corpus
uses 30 shared topics across eight tasks; topic-related dependence limits general
inference. Paired intervals resample samples, not independent topic clusters.

Generation/evaluators remain the frozen v0.2 path: Qwen 192 tokens, temperature
.8, top-k 40, top-p .95; KGW and SynthID d20 weighted mean. Target FPR is 1%;
the frozen SynthID evaluator's observed held-out FPR was 3/99 (3.03%). Do not
recalibrate. Original DETECTED is eligible; baseline misses/abstentions never
enter the evasion denominator. After-state NOT DETECTED is evasion; insufficient
evidence is abstention; invalid output/crash is failure.

The CLI requires the full committed design SHA and verifies the attack source,
public semantic implementation, worker, benchmark/report, config, corpus and
this protocol against that commit before every benchmark stage. Resolved config,
design SHA, evaluator hashes, environment and dataset hash are saved. All five
selectors' outputs must be on disk before constructing the post-attack detector.
Changing a protocol file requires a new declared design commit and a fresh run;
document invalidated runs rather than silently replacing results.

```powershell
nullmark benchmark-skd configs/benchmarks/qwen-skd.yaml `
  --output results/004-skd/qwen-v030 `
  --secrets results/002-qwen-128/private/secrets.json `
  --design-commit <full-design-commit-sha>
```

Stages `generate`, `attack`, `evaluate` support `--resume` with identical inputs.
Public candidates contain only attack-side features/metadata; private keys stay
under `generation/private`. Whole-text quality retains every v0.2 metric. No
composite quality score is introduced.

Paired bootstrap differences (SKD minus random/entropy score reduction) use
**5000** sample resamples, public seed **20261024**, percentile 95% intervals,
separately by scheme and k, with missing-score pairs reported. Feature/effect
Spearman correlations use deduplicated observed one-edit candidates only. They
are descriptive post-hoc analyses and never alter weights or selection. Static
plots and machine-readable analysis/quality/pareto files accompany results.

Before outcomes, fix qualitative selection to the first lexicographic prompt ID
per style, both schemes. Inspect k=1,3,5, rotating selectors by style order
(`random_pool`, `entropy_only`, `context_only`, `tokenizer_only`, `skd`) and also
inspect full SKD at every chosen k. Record duplicates, factual/negation/entity
changes, grammar, truncation and tokenizer artifacts, including failures.

Historical v0.2 results are context only: different corpus, candidate generation
and mechanics prevent pooled denominators. Optional paraphrase and leave-one-out
runs are deferred to keep this fixed milestone bounded. No v0.4 transfer tests,
new watermark families, key inference, policy learning or budget search.
