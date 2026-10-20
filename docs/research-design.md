# Research design — v0.1

NullMark asks how a keyed open text watermark behaves under controlled generation
and, in later milestones, meaning-preserving edits. The first release validates
the experiment machinery. It makes no claims about watermark-breaking attacks.

## Threat model and information boundary

The future blind attacker knows the prompt, continuation text, sample identifier,
public algorithm family, and published research methodology. It receives neither
keys nor detector statistics, model generation state, or a detector query oracle.
The evaluator knows the model/tokenizer revision, all watermark settings, private
master, derived keys, exact original token IDs, ground truth and detector outputs.
The experiment runner is trusted; it does not invoke any attack in this release.

The intended flow is watermarker → sample → attacker boundary → evaluator.
`AttackInput` has a fixed, text-only allowlist. Public exports are constructed from
that allowlist rather than serializing a rich experiment object. AST checks reject
evaluator, model and watermark imports in the current attack package. Such checks
prevent accidental coupling; they do not isolate arbitrary Python. When executing
untrusted future attacks, use a separate process/environment/filesystem that only
has the public sample export. Do not mount private run files there.

The research outcome is a change in the held-out detector's behavior, so future
attacks do not need to recover a key. Revealing scores during transformation would
change the experiment into a detector-query attack. Blind and feedback-enabled
threat models require separate, explicitly labeled evaluations; feedback is not
supported in 0.1.

## Generation and replay

A public seed controls sampling; it never controls key generation. A private,
OS-random 256-bit master is domain-separated through HMAC-SHA256 by scheme,
key index, and SynthID depth/table parameter. The first 32 digest bits, plus one,
form an upstream-compatible positive integer parameter. These values are not
claims about cryptographic security of the upstream watermark. Since v0.1.1,
key references
are HMAC-SHA256(master, "nullmark-v1/key-ref/<scheme>/<index>"). They identify a
master/scheme/index configuration without hashing low-entropy derived keys.
Publishing a direct hash of a KGW integer, as v0.1.0 did, enables offline guess
verification. The new references are stable under master reuse and separated by
scheme and index; they do not expose an oracle for guessed derived integers.
This assumes a private high-entropy master and does not strengthen upstream
watermark security. References identify key slots, not public parameter settings;
retain public configuration alongside them. Existing published v0.1.0 fingerprints
cannot be made safe retroactively: replace those artifacts and rotate affected
masters if key secrecy matters. Plaintext keys are not written to exported rows.
The local master suffices to regenerate
them under the versioned `nullmark-v1` derivation.

Save the private master to replay a run. Publishing the master or all run files
would invalidate blind evaluation. Keep private replay artifacts under evaluator
access control. The normal resolved YAML contains no secrets, and exported
sampling seeds cannot derive the master. Tests search all non-private output
files for the master and actual derived key values.

Sampling uses a fresh scoped Torch RNG per sample. Corresponding plain and marked
conditions use the same sampling seed; different prompt/key pairs use a SHA-256
derived seed. Process-global deterministic algorithms and configured thread counts
are recorded; CPU is the tested backend. The built-in smoke model's fixed weight
initialization seed is independent of both generation and watermark randomness.
For Transformers, full pretrained model commit IDs are mandatory, remote model code is disabled,
and only safetensors weights are loaded. Tokenizer and model use the same revision.
The prompt subset, dataset digest, package versions, platform, source Git revision
when available, model identifier and configuration are stored in every run.

## Detector choices and statistics

Experiment 002 adds clean-only target-FPR calibration on a deterministic prompt
split, frozen before held-out generation. It compares explicitly named SynthID
raw mean-g and upstream weighted mean statistics, plus KGW z-scores. The immutable
artifact binds model/config/sampling/key identity and observed usable-length support.
Unsupported lengths/counts abstain. See [the calibration protocol](detector-calibration.md)
for finite-sample ranks, uncertainties, length buckets, native/visible diagnostics,
and the guard future attack-success metrics must call. Historical demo thresholds
below remain for Experiment 001 reproduction; they are not calibrated decisions.

The [completed Qwen depth study](detector-calibration-results.md) recommends the
frozen depth-20 weighted statistic as an exploratory practical choice. Its held-out
TPR is 97/98 and FPR is 3/99 at the threshold selected with a 1% target. None of
the six SynthID modes achieved an observed FPR at or below 1%; do not interpret
the target as a validated population rate or retune using this evaluation set.

SynthID generation uses the Google DeepMind/Hugging Face integration. Its
reference g-values are extracted with the matching secret config; repeated
contexts and EOS/padding suffixes are masked. We average unmasked g-values across
all depths, following the reference mean detector. The 0.60 threshold is a
configurable smoke default. It is not a calibrated posterior or a guarantee of a
specific FPR. A trained Bayesian detector is deliberately not substituted with
random parameters. Experiments on texts of different lengths need length-aware
calibration on independent controls.

