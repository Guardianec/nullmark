# Changelog

## 0.3.0 — Sparse Keyless Disruption

- One shared pool of bounded local Qwen proposals, validated canonical source
  spans, deduplication and capacity-preserving non-overlapping selection.
- Five public detector-blind features and preregistered fixed weights; exact
  1/2/3/5 edits; matched random, entropy, context, tokenizer and full-SKD selectors.
- Experiment 004: 240 fresh prompts, 480 sources, 479 eligible pools and 9,580
  evaluated attempts. Complete exact-k coverage, zero execution failures.
- Full SKD evasion: KGW 0% at every budget; SynthID 0/0/.42/.42%. All paired
  SKD-vs-random score-drop intervals include zero. Quality metrics, abstentions,
  distributions, paired intervals, post-hoc correlations and seven plots published.
- Candidate inspector with actual raw/normalized features, selected spans and
  edits, text diff, quality and clearly labeled evaluator-only detector results.
- Fixed qualitative inspection documents grammar/meaning failures despite high
  cosine. Two implementation corrections were preregistered before post-attack
  evaluation; invalidated attempts and byte-identical source provenance retained.
- 272 offline tests pass, one optional integration skipped; clean wheel and
  historical exact-replay checks. No v0.4 implementation or detector feedback.

## 0.2.0 — Baseline Attacks

- Four keyless, detector-blind baseline families: Random Edit, contextual Local
  Replacement, one-pass Paraphrase and ordinary-entropy Rewrite. No SKD features.
- Subprocess worker with text-only inputs, explicit provenance, validated outputs,
  clean cwd/environment, AST import guards and content-addressed public caches.
- Fresh 240-prompt corpus in eight styles, disjoint from calibration. Experiment
  003 reuses frozen v0.1.1 KGW and SynthID depth-20 weighted evaluators unchanged.
- Eligibility, completion, evasion, failure and abstention accounting; exact edit,
  pinned local semantic similarity and anchor metrics; distributions, descriptive
  quality-conditioned evasion, Pareto CSV and static plots.
- Playground attack selector and synchronized original/diff/attacked text panels,
  continuous quality metrics and separately labeled evaluator-only detector results.
- CPU/offline smoke fixtures and documentation for local Qwen benchmarking,
  scientific isolation, semantic limitations and reproducibility.

- Real Qwen run: 128/128 eligible originals per scheme, 4,096 completed attempts.
  Paraphrase evasion 2/128 KGW and 7/128 SynthID; abstentions reported separately.
  Sparse mean actual edits remain below 1% due to conservative candidate exhaustion.
- Deterministic 64-comparison qualitative inspection and a real calibrated Qwen
  Playground replay; measured results and limitations are published in docs.

## 0.1.1 — 2026-10-20

Final detector calibration pass:

- Experiment 002: deterministic disjoint prompt splits, clean-only finite-sample
  target-FPR thresholds, frozen reusable condition-bound calibration artifacts.
- SynthID raw mean-g retained; reference weighted mean added without changing generation.
- Held-out TPR/FPR, uncertainty, specificity, abstention, length buckets, score
  distributions, descriptive ROC data, native/visible diagnostics and runtime reporting.
- Playground names the statistic and requires compatible calibration for binary
  decisions; unsupported conditions/lengths report insufficient evidence.
- Existing Experiment 001 and v0.1.1 scope retained; no attack implementation.
- Future evasion eligibility guard rejects originally undetected/abstained samples;
  per-sample held-out decisions retain their frozen calibration identity.
- Completed local Qwen 128/100-prompt depth study; public aggregate metrics,
  frozen artifacts, histograms and calibrated Playground replay. Depth-20 weighted
  mean is the exploratory recommendation (97/98 TPR, 3/99 observed FPR at a 1%
  target); no SynthID mode establishes the requested population FPR from this run.

Visual Playground (maintenance/usability insertion):

- Optional direct GGUF backend reuses supported Ollama-installed weights; no duplicate model download.
- Loopback-only discovery, language/projector separation, blob SHA-256 verification and private paths.
- Embedded chat templates, non-thinking request where supported, exact generation IDs and EOG handling.
- Reused HF processors in the native pre-sampling hook; callback failures reject the sample.
- `nullmark model check-ollama` tests replay, forced logits and multi-seed watermark signals.
- Temperature/top-k/top-p controls and provenance; historical Experiment 001 settings stay pinned.
- Windows Qwen 3.5 9B smoke verification, mocked native tests and conservative model-cache cleanup.

- Optional localhost FastAPI interface; bundled assets, no Node.js or cloud API.
- Cached builtin-tiny and pinned GPT-2; None, KGW and SynthID generation.
- Same-seed plain/marked comparison, divergence marker, token inspector and stepper.
- Shared typed KGW membership and SynthID depth g-values; cumulative detector traces.
- Explicit insufficient-text, retokenization and uncalibrated-score states.
- Replace direct secret fingerprints with domain-separated, master-bound HMAC references.
  Watermark key derivation stays unchanged; v0.1.0 public fingerprints require replacement.
- Regression tests, optional GUI CI and clean installation verification.
- Document pinned HF KGW repeated-n-gram counting behavior without changing the detector.

No attack algorithms were implemented. Next: **v0.2 — Baseline Attacks**.

## 0.1.0 — 2026-10-20

Reproducibility foundation:

- Installable Python package and small CLI for generation, detection, experiments and summaries.
- Open Transformers SynthID-Text and KGW-style adapters, plus CPU model inference.
- Private randomized key configurations, text-only attack boundary and explicit public exports.
- Deterministic replay, pinned pretrained model revisions and environment/dataset provenance.
- Experiment 001, paired unwatermarked controls, descriptive metrics and raw JSONL artifacts.
- Offline CPU tests, GitHub Actions, research notes and upstream attribution.

SynthID mean thresholds are uncalibrated smoke defaults. Small experiments do not
support research-scale claims. No attacks ship in 0.1.0; attack algorithms begin
in **v0.2 — Baseline Attacks**.