KGW uses Transformers' `lefthash` green-list bias and corresponding detector;
the unique-n-gram option is enabled by default. Inspection in v0.1.1 found
that pinned HF 4.57.6 uses tensor identities in its frequency counter, so repeated
n-grams actually count separately. This maintenance release preserves the v0.1
detector and reports its actual behavior; the playground trace matches that
behavior. Do not infer independent evidence from repeated text. Its nominal
z-score uses the
configured green-list ratio. Vocabulary partition sizes are rounded down by the
reference implementation, so that nominal ratio is approximate on small
vocabularies. We compute its upper-tail normal p-value with the standard library
`erfc`, rather than the upstream p-value approximation. Dependencies among tokens,
repeated contexts, entropy, and sample length limit the interpretation of this
p-value. It is not the probability that a document is watermarked.

Text is decoded without cleanup and retokenized before detection. The prompt is
excluded, as are the initial continuation positions without sufficient context.
The original continuation IDs are retained for auditing; a mismatch count flags
tokenizer round trips. A detector with insufficient usable text abstains instead
of returning an invented negative score. Failures and abstentions are counted
separately; TPR/FPR/accuracy use only successful non-abstaining observations.
Generation failures are never silently treated as correct negatives.

Raw data, pooled and per-key TPR/FPR, accuracy, mean/median/population standard
deviation/range of scores and lengths, generation timings, failures, and total
runtime are retained. Each plain sample is evaluated by both families; those
observations and key-conditioned generations are correlated. No independence,
confidence interval, calibrated FPR or population generalization is inferred from
the tiny default runs.

## Scientifically valid future comparisons

Hold model, tokenizer, prompts, sampling policy, length budgets, detector thresholds
and key distribution constant across compared conditions. Calibrate detectors on
disjoint data before measuring attacks. Predefine false-positive targets, report
abstention/failure coverage and uncertainty, and split development/evaluation
prompts and keys. Define edit cost and semantic preservation before searching for
MDB. Compare methods at matched query/compute/edit budgets. Report length and
style strata, all controls and raw results, including unsuccessful trials. Never
select test keys or tune thresholds using attack outcomes on the held-out test set.
These are evaluation requirements for future work, not implemented attack features.

## Limitations

- The offline model is untrained and cannot establish language quality or research conclusions.
- GPT-2 is small; its behavior cannot establish generalization to stronger models.
- The smoke prompt/key counts are too small for reliable rare false-positive estimates.
- SynthID's sparse calibration tail needs larger independent confirmation for strict
  population FPR claims; no Bayesian training ships here.
- CPU replay is tested; cross-environment bitwise replay and CUDA behavior are not guaranteed.
- Parameter randomization is not a cryptographic security proof or production-key inference.
- Architecture checks are not a sandbox, and filesystem ACLs remain the evaluator's responsibility.
- Version 0.1 contains no transformations, semantic scoring, MDB search or robustness benchmark.

## References

- Kirchenbauer et al., *A Watermark for Large Language Models*, ICML 2023:
  https://arxiv.org/abs/2301.10226 and https://github.com/jwkirchenbauer/lm-watermarking
- Dathathri et al., *Scalable watermarking for identifying large language model outputs*,
  Nature 2024: https://doi.org/10.1038/s41586-024-08025-4
- Google DeepMind SynthID-Text implementation and mean detector:
  https://github.com/google-deepmind/synthid-text and
  https://github.com/google-deepmind/synthid-text/blob/main/src/synthid_text/detector_mean.py
- Pinned Transformers generation and detection implementation:
  https://github.com/huggingface/transformers/tree/v4.57.6/src/transformers/generation
- GPT-2 model card and license:
  https://huggingface.co/openai-community/gpt2

## Trusted visualization (v0.1.1)

The local playground consumes typed inspection data in `nullmark.evaluation`.
It is trusted researcher/evaluator tooling with access to hidden keys and detector
feedback, never an attack interface or blind attacker input. It does not execute
transformations or benchmark suites. Generation-context token views and the
retokenized continuation-only detector trace are explicitly separate. The CLI
remains authoritative for replayable experiments. See [playground](playground.md).


### Direct GGUF amendment

Supported Ollama-installed GGUFs are discovered only on loopback; direct
llama-cpp-python inference passes exact native prefix IDs and full-vocabulary
logits through the same HF watermark processors before sampling. Native custom
callbacks are checked against actual prefix IDs, vocabulary shape and sample
counts; exceptions are raised outside ctypes and no unmarked fallback sample is
returned. The GGUF blob is SHA-256 verified before loading. Chat-template digest,
backend/version, quantization, context/offload and sampling are recorded, without
absolute blob paths. Formatted prompt IDs are retained in private token records.

The native order is watermark transformation, then native top-k/top-p/temperature
sampling with neutral repetition penalty and disabled min-p. Transformers retains
its pinned processor ordering. Equal numeric settings do not promise identical
sampling behavior across engines, vocabularies, quantization or hardware.

Core sampling defaults and Experiment 001 retain temperature 1, top-k 0, top-p 1;
interactive defaults are explicitly 0.8/40/0.95. No detector threshold was tuned to
make the Qwen examples positive. At these low-entropy instruction continuations,
consistent correct-key signal gain need not cross the historical uncalibrated
threshold. This is a usability/backend smoke check, not a semantic-quality metric,
calibration study or attack milestone.
